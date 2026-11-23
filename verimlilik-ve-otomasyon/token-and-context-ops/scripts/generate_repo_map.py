#!/usr/bin/env python3
"""
Lightweight, Token-Efficient Repository Map Generator.
Extracts directory hierarchy, symbol signatures (functions, classes, interfaces, routes, HTML IDs/tags),
and exact line ranges (`Lxx` or `Lxx-Lyy`) without reading entire file contents into LLM context.
Features:
- Fast change-detection (mtime caching with schema versioning)
- HTML (including inline `<script>` JS), JS/TS, Astro/Svelte/Vue, Python, Go (types/receivers/routes), SQL (`CREATE`/`ALTER TABLE`), Java, C/C++, C#, PHP, Rust, PowerShell, CSS, Markdown symbol extraction
- Multi-query symbol lookup (`--find "Foo|Bar"`) for instant retrieval
"""

import os
import sys
import re
import json
import fnmatch
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

DEFAULT_IGNORES = {
    '.git', '.svn', '.hg', 'node_modules', 'dist', 'build', 'out',
    '.next', '.nuxt', '.venv', 'venv', 'env', '__pycache__', '.pytest_cache',
    '.mypy_cache', '.ruff_cache', '.cache', '.idea', '.vscode', 'coverage',
    '.turbo', 'vendor', '.gemini', '.agents', '.superpowers', '.worktrees',
    'brain', 'bin', 'obj', 'target', '.gradle', '.cargo', 'package-lock.json',
    'yarn.lock', 'pnpm-lock.yaml', 'composer.lock', 'Cargo.lock', 'poetry.lock'
}

BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.webp', '.pdf', '.docx',
    '.xlsx', '.pptx', '.zip', '.tar', '.gz', '.7z', '.exe', '.dll', '.so',
    '.dylib', '.bin', '.class', '.jar', '.war', '.pyc', '.pyd', '.ttf', '.woff',
    '.woff2', '.eot', '.mp3', '.mp4', '.mov', '.avi', '.sqlite', '.db'
}

CACHE_FILENAME = ".repo-map.cache.json"
CACHE_SCHEMA_VERSION = 4
SKIP_JSON_SUFFIXES = ('.lock.json', '.cache.json', 'tsconfig.tsbuildinfo')

_SYMBOL_LINE_RE = re.compile(r'\(L(\d+)(?:-L(\d+))?\)$')


def format_symbol(label, start_line, end_line=None):
    if end_line is not None and end_line > start_line:
        return f'{label} (L{start_line}-L{end_line})'
    return f'{label} (L{start_line})'


def sort_symbols_by_line(symbols):
    def _key(sym):
        m = _SYMBOL_LINE_RE.search(sym)
        return int(m.group(1)) if m else 0
    return sorted(symbols, key=_key)


def _strip_html_comments_line(line, in_comment):
    """Blank out HTML comment spans on a line while preserving column indices."""
    out = []
    i = 0
    n = len(line)
    while i < n:
        if in_comment:
            end_pos = line.find('-->', i)
            if end_pos == -1:
                out.append(' ' * (n - i))
                return ''.join(out), True
            out.append(' ' * (end_pos + 3 - i))
            i = end_pos + 3
            in_comment = False
        else:
            start_pos = line.find('<!--', i)
            if start_pos == -1:
                out.append(line[i:])
                return ''.join(out), False
            out.append(line[i:start_pos])
            i = start_pos
            in_comment = True
    return ''.join(out), in_comment


def _has_arrow_after_params(lines, start_idx, open_paren_col):
    """Verify whether a JS `const/let/var name = (` assignment actually defines an arrow function."""
    n = len(lines)
    depth = 0
    in_block = False
    for i in range(start_idx, min(start_idx + 8, n)):
        line = lines[i]
        m = len(line)
        j = open_paren_col if i == start_idx else 0
        while j < m:
            ch = line[j]
            if in_block:
                if ch == '*' and j + 1 < m and line[j + 1] == '/':
                    in_block = False
                    j += 2
                    continue
                j += 1
                continue
            if line.startswith('//', j):
                break
            if line.startswith('/*', j):
                in_block = True
                j += 2
                continue
            if ch in ('"', "'", '`'):
                q = ch
                j += 1
                while j < m:
                    if line[j] == '\\':
                        j += 2
                        continue
                    if line[j] == q:
                        break
                    j += 1
                j += 1
                continue
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    rest = line[j + 1:].split('//', 1)[0].strip()
                    if '=>' in rest:
                        return True
                    if ';' in rest:
                        return False
                    if (not rest or rest.startswith(':')) and i + 1 < n:
                        nxt = lines[i + 1].split('//', 1)[0].strip()
                        if nxt.startswith('=>'):
                            return True
                    return False
            j += 1
    return False


def find_brace_block_end(
    lines,
    start_idx,
    line_comments=('//',),
    support_block_comments=True,
    is_go=False,
    is_js=False,
    max_header_lines=6,
):
    """Find 1-based closing line of a brace-delimited block starting at 0-based start_idx."""
    n = len(lines)
    if start_idx < 0 or start_idx >= n:
        return None

    brace_depth = 0
    paren_depth = 0
    saw_open = False
    in_block_comment = False
    in_go_raw = False
    tpl_stack = []  # for JS: 'tpl' (template text) or int (brace depth inside ${...})
    start_indent = len(lines[start_idx].expandtabs(4)) - len(lines[start_idx].expandtabs(4).lstrip(' '))

    for i in range(start_idx, n):
        line = lines[i]
        m = len(line)
        j = 0
        last_sig = ''
        while j < m:
            ch = line[j]
            if in_block_comment:
                if ch == '*' and j + 1 < m and line[j + 1] == '/':
                    in_block_comment = False
                    j += 2
                    continue
                j += 1
                continue

            if in_go_raw:
                if ch == '`':
                    in_go_raw = False
                j += 1
                continue

            if is_js and tpl_stack and tpl_stack[-1] == 'tpl':
                if ch == '\\':
                    j += 2
                    continue
                if ch == '$' and j + 1 < m and line[j + 1] == '{':
                    tpl_stack.append(0)
                    j += 2
                    continue
                if ch == '`':
                    tpl_stack.pop()
                    last_sig = '`'
                j += 1
                continue

            # Line comments
            comment_hit = False
            for prefix in line_comments:
                if line.startswith(prefix, j):
                    comment_hit = True
                    break
            if comment_hit:
                break

            # Block comments
            if support_block_comments and ch == '/' and j + 1 < m and line[j + 1] == '*':
                in_block_comment = True
                j += 2
                continue

            # JS single-line regex literal heuristic so /{'}/ inside regexes don't skew counts
            if is_js and ch == '/' and (j + 1 >= m or line[j + 1] not in ('/', '*')):
                before = line[:j].rstrip()
                is_regex_ctx = (
                    last_sig in ('', '=', '(', ',', ':', '[', '!', '?', '&', '|', '{', ';', '~', '^', '>')
                    or before.endswith(('return', 'typeof', 'throw', 'case', 'yield', 'await'))
                )
                if is_regex_ctx:
                    k = j + 1
                    in_class = False
                    closed = False
                    while k < m:
                        rc = line[k]
                        if rc == '\\':
                            k += 2
                            continue
                        if rc == '[':
                            in_class = True
                        elif rc == ']' and in_class:
                            in_class = False
                        elif rc == '/' and not in_class:
                            closed = True
                            break
                        k += 1
                    if closed:
                        last_sig = '/'
                        j = k + 1
                        continue

            # String literals
            if is_go and ch == '`':
                in_go_raw = True
                j += 1
                continue
            if is_js and ch == '`':
                tpl_stack.append('tpl')
                j += 1
                continue
            if ch in ('"', "'"):
                quote = ch
                j += 1
                while j < m:
                    if line[j] == '\\':
                        j += 2
                        continue
                    if line[j] == quote:
                        break
                    j += 1
                last_sig = quote
                j += 1
                continue

            if ch == '(':
                paren_depth += 1
            elif ch == ')':
                if paren_depth > 0:
                    paren_depth -= 1
            elif ch == '{':
                if is_js and tpl_stack and isinstance(tpl_stack[-1], int):
                    tpl_stack[-1] += 1
                else:
                    brace_depth += 1
                    if paren_depth == 0:
                        saw_open = True
            elif ch == '}':
                if is_js and tpl_stack and isinstance(tpl_stack[-1], int):
                    if tpl_stack[-1] == 0:
                        tpl_stack.pop()
                    else:
                        tpl_stack[-1] -= 1
                else:
                    brace_depth -= 1
                    if brace_depth < 0:
                        return None
            elif ch == ';' and not saw_open and brace_depth == 0 and paren_depth == 0:
                return i + 1

            if not ch.isspace():
                last_sig = ch
            j += 1

        if saw_open and brace_depth == 0 and paren_depth == 0 and not tpl_stack and not in_go_raw:
            return i + 1

        if not saw_open and paren_depth == 0 and not in_block_comment and not in_go_raw and not tpl_stack:
            if (i - start_idx) >= max_header_lines:
                return None
            # Prevent unbraced statements (e.g. Go type aliases, JS arrow expressions without braces)
            # from bleeding into the following function's braces.
            next_nonempty = None
            for k in range(i + 1, min(i + 4, n)):
                stripped_next = lines[k].strip()
                if stripped_next and not any(stripped_next.startswith(p) for p in line_comments):
                    next_nonempty = lines[k]
                    break
            if next_nonempty is None:
                return i + 1
            next_stripped = next_nonempty.lstrip()
            next_indent = len(next_nonempty.expandtabs(4)) - len(next_nonempty.expandtabs(4).lstrip(' '))
            if not next_stripped.startswith('{') and next_indent <= start_indent:
                return None

    return None


def find_python_block_end(lines, start_idx):
    """Find 1-based closing line of a Python class/def block using indentation."""
    n = len(lines)
    if start_idx < 0 or start_idx >= n:
        return None

    base_indent = len(lines[start_idx].expandtabs(4)) - len(lines[start_idx].expandtabs(4).lstrip(' '))
    depth = 0
    in_triple = None
    header_end = None

    for i in range(start_idx, min(start_idx + 25, n)):
        line = lines[i]
        m = len(line)
        j = 0
        while j < m:
            if in_triple:
                if line.startswith(in_triple, j):
                    in_triple = None
                    j += 3
                    continue
                j += 1
                continue
            if line.startswith('"""', j) or line.startswith("'''", j):
                in_triple = line[j:j + 3]
                j += 3
                continue
            ch = line[j]
            if ch == '#':
                break
            if ch in ('"', "'"):
                q = ch
                j += 1
                while j < m:
                    if line[j] == '\\':
                        j += 2
                        continue
                    if line[j] == q:
                        break
                    j += 1
                j += 1
                continue
            if ch in '([{':
                depth += 1
            elif ch in ')]}':
                if depth > 0:
                    depth -= 1
            elif ch == ':' and depth == 0:
                header_end = i
                rest = line[j + 1:].strip()
                if rest and not rest.startswith('#'):
                    return i + 1
                break
            j += 1
        if header_end is not None:
            break

    if header_end is None:
        return None

    last_content_line = header_end + 1
    in_triple = None
    for i in range(header_end + 1, n):
        line = lines[i]
        stripped = line.strip()
        if in_triple:
            last_content_line = i + 1
            # Walk line to update triple-quote state
            j = 0
            while j < len(line):
                if in_triple:
                    if line[j] == '\\':
                        j += 2
                        continue
                    if line.startswith(in_triple, j):
                        in_triple = None
                        j += 3
                        continue
                elif line.startswith('"""', j) or line.startswith("'''", j):
                    in_triple = line[j:j + 3]
                    j += 3
                    continue
                elif line[j] == '#':
                    break
                elif line[j] in ('"', "'"):
                    q = line[j]
                    j += 1
                    while j < len(line):
                        if line[j] == '\\':
                            j += 2
                            continue
                        if line[j] == q:
                            break
                        j += 1
                j += 1
            continue

        if not stripped or stripped.startswith('#'):
            continue

        indent = len(line.expandtabs(4)) - len(line.expandtabs(4).lstrip(' '))
        if indent <= base_indent:
            break

        last_content_line = i + 1
        j = 0
        while j < len(line):
            if in_triple:
                if line[j] == '\\':
                    j += 2
                    continue
                if line.startswith(in_triple, j):
                    in_triple = None
                    j += 3
                    continue
            elif line.startswith('"""', j) or line.startswith("'''", j):
                in_triple = line[j:j + 3]
                j += 3
                continue
            elif line[j] == '#':
                break
            elif line[j] in ('"', "'"):
                q = line[j]
                j += 1
                while j < len(line):
                    if line[j] == '\\':
                        j += 2
                        continue
                    if line[j] == q:
                        break
                    j += 1
            j += 1

    return last_content_line


def find_sql_stmt_end(lines, start_idx):
    """Find 1-based line ending with terminating ';' for a SQL statement."""
    n = len(lines)
    if start_idx < 0 or start_idx >= n:
        return None

    in_single = False
    in_block_comment = False
    dollar_tag = None

    for i in range(start_idx, n):
        line = lines[i]
        m = len(line)
        j = 0
        while j < m:
            if in_block_comment:
                if line[j] == '*' and j + 1 < m and line[j + 1] == '/':
                    in_block_comment = False
                    j += 2
                    continue
                j += 1
                continue
            if dollar_tag is not None:
                if line.startswith(dollar_tag, j):
                    j += len(dollar_tag)
                    dollar_tag = None
                    continue
                j += 1
                continue
            if in_single:
                if line[j] == "'":
                    if j + 1 < m and line[j + 1] == "'":
                        j += 2
                        continue
                    in_single = False
                j += 1
                continue

            if line.startswith('--', j):
                break
            if line.startswith('/*', j):
                in_block_comment = True
                j += 2
                continue
            if line[j] == "'":
                in_single = True
                j += 1
                continue
            if line[j] == '$':
                dm = re.match(r'\$(?:[a-zA-Z_][a-zA-Z0-9_]*)?\$', line[j:])
                if dm:
                    dollar_tag = dm.group(0)
                    j += len(dollar_tag)
                    continue
            if line[j] == ';':
                return i + 1
            j += 1

    return None


def find_html_block_end(lines, start_idx, tag_name, start_col=0):
    """Find 1-based closing line for an HTML block tag."""
    n = len(lines)
    if start_idx < 0 or start_idx >= n:
        return None

    is_raw_tag = tag_name in {'script', 'style'}
    tag_re = re.compile(
        rf'(<!--|-->|<(?P<close>/?){re.escape(tag_name)}\b(?P<rest>[^>]*)>)',
        re.IGNORECASE,
    )
    depth = 0
    in_comment = False
    saw_open = False

    for i in range(start_idx, n):
        line = lines[i]
        pos = start_col if i == start_idx else 0
        for m in tag_re.finditer(line, pos):
            tok = m.group(1)
            if not is_raw_tag:
                if tok == '<!--':
                    in_comment = True
                    continue
                if tok == '-->':
                    in_comment = False
                    continue
                if in_comment:
                    continue

            if m.group('close'):
                depth -= 1
                if saw_open and depth <= 0:
                    return i + 1
            else:
                rest = m.group('rest') or ''
                if rest.rstrip().endswith('/'):
                    if not saw_open:
                        return i + 1
                    continue
                depth += 1
                saw_open = True

    return None

def load_gitignore(root_path: Path):
    patterns = []
    gitignore_file = root_path / '.gitignore'
    if gitignore_file.is_file():
        try:
            with open(gitignore_file, 'r', encoding='utf-8-sig', errors='replace') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('!'):
                        pattern = line.rstrip('/').replace('\\', '/')
                        if pattern:
                            patterns.append(pattern)
        except Exception:
            pass
    return patterns

def is_ignored(rel_path_str: str, root_path: Path, gitignore_patterns: list) -> bool:
    norm_path = rel_path_str.replace('\\', '/')
    while norm_path.startswith('./') or norm_path.startswith('/'):
        norm_path = norm_path[2:] if norm_path.startswith('./') else norm_path[1:]
    parts = [p for p in norm_path.split('/') if p]
    for part in parts:
        if part in DEFAULT_IGNORES:
            return True
        if part.startswith('.') and part not in {'.', '..'}:
            if len(parts) > 1 and part in {'.vscode', '.idea'}:
                return True

    for pattern in gitignore_patterns:
        anchored = pattern.startswith('/')
        cleaned = pattern.lstrip('/')
        if anchored or '/' in cleaned:
            if fnmatch.fnmatch(norm_path, cleaned) or norm_path.startswith(cleaned + '/'):
                return True
        else:
            if fnmatch.fnmatch(norm_path, cleaned) or fnmatch.fnmatch(parts[-1] if parts else '', cleaned):
                return True
            if any(fnmatch.fnmatch(part, cleaned) for part in parts):
                return True
    return False

def _find_go_tmpl_end(lines, start_idx):
    """Find 1-based closing line of a Go {{define}} block tracking nested template blocks."""
    open_re = re.compile(r'\{\{-?\s*(?:if|range|with|define|block)\b')
    end_re = re.compile(r'\{\{-?\s*end\b')
    comment_open = re.compile(r'\{\{-?\s*/\*')
    comment_close = re.compile(r'\*/\s*-?\}\}')
    depth = 0
    in_comment = False

    for i in range(start_idx, len(lines)):
        line = lines[i]
        if in_comment:
            if comment_close.search(line):
                in_comment = False
            continue
        if comment_open.search(line) and not comment_close.search(line):
            in_comment = True
            continue
        # Strip inline Go template comments on the same line
        cleaned = re.sub(r'\{\{-?\s*/\*.*?\*/\s*-?\}\}', '', line)
        depth += len(open_re.findall(cleaned))
        ends = len(end_re.findall(cleaned))
        if ends:
            depth -= ends
            if depth <= 0:
                return i + 1
    return None


def parse_html_symbols(lines, skip_frontmatter=False):
    symbols = []
    id_pattern = re.compile(r'\bid=["\']([a-zA-Z0-9_\-]+)["\']')
    tag_pattern = re.compile(r'<(title|header|nav|main|section|article|aside|footer|form|table|template|script|link)\b([^>]*)>', re.IGNORECASE)
    any_id_tag_pattern = re.compile(r'<([a-zA-Z][a-zA-Z0-9\-]*)\b([^>]*\bid=["\']([a-zA-Z0-9_\-]+)["\'][^>]*)>', re.IGNORECASE)
    go_define_re = re.compile(r'\{\{-?\s*define\s+["\']([^"\']+)["\']\s*-?\}\}')
    close_script_re = re.compile(r'</script\b[^>]*>', re.IGNORECASE)
    landmark_tags = {'header', 'nav', 'main', 'section', 'article', 'aside', 'footer', 'form', 'table', 'template', 'script'}
    in_comment = False

    n = len(lines)
    i = 0
    if skip_frontmatter and n > 0 and lines[0].strip() == '---':
        for k in range(1, n):
            if lines[k].strip() == '---':
                i = k + 1
                break

    while i < n:
        idx = i + 1
        clean_line, in_comment = _strip_html_comments_line(lines[i], in_comment)
        if not clean_line.strip():
            i += 1
            continue

        for gm in go_define_re.finditer(clean_line):
            end_line = _find_go_tmpl_end(lines, i)
            symbols.append(format_symbol(f'define "{gm.group(1)}"', idx, end_line))

        # Track non-script segment on this line for standalone #id scan
        line_for_ids = clean_line
        pos = 0
        while True:
            m = tag_pattern.search(clean_line, pos)
            if not m:
                break
            pos = m.end()
            tag = m.group(1).lower()
            attrs = m.group(2)
            id_match = id_pattern.search(attrs)
            element_id = f' #{id_match.group(1)}' if id_match else ''

            if tag == 'title':
                title_match = re.search(r'<title[^>]*>(.*?)</title>', clean_line, re.IGNORECASE)
                val = f': "{title_match.group(1).strip()}"' if title_match else ''
                symbols.append(format_symbol(f'<title>{val}', idx))
            elif tag in {'header', 'nav', 'main', 'section', 'article', 'aside', 'footer', 'form', 'table'}:
                end_line = find_html_block_end(lines, i, tag, start_col=m.start())
                symbols.append(format_symbol(f'<{tag}{element_id}>', idx, end_line))
            elif tag == 'template' and element_id:
                end_line = find_html_block_end(lines, i, tag, start_col=m.start())
                symbols.append(format_symbol(f'<template{element_id}>', idx, end_line))
            elif tag == 'script':
                if 'src=' in attrs.lower():
                    src_match = re.search(r'src=["\']([^"\']+)["\']', attrs, re.IGNORECASE)
                    if src_match:
                        symbols.append(format_symbol(f'<script src="{src_match.group(1)}">', idx))
                else:
                    type_match = re.search(r'type=["\']([^"\']+)["\']', attrs, re.IGNORECASE)
                    type_suffix = f' type="{type_match.group(1)}"' if type_match else ''
                    end_line = find_html_block_end(lines, i, 'script', start_col=m.start())
                    symbols.append(format_symbol(f'<script{type_suffix}{element_id}>', idx, end_line))

                    # Skip inline <script> body so JS template strings aren't misread as HTML
                    line_for_ids = clean_line[:m.start()]
                    if end_line is None:
                        return sort_symbols_by_line(symbols)
                    if end_line == idx:
                        cm = close_script_re.search(clean_line, pos)
                        pos = cm.end() if cm else len(clean_line)
                    else:
                        i = end_line - 1
                        idx = i + 1
                        clean_line, in_comment = _strip_html_comments_line(lines[i], False)
                        cm = close_script_re.search(clean_line)
                        pos = cm.end() if cm else len(clean_line)
                        line_for_ids = clean_line[pos:]
            elif tag == 'link' and 'rel="stylesheet"' in attrs.lower() and 'href=' in attrs.lower():
                href_match = re.search(r'href=["\']([^"\']+)["\']', attrs, re.IGNORECASE)
                if href_match:
                    symbols.append(format_symbol(f'<link rel="stylesheet" href="{href_match.group(1)}">', idx))

        for im in any_id_tag_pattern.finditer(line_for_ids):
            if im.group(1).lower() not in landmark_tags:
                symbols.append(format_symbol(f'#{im.group(3)} <{im.group(1).lower()}>', idx))
        i += 1
    return sort_symbols_by_line(symbols)


def extract_inline_script_blocks(lines):
    """Return list of (0-based line_offset, masked_lines) for inline JS <script> blocks."""
    blocks = []
    open_re = re.compile(r'<script\b([^>]*)>', re.IGNORECASE)
    close_re = re.compile(r'</script\b[^>]*>', re.IGNORECASE)
    src_re = re.compile(r'\bsrc\s*=', re.IGNORECASE)
    type_re = re.compile(r'\btype\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)

    in_comment = False
    i = 0
    n = len(lines)
    while i < n:
        clean_line, in_comment = _strip_html_comments_line(lines[i], in_comment)
        pos = 0
        jumped = False
        for m in open_re.finditer(clean_line, pos):
            attrs = m.group(1) or ''
            if src_re.search(attrs):
                continue
            tm = type_re.search(attrs)
            if tm:
                tval = tm.group(1).strip().lower()
                if not ('javascript' in tval or tval == 'module'):
                    continue

            start_idx = i
            end_line = find_html_block_end(lines, start_idx, 'script', start_col=m.start())
            end_idx = (end_line - 1) if end_line else start_idx
            slice_lines = list(lines[start_idx:end_idx + 1])

            # Mask HTML wrapper tags with spaces while preserving 1-to-1 line indexing
            first = slice_lines[0]
            open_end_col = m.end()
            slice_lines[0] = (' ' * open_end_col) + first[open_end_col:]

            last = slice_lines[-1]
            search_from = open_end_col if start_idx == end_idx else 0
            cm = close_re.search(last, search_from)
            if cm:
                slice_lines[-1] = last[:cm.start()]

            blocks.append((start_idx, slice_lines))
            if end_idx > i:
                i = end_idx
                jumped = True
                break
        i += 1
        if jumped:
            in_comment = False
    return blocks


def parse_css_symbols(lines):
    symbols = []
    var_pattern = re.compile(r'^\s*(--[a-zA-Z0-9_\-]+)\s*:')
    id_rule = re.compile(r'^(#[a-zA-Z0-9_\-]+)\s*\{')
    class_rule = re.compile(r'^(\.[a-zA-Z0-9_\-]+)\s*\{')
    media_rule = re.compile(r'^(@media\b[^{]+)\{')
    keyframes_rule = re.compile(r'^(@keyframes\s+[a-zA-Z0-9_\-]+)\s*\{')
    in_block = False

    for idx, line in enumerate(lines, 1):
        sline = line.strip()
        if in_block:
            if '*/' in sline:
                in_block = False
            continue
        if sline.startswith('/*'):
            if '*/' not in sline[2:]:
                in_block = True
            continue
        if not sline or sline.startswith('*'):
            continue

        for rule_re, prefix in ((keyframes_rule, ''), (media_rule, '')):
            m = rule_re.match(sline)
            if m:
                end_line = find_brace_block_end(lines, idx - 1, line_comments=(), support_block_comments=True)
                label = re.sub(r'\s+', ' ', m.group(1)).strip()
                symbols.append(format_symbol(f'{prefix}{label}', idx, end_line))
                break
        else:
            v_match = var_pattern.match(sline)
            if v_match:
                symbols.append(format_symbol(f'var {v_match.group(1)}', idx))
                continue
            i_match = id_rule.match(sline)
            if i_match:
                end_line = find_brace_block_end(lines, idx - 1, line_comments=(), support_block_comments=True)
                symbols.append(format_symbol(f'id {i_match.group(1)}', idx, end_line))
                continue
            c_match = class_rule.match(sline)
            if c_match:
                end_line = find_brace_block_end(lines, idx - 1, line_comments=(), support_block_comments=True)
                symbols.append(format_symbol(f'class {c_match.group(1)}', idx, end_line))
    return symbols


def parse_markdown_symbols(lines):
    headings = []
    in_fence = False
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('```') or stripped.startswith('~~~'):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r'^(#{1,3})\s+(.+)$', stripped)
        if m:
            headings.append((idx, len(m.group(1)), f'{m.group(1)} {m.group(2).strip()}'))

    symbols = []
    total_lines = len(lines)
    for k, (start_line, level, label) in enumerate(headings):
        end_candidate = total_lines
        for next_start, next_level, _ in headings[k + 1:]:
            if next_level <= level:
                end_candidate = next_start - 1
                break
        while end_candidate > start_line and not lines[end_candidate - 1].strip():
            end_candidate -= 1
        symbols.append(format_symbol(label, start_line, end_candidate))
    return symbols


def _extract_sql_alter_action(lines, start_idx, end_line, table_name):
    last_idx = (end_line - 1) if end_line else start_idx
    chunk = []
    for line in lines[start_idx:last_idx + 1]:
        # Strip inline SQL comments for clean clause extraction
        clean = re.sub(r'--.*$', '', line).strip()
        if clean:
            chunk.append(clean)
    joined = ' '.join(chunk).rstrip(';').strip()
    m = re.match(
        rf'ALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:ONLY\s+)?{re.escape(table_name)}\s+(.*)$',
        joined,
        re.IGNORECASE,
    )
    if not m:
        return ''
    rest = re.sub(r'\bIF\s+(?:NOT\s+)?EXISTS\b', '', m.group(1), flags=re.IGNORECASE)
    rest = re.sub(r'\s+', ' ', rest).strip()
    if not rest:
        return ''

    m_col = re.match(r'^(ADD|DROP|RENAME|ALTER)\s+(COLUMN|CONSTRAINT)\s+([a-zA-Z0-9_."`]+)', rest, re.IGNORECASE)
    if m_col:
        return f'{m_col.group(1).upper()} {m_col.group(2).upper()} {m_col.group(3)}'

    m_rls = re.match(r'^(ENABLE|DISABLE|FORCE|NO\s+FORCE)\s+ROW\s+LEVEL\s+SECURITY\b', rest, re.IGNORECASE)
    if m_rls:
        return f'{re.sub(r"\\s+", " ", m_rls.group(1).upper())} ROW LEVEL SECURITY'

    m_add_short = re.match(r'^ADD\s+([a-zA-Z0-9_."`]+)\b', rest, re.IGNORECASE)
    if m_add_short:
        return f'ADD {m_add_short.group(1)}'

    words = rest.split(',')[0].split()[:4]
    summary = ' '.join(words)
    return summary[:36].rstrip()


def parse_sql_symbols(lines):
    symbols = []
    create_re = re.compile(
        r'^\s*CREATE\s+(?:OR\s+REPLACE\s+)?(?:UNIQUE\s+)?(TABLE|VIEW|INDEX|FUNCTION|PROCEDURE|TRIGGER|POLICY)\s+(?:CONCURRENTLY\s+)?(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z0-9_."`]+)',
        re.IGNORECASE,
    )
    alter_re = re.compile(
        r'^\s*ALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:ONLY\s+)?([a-zA-Z0-9_."`]+)',
        re.IGNORECASE,
    )
    in_block_comment = False
    for idx, line in enumerate(lines, 1):
        sline = line.strip()
        if in_block_comment:
            if '*/' in sline:
                in_block_comment = False
            continue
        if sline.startswith('/*'):
            if '*/' not in sline[2:]:
                in_block_comment = True
            continue
        if not sline or sline.startswith('--'):
            continue

        cm = create_re.match(line)
        if cm:
            end_line = find_sql_stmt_end(lines, idx - 1)
            symbols.append(format_symbol(f'{cm.group(1).upper()} {cm.group(2)}', idx, end_line))
            continue

        am = alter_re.match(line)
        if am:
            end_line = find_sql_stmt_end(lines, idx - 1)
            action = _extract_sql_alter_action(lines, idx - 1, end_line, am.group(1))
            label = f'ALTER TABLE {am.group(1)}'
            if action:
                label += f' [{action}]'
            symbols.append(format_symbol(label, idx, end_line))
    return symbols


def _extract_call_signature(lines, start_idx, open_paren_col, lang='go', max_lines=3, max_param_len=56, max_ret_len=28):
    """Extract compact single-line '(params) ret' suffix from a declaration header."""
    if start_idx < 0 or start_idx >= len(lines) or open_paren_col < 0:
        return ''
    line0 = lines[start_idx]
    if open_paren_col >= len(line0) or line0[open_paren_col] != '(':
        return ''

    depth = 0
    in_quote = None
    escaped = False
    params_chars = []
    tail_buf = []
    closed_at_tail = False
    limit = min(len(lines), start_idx + max_lines)

    for r in range(start_idx, limit):
        raw = lines[r]
        c_start = open_paren_col if r == start_idx else 0
        for c in range(c_start, len(raw)):
            ch = raw[c]
            if closed_at_tail:
                tail_buf.append(ch)
                continue
            if escaped:
                escaped = False
                if depth > 0:
                    params_chars.append(ch)
                continue
            if ch == '\\' and in_quote in {'"', "'"}:
                escaped = True
                if depth > 0:
                    params_chars.append(ch)
                continue
            if in_quote:
                if ch == in_quote:
                    in_quote = None
                if depth > 0:
                    params_chars.append(ch)
                continue
            if ch in {'"', "'", '`'}:
                in_quote = ch
                if depth > 0:
                    params_chars.append(ch)
                continue
            if ch == '(':
                depth += 1
                if depth > 1:
                    params_chars.append(ch)
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    closed_at_tail = True
                elif depth > 0:
                    params_chars.append(ch)
            elif depth > 0:
                params_chars.append(ch)
        if closed_at_tail and ('{' in ''.join(tail_buf) or '=>' in ''.join(tail_buf) or (lang == 'py' and ':' in ''.join(tail_buf))):
            break

    if not closed_at_tail:
        return '(...)'

    params = re.sub(r'\s+', ' ', ''.join(params_chars)).strip()
    if len(params) > max_param_len:
        params = params[:max_param_len - 3].rstrip() + '...'

    tail = re.sub(r'\s+', ' ', ''.join(tail_buf)).strip()
    if lang == 'py':
        tail = tail.split(':', 1)[0].strip()
    elif lang == 'rs':
        tail = re.split(r'\{|\bwhere\b', tail, 1)[0].strip()
    elif lang == 'js':
        if '=>' in tail:
            tail = tail.split('=>', 1)[0].strip()
        elif '{' in tail:
            tail = tail.split('{', 1)[0].strip()
    else:
        tail = tail.split('{', 1)[0].strip()

    ret = ''
    if tail and lang in {'go', 'py', 'rs', 'js'}:
        if lang == 'js' and not tail.startswith(':'):
            ret = ''
        else:
            ret = tail
            if len(ret) > max_ret_len:
                ret = ret[:max_ret_len - 3].rstrip() + '...'

    sep = '' if (lang == 'js' and ret.startswith(':')) else ' '
    return f'({params})' + (f'{sep}{ret}' if ret else '')


def parse_go_symbols(lines, line_offset=0, include_signatures=False):
    symbols = []
    fn_re = re.compile(r'^\s*func\s+(?:\(([^)]+)\)\s+)?([a-zA-Z0-9_]+)(?:\[[^\]]+\])?\s*\(')
    type_re = re.compile(r'^\s*type\s+([a-zA-Z0-9_]+)(?:\[[^\]]+\])?\s+(struct|interface)\b')
    type_group_open_re = re.compile(r'^\s*type\s*\(\s*(?://.*)?$')
    type_group_member_re = re.compile(r'^\s*([a-zA-Z0-9_]+)(?:\[[^\]]+\])?\s+(struct|interface)\b')
    route_re = re.compile(r'\.[Hh]andle(?:Func)?\s*\(\s*(?:["`]([^"`]+)["`])?')
    route_cont_str_re = re.compile(r'^\s*["`]([^"`]+)["`]')

    in_block_comment = False
    in_raw = False
    in_type_group = False
    n = len(lines)

    for idx, line in enumerate(lines, 1):
        sline = line.strip()
        if in_block_comment:
            if '*/' in sline:
                in_block_comment = False
            continue
        if in_raw:
            if sline.count('`') % 2 == 1:
                in_raw = False
            continue
        if sline.startswith('/*'):
            if '*/' not in sline[2:]:
                in_block_comment = True
            continue
        if not sline or sline.startswith('//'):
            continue

        code_no_comment = sline.split('//', 1)[0]

        if in_type_group:
            if code_no_comment.startswith(')'):
                in_type_group = False
                continue
            tm = type_group_member_re.match(line)
            if tm:
                end_line = find_brace_block_end(lines, idx - 1, is_go=True)
                end_abs = (end_line + line_offset) if end_line else None
                symbols.append(format_symbol(f'type {tm.group(1)} {tm.group(2)}', idx + line_offset, end_abs))
                continue

        if type_group_open_re.match(line):
            in_type_group = True
            continue

        tm = type_re.match(line)
        if tm:
            end_line = find_brace_block_end(lines, idx - 1, is_go=True)
            end_abs = (end_line + line_offset) if end_line else None
            symbols.append(format_symbol(f'type {tm.group(1)} {tm.group(2)}', idx + line_offset, end_abs))
            continue

        fm = fn_re.match(line)
        if fm:
            recv_raw, fn_name = fm.group(1), fm.group(2)
            if recv_raw:
                recv_type = recv_raw.strip().split()[-1].lstrip('*')
                recv_type = re.sub(r'\[.*\]$', '', recv_type)
                base_label = f'func ({recv_type}) {fn_name}'
            else:
                base_label = f'func {fn_name}'
            sig = _extract_call_signature(lines, idx - 1, fm.end() - 1, lang='go') if include_signatures else ''
            end_line = find_brace_block_end(lines, idx - 1, is_go=True)
            end_abs = (end_line + line_offset) if end_line else None
            symbols.append(format_symbol(f'{base_label}{sig}', idx + line_offset, end_abs))
            continue

        # Check Go 1.22+ mux.Handle / HandleFunc routes outside string literals
        rm = route_re.search(code_no_comment)
        if rm:
            route_pat = rm.group(1)
            if not route_pat and idx < n:
                nxt = lines[idx].strip().split('//', 1)[0]
                cm = route_cont_str_re.match(nxt)
                if cm:
                    route_pat = cm.group(1)
            if route_pat:
                symbols.append(format_symbol(f'route {route_pat}', idx + line_offset))

        if code_no_comment.count('`') % 2 == 1:
            in_raw = True

    return symbols


def parse_code_symbols(lines, ext, line_offset=0, include_signatures=False):
    if ext == '.go':
        return parse_go_symbols(lines, line_offset=line_offset, include_signatures=include_signatures)

    symbols = []

    # Python
    if ext == '.py':
        cls_def = re.compile(r'^\s*(class\s+[a-zA-Z0-9_]+(?:\([^)]*\))?):')
        fn_def = re.compile(r'^\s*((?:async\s+)?def\s+[a-zA-Z0-9_]+\s*\([^)]*\))(?:\s*->\s*([^:]+))?:')
        fn_multi_def = re.compile(r'^\s*((?:async\s+)?def\s+[a-zA-Z0-9_]+)\s*\(')
        route_def = re.compile(r'^\s*(@(?:app|router|blueprint)\.(?:get|post|put|delete|patch|route)\([^)]*\))')

        for idx, line in enumerate(lines, 1):
            sline = line.strip()
            if not sline or sline.startswith('#'):
                continue
            r_match = route_def.match(line)
            if r_match:
                symbols.append(format_symbol(r_match.group(1), idx + line_offset))
                continue
            c_match = cls_def.match(line)
            if c_match:
                end_line = find_python_block_end(lines, idx - 1)
                end_abs = (end_line + line_offset) if end_line else None
                symbols.append(format_symbol(c_match.group(1), idx + line_offset, end_abs))
                continue
            f_match = fn_def.match(line) or fn_multi_def.match(line)
            if f_match:
                end_line = find_python_block_end(lines, idx - 1)
                end_abs = (end_line + line_offset) if end_line else None
                if f_match.re is fn_def:
                    label = f_match.group(1)
                    if include_signatures and f_match.group(2):
                        ret = re.sub(r'\s+', ' ', f_match.group(2)).strip()
                        label = f'{label} -> {ret[:24]}'
                else:
                    if include_signatures:
                        sig = _extract_call_signature(lines, idx - 1, f_match.end() - 1, lang='py')
                        label = f'{f_match.group(1)}{sig}'
                    else:
                        label = f'{f_match.group(1)}(...)'
                symbols.append(format_symbol(label, idx + line_offset, end_abs))

    # JavaScript / TypeScript / JSX / TSX
    elif ext in {'.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'}:
        patterns = [
            ('class', re.compile(r'^\s*(?:export\s+(?:default\s+)?)?(?:abstract\s+)?class\s+([a-zA-Z0-9_]+)')),
            ('interface', re.compile(r'^\s*(?:export\s+(?:default\s+)?)?interface\s+([a-zA-Z0-9_]+)')),
            ('type', re.compile(r'^\s*(?:export\s+)?type\s+([a-zA-Z0-9_]+)\s*=')),
            ('fn', re.compile(r'^\s*(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+([a-zA-Z0-9_]+)\s*\(')),
            ('arrow_paren', re.compile(r'^\s*(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?\(')),
            ('fn_arrow_id', re.compile(r'^\s*(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?([a-zA-Z0-9_]+)\s*=>')),
            ('fn_assign', re.compile(r'^\s*((?:window|globalThis|exports|module\.exports)\.[a-zA-Z0-9_]+)\s*=\s*(?:async\s+)?(?:function\b|\([^)]*\)\s*=>)')),
            ('route', re.compile(r'^\s*(?:router|app)\.(get|post|put|delete|patch|use)\s*\(\s*[\'"`]([^\'"`]+)[\'"`]')),
        ]
        in_block_comment = False
        for idx, line in enumerate(lines, 1):
            sline = line.strip()
            if in_block_comment:
                if '*/' in sline:
                    in_block_comment = False
                continue
            if sline.startswith('/*'):
                if '*/' not in sline[2:]:
                    in_block_comment = True
                continue
            if not sline or sline.startswith('//') or sline.startswith('*'):
                continue
            for kind, p in patterns:
                m = p.match(line)
                if not m:
                    continue
                if kind == 'arrow_paren' and not _has_arrow_after_params(lines, idx - 1, m.end() - 1):
                    continue
                if kind == 'route':
                    symbols.append(format_symbol(f'route {m.group(1).upper()} {m.group(2)}', idx + line_offset))
                    break
                end_line = find_brace_block_end(lines, idx - 1, is_js=True)
                end_abs = (end_line + line_offset) if end_line else None
                if kind in {'class', 'interface', 'type'}:
                    label = f'{kind} {m.group(1)}'
                elif include_signatures:
                    if kind == 'fn_arrow_id':
                        sig = f'({m.group(2)})'
                    else:
                        paren_pos = line.find('(', m.end() - 1 if kind in {'fn', 'arrow_paren'} else m.start())
                        sig = _extract_call_signature(lines, idx - 1, paren_pos, lang='js') if paren_pos >= 0 else '()'
                    label = f'fn {m.group(1)}{sig or "()"}'
                else:
                    label = f'fn {m.group(1)}()'
                symbols.append(format_symbol(label, idx + line_offset, end_abs))
                break

    # Rust / PowerShell
    elif ext == '.rs':
        rs_re = re.compile(r'^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(fn|struct|enum|trait|impl|mod)\s+([a-zA-Z0-9_<>\[\]:]+)')
        for idx, line in enumerate(lines, 1):
            sline = line.strip()
            if sline.startswith('//') or sline.startswith('/*'):
                continue
            m = rs_re.match(line)
            if m:
                end_line = find_brace_block_end(lines, idx - 1)
                end_abs = (end_line + line_offset) if end_line else None
                sig = ''
                if include_signatures and m.group(1) == 'fn':
                    paren_pos = line.find('(', m.end())
                    if paren_pos >= 0:
                        sig = _extract_call_signature(lines, idx - 1, paren_pos, lang='rs')
                symbols.append(format_symbol(f'{m.group(1)} {m.group(2)}{sig}', idx + line_offset, end_abs))

    elif ext in {'.ps1', '.psm1'}:
        ps_re = re.compile(r'^\s*(function|filter|class)\s+([a-zA-Z0-9_\-]+)', re.IGNORECASE)
        for idx, line in enumerate(lines, 1):
            sline = line.strip()
            if sline.startswith('#'):
                continue
            m = ps_re.match(line)
            if m:
                end_line = find_brace_block_end(lines, idx - 1, line_comments=('#',), support_block_comments=False)
                end_abs = (end_line + line_offset) if end_line else None
                symbols.append(format_symbol(f'{m.group(1).lower()} {m.group(2)}', idx + line_offset, end_abs))

    # Java / C# / C / C++ / PHP
    elif ext in {'.java', '.cs', '.php', '.c', '.cpp', '.h', '.hpp'}:
        cls_p = re.compile(r'^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:class|interface|struct|enum)\s+([a-zA-Z0-9_]+)')
        fn_p = re.compile(r'^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:async\s+)?[a-zA-Z0-9_<>[\]]+\s+([a-zA-Z0-9_]+)\s*\([^;{}]*\)\s*\{')
        php_fn = re.compile(r'^\s*(?:public|private|protected)?\s*(?:static\s+)?function\s+([a-zA-Z0-9_]+)\s*\(')
        comments = ('//', '#') if ext == '.php' else ('//',)

        for idx, line in enumerate(lines, 1):
            sline = line.strip()
            if sline.startswith('//') or sline.startswith('/*') or sline.startswith('*') or sline.startswith('#'):
                continue

            if ext == '.php':
                pm = php_fn.match(line)
                if pm:
                    end_line = find_brace_block_end(lines, idx - 1, line_comments=comments)
                    end_abs = (end_line + line_offset) if end_line else None
                    sig = _extract_call_signature(lines, idx - 1, pm.end() - 1, lang='c') if include_signatures else ''
                    symbols.append(format_symbol(f'function {pm.group(1)}{sig}', idx + line_offset, end_abs))
                    continue

            cm = cls_p.match(line)
            if cm:
                end_line = find_brace_block_end(lines, idx - 1, line_comments=comments)
                end_abs = (end_line + line_offset) if end_line else None
                symbols.append(format_symbol(f'class/type {cm.group(1)}', idx + line_offset, end_abs))
                continue
            fm = fn_p.match(line)
            if fm and fm.group(1) not in {'if', 'for', 'while', 'switch', 'catch'}:
                end_line = find_brace_block_end(lines, idx - 1, line_comments=comments)
                end_abs = (end_line + line_offset) if end_line else None
                sig = '()'
                if include_signatures:
                    paren_pos = line.find('(', fm.start(1))
                    sig = _extract_call_signature(lines, idx - 1, paren_pos, lang='c') if paren_pos >= 0 else '()'
                symbols.append(format_symbol(f'method {fm.group(1)}{sig}', idx + line_offset, end_abs))

    return symbols

def parse_yaml_symbols(lines):
    symbols = []
    container_keys = {'services', 'jobs', 'networks', 'volumes', 'stages', 'targets', 'routes', 'plugins', 'inputs', 'outputs'}
    key_re = re.compile(r'^(\s*)([a-zA-Z0-9_.\-/]+)\s*:(?:\s*(.*))?$')
    parent_key = None
    parent_indent = None
    child_indent = None
    n = len(lines)

    def _find_yaml_end(start_idx, base_indent):
        last = start_idx + 1
        for k in range(start_idx + 1, n):
            raw = lines[k]
            s = raw.strip()
            if not s or s.startswith('#'):
                continue
            ind = len(raw) - len(raw.lstrip(' '))
            if ind <= base_indent and not s.startswith('- '):
                break
            last = k + 1
        return last if last > start_idx + 1 else None

    for idx, line in enumerate(lines, 1):
        s = line.strip()
        if not s or s.startswith('#') or s in {'---', '...'}:
            continue
        m = key_re.match(line.rstrip('\r\n'))
        if not m or m.group(2).startswith('-'):
            continue
        indent = len(m.group(1))
        key = m.group(2)
        if indent == 0:
            parent_key = key if key in container_keys else None
            parent_indent = indent if parent_key else None
            child_indent = None
            end_line = _find_yaml_end(idx - 1, indent)
            symbols.append(format_symbol(f'key {key}', idx, end_line))
        elif parent_key and parent_indent is not None and indent > parent_indent:
            if child_indent is None:
                child_indent = indent
            if indent == child_indent:
                end_line = _find_yaml_end(idx - 1, indent)
                symbols.append(format_symbol(f'{parent_key}.{key}', idx, end_line))
    return symbols


def parse_json_symbols(lines):
    if len(lines) > 1500:
        return []
    symbols = []
    child_sections = {'scripts', 'targets', 'compilerOptions'}
    key_re = re.compile(r'^\s*"([^"]+)"\s*:')
    depth = 0
    in_string = False
    escape = False
    active_section = None

    for idx, line in enumerate(lines, 1):
        if depth in {1, 2}:
            km = key_re.match(line)
            if km:
                key = km.group(1)
                if depth == 1:
                    active_section = key if key in child_sections else None
                    symbols.append(format_symbol(f'key "{key}"', idx))
                elif depth == 2 and active_section:
                    symbols.append(format_symbol(f'{active_section}.{key}', idx))

        for ch in line:
            if escape:
                escape = False
                continue
            if ch == '\\' and in_string:
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth = max(0, depth - 1)
                if depth <= 1:
                    active_section = None
    return symbols


def parse_makefile_symbols(lines):
    symbols = []
    target_re = re.compile(r'^([a-zA-Z0-9_.\-/]+)\s*:(?!=)')
    for idx, line in enumerate(lines, 1):
        s = line.strip()
        if not s or s.startswith('#') or line.startswith('\t'):
            continue
        m = target_re.match(line)
        if m and not m.group(1).startswith('.'):
            symbols.append(format_symbol(f'target {m.group(1)}', idx))
    return symbols


def parse_dockerfile_symbols(lines):
    symbols = []
    inst_re = re.compile(r'^\s*(FROM|EXPOSE|ENTRYPOINT|CMD)\s+(.+)$', re.IGNORECASE)
    for idx, line in enumerate(lines, 1):
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        m = inst_re.match(s)
        if m:
            val = re.sub(r'\s+', ' ', m.group(2)).strip()[:50]
            symbols.append(format_symbol(f'{m.group(1).upper()} {val}', idx))
    return symbols


def _read_go_module_name(root_path: Path):
    gomod = root_path / 'go.mod'
    if not gomod.is_file():
        return None
    try:
        with open(gomod, 'r', encoding='utf-8-sig', errors='replace') as f:
            for line in f:
                m = re.match(r'^\s*module\s+(\S+)', line)
                if m:
                    return m.group(1).strip()
    except Exception:
        pass
    return None


def extract_file_refs(lines, ext, fname='', go_module=None):
    """Extract lightweight internal imports, assets, templates, and endpoint refs."""
    refs = []
    text_joined = None

    if ext == '.go':
        in_import = False
        import_str_re = re.compile(r'"([^"]+)"')
        tmpl_re = re.compile(r'["`]([a-zA-Z0-9_./\-]+\.html)["`]')
        for line in lines:
            s = line.strip()
            if s.startswith('//'):
                continue
            if re.match(r'^import\s*\(', s):
                in_import = True
                continue
            if in_import:
                if s.startswith(')'):
                    in_import = False
                    continue
                m = import_str_re.search(s)
                if m:
                    imp = m.group(1)
                    if (go_module and imp.startswith(go_module + '/')) or '/internal/' in imp or imp.startswith('internal/'):
                        short_imp = imp[len(go_module) + 1:] if (go_module and imp.startswith(go_module + '/')) else imp
                        refs.append(f'pkg:{short_imp}')
            elif s.startswith('import '):
                m = import_str_re.search(s)
                if m:
                    imp = m.group(1)
                    if (go_module and imp.startswith(go_module + '/')) or '/internal/' in imp:
                        short_imp = imp[len(go_module) + 1:] if (go_module and imp.startswith(go_module + '/')) else imp
                        refs.append(f'pkg:{short_imp}')
            for tm in tmpl_re.finditer(line):
                refs.append(f'tmpl:{tm.group(1)}')

    elif ext in {'.html', '.htm', '.astro', '.svelte', '.vue'}:
        text_joined = ''.join(lines)
        for m in re.finditer(r'<(?:script[^>]+src|link[^>]+href)=["\']([^"\']+)["\']', text_joined, re.IGNORECASE):
            refs.append(m.group(1))
        for m in re.finditer(r'\{\{-?\s*(?:template|block)\s+["\']([^"\']+)["\']', text_joined):
            refs.append(f'tmpl:{m.group(1)}')
        for m in re.finditer(r'\bfetch\s*\(\s*[\'"`](/[^\'`"\s)]+)', text_joined):
            refs.append(f'api:{m.group(1)}')

    elif ext in {'.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'}:
        text_joined = ''.join(lines)
        for m in re.finditer(r'(?:from\s+|import\s*\(|require\s*\()\s*[\'"`](\.\.?/[^\'"]+)[\'"`]', text_joined):
            refs.append(m.group(1))
        for m in re.finditer(r'\bfetch\s*\(\s*[\'"`](/[^\'`"\s)]+)', text_joined):
            refs.append(f'api:{m.group(1)}')

    elif ext == '.py':
        for line in lines:
            m = re.match(r'^\s*from\s+(\.[a-zA-Z0-9_\.]*)\s+import\b', line)
            if m:
                refs.append(m.group(1))

    return list(dict.fromkeys(refs))


def iter_project_files(root_path: Path, gitignore_patterns: list):
    """Yield (rel_file_path, full_file_path, fname, ext) for all non-ignored indexable files."""
    for dirpath, dirnames, filenames in os.walk(root_path):
        rel_dir = os.path.relpath(dirpath, root_path)
        if rel_dir == '.':
            rel_dir = ''
        dirnames[:] = sorted(d for d in dirnames if not is_ignored(os.path.join(rel_dir, d), root_path, gitignore_patterns))
        for fname in sorted(filenames):
            rel_file_path = os.path.normpath(os.path.join(rel_dir, fname)).replace('\\', '/')
            if is_ignored(rel_file_path, root_path, gitignore_patterns):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext in BINARY_EXTENSIONS or fname in {CACHE_FILENAME, '.repo-map.md'}:
                continue
            if ext == '.json' and any(fname.lower().endswith(sfx) for sfx in SKIP_JSON_SUFFIXES):
                continue
            yield rel_file_path, Path(dirpath) / fname, fname, ext


def parse_file_content(lines, fname, ext, go_module=None, include_signatures=False):
    """Parse symbols and cross-file refs for a single file."""
    symbols = []
    lower_name = fname.lower()

    if ext in {'.html', '.htm'}:
        symbols = parse_html_symbols(lines)
        for block_offset, block_lines in extract_inline_script_blocks(lines):
            symbols.extend(parse_code_symbols(block_lines, '.js', line_offset=block_offset, include_signatures=include_signatures))
        symbols = sort_symbols_by_line(symbols)
    elif ext in {'.astro', '.svelte', '.vue'}:
        symbols = sort_symbols_by_line(
            parse_code_symbols(lines, '.ts', include_signatures=include_signatures)
            + parse_html_symbols(lines, skip_frontmatter=(ext == '.astro'))
        )
    elif ext in {'.css', '.scss', '.sass'}:
        symbols = parse_css_symbols(lines)
    elif ext in {'.md', '.mdx'}:
        symbols = parse_markdown_symbols(lines)
    elif ext == '.sql':
        symbols = parse_sql_symbols(lines)
    elif ext in {'.yml', '.yaml'}:
        symbols = parse_yaml_symbols(lines)
    elif ext == '.json':
        symbols = parse_json_symbols(lines)
    elif lower_name in {'makefile', 'gnumakefile'} or ext == '.mk':
        symbols = parse_makefile_symbols(lines)
    elif lower_name.startswith('dockerfile') or ext == '.dockerfile':
        symbols = parse_dockerfile_symbols(lines)
    elif ext in {'.py', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.java', '.cs', '.go', '.php', '.c', '.cpp', '.h', '.hpp', '.rs', '.ps1', '.psm1'}:
        symbols = parse_code_symbols(lines, ext, include_signatures=include_signatures)

    refs = extract_file_refs(lines, ext, fname=fname, go_module=go_module)
    return symbols, refs


def load_cache(cache_file: Path):
    if not cache_file.is_file():
        return None
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data.get('__schema_version__') == CACHE_SCHEMA_VERSION and isinstance(data.get('files'), dict):
            return data
    except Exception:
        pass
    return None


def get_project_file_snapshot(root_path: Path, gitignore_patterns: list):
    snapshot = {}
    for rel_file_path, full_file_path, _, _ in iter_project_files(root_path, gitignore_patterns):
        try:
            st = full_file_path.stat()
            snapshot[rel_file_path] = {'mtime': st.st_mtime, 'size': st.st_size}
        except Exception:
            pass
    return snapshot


def scan_project(root_dir: str, cached_files=None, include_signatures=False):
    root_path = Path(root_dir).resolve()
    gitignore_patterns = load_gitignore(root_path)
    go_module = _read_go_module_name(root_path)
    cached_files = cached_files or {}

    file_entries = []
    new_cache_files = {}
    reparsed_count = 0

    for rel_file_path, full_file_path, fname, ext in iter_project_files(root_path, gitignore_patterns):
        try:
            st = full_file_path.stat()
            mtime, size = st.st_mtime, st.st_size
        except Exception:
            continue

        cached = cached_files.get(rel_file_path)
        if (
            isinstance(cached, dict)
            and cached.get('mtime') == mtime
            and cached.get('size') == size
            and isinstance(cached.get('symbols'), list)
        ):
            line_count = cached.get('lines', 0)
            symbols = cached['symbols']
            refs = cached.get('refs', [])
        else:
            try:
                with open(full_file_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                    lines = f.readlines()
            except Exception:
                continue
            line_count = len(lines)
            symbols, refs = parse_file_content(
                lines, fname, ext, go_module=go_module, include_signatures=include_signatures
            )
            reparsed_count += 1

        entry = {
            'path': rel_file_path,
            'lines': line_count,
            'symbols': symbols,
            'refs': refs,
        }
        file_entries.append(entry)
        new_cache_files[rel_file_path] = {
            'mtime': mtime,
            'size': size,
            'lines': line_count,
            'symbols': symbols,
            'refs': refs,
        }

    return file_entries, new_cache_files, reparsed_count


def is_test_file(rel_path: str) -> bool:
    norm = rel_path.replace('\\', '/').lower()
    fname = os.path.basename(norm)
    parts = norm.split('/')
    if any(p in {'tests', '__tests__', 'test'} for p in parts[:-1]):
        return True
    return (
        fname.endswith('_test.go')
        or fname.endswith('_test.py')
        or fname.startswith('test_') and fname.endswith('.py')
        or '.test.' in fname
        or '.spec.' in fname
    )


def _format_entry_symbols(entry, max_symbols=60, compact=False):
    syms = entry['symbols']
    if not syms:
        return ""
    p = entry['path']
    ext = os.path.splitext(p)[1].lower()
    indent = "  "

    if compact and is_test_file(p):
        test_count = sum(1 for s in syms if 'test' in s.lower())
        count_label = test_count or len(syms)
        return f"\n{indent}  - [{count_label} test symbols omitted in --compact; use --find]"

    if compact and ext in {'.css', '.scss', '.sass'}:
        vars_count = sum(1 for s in syms if s.startswith('var '))
        structural = [s for s in syms if s.startswith(('@media', '@keyframes', 'id #'))]
        kept = structural[:20]
        omitted = len(syms) - len(kept)
        lines_out = [f"{indent}  - {s}" for s in kept]
        if omitted > 0:
            lines_out.append(f"{indent}  - ... ({vars_count} vars, {omitted} selectors omitted in --compact; use --find)")
        return "\n" + "\n".join(lines_out)

    shown = syms[:max_symbols] if max_symbols > 0 else syms
    sym_items = [f"{indent}  - {s}" for s in shown]
    if max_symbols > 0 and len(syms) > max_symbols:
        sym_items.append(f"{indent}  - ... (+{len(syms) - max_symbols} more; use --find)")
    return "\n" + "\n".join(sym_items)


def _filter_by_scope(file_entries, scope=None):
    if not scope:
        return file_entries
    s = scope.strip().strip('/').lower()
    return [e for e in file_entries if s in e['path'].lower()]


def generate_markdown(file_entries, root_name="Project", max_symbols=60, compact=False, no_wiring=False):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_files = len(file_entries)
    total_lines = sum(e['lines'] for e in file_entries)

    md = []
    md.append(f"# Codebase Skeleton & Repository Map: {root_name}")
    md.append(f"> **Updated:** {now_str} | **Total Files:** {total_files} | **Total LOC:** {total_lines}")
    md.append("> **Rule for Agents:** Read this map first. Identify exact files and line ranges (`Lxx` or `Lxx-Lyy`) before reading or modifying code. Never scan whole directories blindly.\n")
    md.append("## Directory Tree & Symbol Index\n")

    current_folder = None
    for entry in file_entries:
        p = entry['path']
        folder = os.path.dirname(p) or "/"
        fname = os.path.basename(p)

        if folder != current_folder:
            current_folder = folder
            md.append(f"\n### `{current_folder}`")

        sym_str = _format_entry_symbols(entry, max_symbols=max_symbols, compact=compact)
        md.append(f"- **`{fname}`** (Lines: {entry['lines']}){sym_str}")

    if not no_wiring:
        wiring_lines = []
        for entry in file_entries:
            refs = entry.get('refs') or []
            if not refs:
                continue
            shown_refs = refs[:8]
            suffix = f" (+{len(refs) - 8} more)" if len(refs) > 8 else ""
            wiring_lines.append(f"- `{entry['path']}` -> {', '.join(f'`{r}`' for r in shown_refs)}{suffix}")
        if wiring_lines:
            md.append("\n## Cross-References & Wiring\n")
            md.extend(wiring_lines)

    return "\n".join(md)


def search_symbols(file_entries, query, scope=None, use_regex=False):
    scoped = _filter_by_scope(file_entries, scope)
    if use_regex:
        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error as exc:
            print(f"[RepoMap] Invalid regex '{query}': {exc}", file=sys.stderr)
            sys.exit(1)
        matcher = lambda text: bool(pattern.search(text))
    else:
        terms = [t.strip().lower() for t in query.split('|') if t.strip()]
        if not terms:
            return []
        matcher = lambda text: any(t in text.lower() for t in terms)

    matches = []
    for entry in scoped:
        p = entry['path']
        syms = entry['symbols']
        refs = entry.get('refs') or []
        matched_syms = [s for s in syms if matcher(s)]
        matched_refs = [f'ref: {r}' for r in refs if matcher(r)]
        path_hit = matcher(p)

        if matched_syms or matched_refs or path_hit:
            out_syms = matched_syms + matched_refs
            if path_hit and not out_syms and syms:
                out_syms = list(syms[:25])
                if len(syms) > 25:
                    out_syms.append(f"... (+{len(syms) - 25} more symbols in {os.path.basename(p)})")
            matches.append((p, entry['lines'], out_syms))
    return matches


CALLER_CODE_EXTS = {
    '.go', '.py', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs',
    '.html', '.htm', '.astro', '.svelte', '.vue', '.rs', '.java',
    '.cs', '.php', '.c', '.cpp', '.h', '.hpp', '.ps1', '.psm1', '.sql',
}


def _parse_symbol_spans(symbols):
    spans = []
    for s in symbols:
        m = _SYMBOL_LINE_RE.search(s)
        if not m:
            continue
        start_l = int(m.group(1))
        end_l = int(m.group(2)) if m.group(2) else start_l
        name_part = _SYMBOL_LINE_RE.sub('', s).strip()
        spans.append((start_l, end_l, name_part))
    return spans


def _enclosing_symbol(spans, lineno):
    best = None
    best_len = None
    for start_l, end_l, name_part in spans:
        if start_l <= lineno <= end_l:
            span_len = end_l - start_l
            if best is None or span_len < best_len:
                best = name_part
                best_len = span_len
    return best


def find_callers(root_path: Path, file_entries, query, scope=None, use_regex=False, max_per_file=15):
    """Trace symbol definitions and cross-file call/reference sites with enclosing context."""
    scoped = _filter_by_scope(file_entries, scope)
    if use_regex:
        try:
            pattern = re.compile(query)
        except re.error as exc:
            print(f"[RepoMap] Invalid regex '{query}': {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        terms = [t.strip() for t in query.split('|') if t.strip()]
        if not terms:
            return []
        joined = '|'.join(re.escape(t) for t in sorted(terms, key=len, reverse=True))
        pattern = re.compile(rf'(?<![a-zA-Z0-9_])(?:{joined})(?![a-zA-Z0-9_])')

    results = []
    for entry in scoped:
        rel_p = entry['path']
        ext = os.path.splitext(rel_p)[1].lower()
        if ext not in CALLER_CODE_EXTS:
            continue
        full_p = root_path / rel_p
        try:
            with open(full_p, 'r', encoding='utf-8-sig', errors='replace') as f:
                lines = f.readlines()
        except Exception:
            continue

        spans = _parse_symbol_spans(entry['symbols'])
        def_lines = {st: nm for st, _, nm in spans if pattern.search(nm)}
        hash_comment = ext in {'.py', '.ps1', '.psm1', '.php'}
        slash_comment = ext in {'.go', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.rs', '.java', '.cs', '.php', '.c', '.cpp', '.h', '.hpp'}
        in_block_comment = False

        hits = []
        for idx, raw in enumerate(lines, 1):
            stripped = raw.strip()
            if not stripped:
                continue
            if ext in {'.html', '.htm', '.astro', '.svelte', '.vue'}:
                clean, in_block_comment = _strip_html_comments_line(raw, in_block_comment)
            else:
                if in_block_comment:
                    if '*/' in stripped:
                        in_block_comment = False
                    continue
                if stripped.startswith('/*') and '*/' not in stripped[2:]:
                    in_block_comment = True
                    continue
                clean = raw
                if slash_comment and stripped.startswith('//'):
                    continue
                if hash_comment and stripped.startswith('#'):
                    continue
                if ext == '.sql' and stripped.startswith('--'):
                    continue
                if slash_comment and '//' in clean:
                    clean = clean.split('//', 1)[0]

            if not pattern.search(clean):
                continue

            snippet = re.sub(r'\s+', ' ', stripped)[:110]
            if idx in def_lines:
                tag = '[def]'
            else:
                enc = _enclosing_symbol(spans, idx)
                tag = f'[in {enc}]' if enc else '[top]'
            hits.append((idx, tag, snippet))

        if hits:
            truncated = 0
            if max_per_file > 0 and len(hits) > max_per_file:
                truncated = len(hits) - max_per_file
                hits = hits[:max_per_file]
            results.append((rel_p, hits, truncated))

    return results


def get_git_changed_paths(root_path: Path):
    try:
        res = subprocess.run(
            ['git', 'status', '--porcelain', '-uall'],
            cwd=str(root_path),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=False,
        )
        if res.returncode != 0:
            return None
        changed = set()
        for line in res.stdout.splitlines():
            if len(line) < 4:
                continue
            raw_path = line[3:].strip()
            if ' -> ' in raw_path:
                raw_path = raw_path.split(' -> ', 1)[1].strip()
            changed.add(raw_path.strip('"').replace('\\', '/'))
        if not changed:
            # Skip map-only sync commits when working tree is clean (check up to 5 recent commits)
            log_res = subprocess.run(
                ['git', 'log', '-n', '5', '--format=%H'],
                cwd=str(root_path),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                check=False,
            )
            if log_res.returncode == 0:
                for sha in [s.strip() for s in log_res.stdout.splitlines() if s.strip()]:
                    diff_res = subprocess.run(
                        ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', sha],
                        cwd=str(root_path),
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        check=False,
                    )
                    if diff_res.returncode != 0:
                        continue
                    commit_files = {
                        line.strip().replace('\\', '/')
                        for line in diff_res.stdout.splitlines()
                        if line.strip()
                    } - {'.repo-map.md', CACHE_FILENAME}
                    if commit_files:
                        changed = commit_files
                        break
        return changed
    except Exception:
        return None


def print_stats(file_entries, out_file: Path):
    total_files = len(file_entries)
    total_lines = sum(e['lines'] for e in file_entries)
    total_syms = sum(len(e['symbols']) for e in file_entries)
    total_refs = sum(len(e.get('refs') or []) for e in file_entries)
    map_info = ""
    if out_file.is_file():
        sz = out_file.stat().st_size
        map_info = f" | Current map: {sz} bytes (~{sz // 4} tokens)"
    print(f"[RepoMap] Files: {total_files} | LOC: {total_lines} | Symbols: {total_syms} | Refs: {total_refs}{map_info}")
    print("  Largest files (LOC):")
    for e in sorted(file_entries, key=lambda x: x['lines'], reverse=True)[:8]:
        print(f"    - {e['path']} ({e['lines']} LOC, {len(e['symbols'])} symbols)")


def install_git_hooks(root_path: Path):
    try:
        res = subprocess.run(
            ['git', 'rev-parse', '--git-path', 'hooks'],
            cwd=str(root_path),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            print("[RepoMap] Error: Not a git repository.", file=sys.stderr)
            return 1
        hooks_dir = Path(res.stdout.strip())
        if not hooks_dir.is_absolute():
            hooks_dir = (root_path / hooks_dir).resolve()
        hooks_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        print(f"[RepoMap] Hook setup failed: {exc}", file=sys.stderr)
        return 1

    script_posix = Path(__file__).resolve().as_posix()
    start_marker = "# >>> token-and-context-ops repo-map >>>"
    end_marker = "# <<< token-and-context-ops repo-map <<<"
    hook_block = (
        f"{start_marker}\n"
        f'if [ -f .repo-map.md ]; then\n'
        f'  (python "{script_posix}" . >/dev/null 2>&1 || python3 "{script_posix}" . >/dev/null 2>&1 || true)\n'
        f"fi\n"
        f"{end_marker}\n"
    )

    updated = []
    for hook_name in ("post-commit", "post-merge"):
        hook_path = hooks_dir / hook_name
        existing = hook_path.read_text(encoding='utf-8') if hook_path.exists() else "#!/bin/sh\n"
        if start_marker in existing and end_marker in existing:
            new_text = re.sub(
                rf"{re.escape(start_marker)}.*?{re.escape(end_marker)}\n?",
                lambda _: hook_block,
                existing,
                flags=re.DOTALL,
            )
        else:
            sep = "" if existing.endswith("\n") else "\n"
            new_text = existing + sep + hook_block
        hook_path.write_text(new_text, encoding='utf-8', newline='\n')
        try:
            hook_path.chmod(0o755)
        except Exception:
            pass
        updated.append(hook_name)

    print(f"[RepoMap] Installed sync hooks ({', '.join(updated)}) in: {hooks_dir}")
    return 0


def main():
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Generate compact repository map for token-efficient agent navigation.")
    parser.add_argument("path", nargs="?", default=".", help="Root directory of the project")
    parser.add_argument("--output", "-o", default=".repo-map.md", help="Output markdown file path (relative to root)")
    parser.add_argument("--check", action="store_true", help="Only check if map is stale without regenerating")
    parser.add_argument("--find", "-f", help="Instant symbol/path search across project (supports '|' OR queries)")
    parser.add_argument("--callers", "-c", help="Trace definitions & call/reference sites of symbol(s) across project (supports '|')")
    parser.add_argument("--in", "-i", dest="scope", help="Filter output/search to paths containing substring")
    parser.add_argument("--regex", "-E", action="store_true", help="Treat --find / --callers query as a Python regular expression")
    parser.add_argument("--changed", action="store_true", help="Print map symbols only for git-changed (or HEAD) files")
    parser.add_argument("--stats", action="store_true", help="Print project LOC/symbol hotspot statistics")
    parser.add_argument("--signatures", "-S", action="store_true", help="Include compact function/method parameter & return signatures")
    parser.add_argument("--compact", action="store_true", help="Summarize test files and CSS selectors for smaller maps")
    parser.add_argument("--no-wiring", action="store_true", help="Omit the Cross-References & Wiring section")
    parser.add_argument("--max-symbols", type=int, default=60, help="Max symbols per file in .repo-map.md (0 = unlimited; --find searches all symbols)")
    parser.add_argument("--install-hook", action="store_true", help="Install idempotent git post-commit/post-merge sync hooks")
    args = parser.parse_args()

    target_dir = Path(args.path).resolve()
    if not target_dir.is_dir():
        print(f"Error: Directory '{target_dir}' does not exist.")
        sys.exit(1)

    if args.install_hook:
        sys.exit(install_git_hooks(target_dir))

    out_file = target_dir / args.output
    cache_file = target_dir / CACHE_FILENAME
    gitignore_patterns = load_gitignore(target_dir)

    cached_data = load_cache(cache_file)
    cached_opts = cached_data.get('options') if isinstance(cached_data, dict) else None
    read_only_mode = bool(args.find or args.callers or args.changed or args.stats)
    has_explicit_render_flag = bool(args.compact or args.no_wiring or args.signatures or args.max_symbols != 60 or args.scope)
    raw_cached_files = cached_data['files'] if cached_data else {}
    current_snapshot = get_project_file_snapshot(target_dir, gitignore_patterns)
    cached_snapshot = (
        {p: {'mtime': v.get('mtime'), 'size': v.get('size')} for p, v in raw_cached_files.items()}
        if cached_data else None
    )
    files_fresh = out_file.exists() and (cached_snapshot == current_snapshot)
    render_opts = {
        'compact': args.compact,
        'no_wiring': args.no_wiring,
        'signatures': args.signatures,
        'max_symbols': args.max_symbols,
        'scope': args.scope or '',
    }

    if args.check:
        opts_ok = True
        if has_explicit_render_flag:
            opts_ok = (cached_opts == render_opts)
        is_up_to_date = files_fresh and opts_ok
        status_msg = "UP_TO_DATE" if is_up_to_date else "STALE"
        print(f"[RepoMap] Status: {status_msg}")
        sys.exit(0 if is_up_to_date else 2)

    sig_mismatch = (not args.callers) and bool(cached_opts) and (cached_opts.get('signatures', False) != args.signatures)
    cached_files = {} if sig_mismatch else raw_cached_files

    if args.scope and not read_only_mode and args.output == ".repo-map.md":
        print("[RepoMap] Error: --in cannot overwrite root .repo-map.md; pass --output <file> or use with --find/--callers/--changed/--stats.", file=sys.stderr)
        sys.exit(1)

    is_fresh = files_fresh and (cached_opts == render_opts if cached_opts else False)

    if is_fresh and not read_only_mode:
        print(f"[RepoMap] Map is already fresh (0 changes detected). Output: {out_file}")
        sys.exit(0)

    entries, new_cache_files, reparsed = scan_project(
        str(target_dir), cached_files=cached_files, include_signatures=args.signatures
    )

    if args.stats:
        print_stats(_filter_by_scope(entries, args.scope), out_file)
        sys.exit(0)

    if args.callers:
        per_file_cap = 0 if args.max_symbols == 0 else 15
        caller_results = find_callers(
            target_dir, entries, args.callers, scope=args.scope, use_regex=args.regex, max_per_file=per_file_cap
        )
        total_hits = sum(len(h) + trunc for _, h, trunc in caller_results)
        print(f"[RepoMap] Callers / References for '{args.callers}' ({total_hits} hits in {len(caller_results)} files):")
        if not caller_results:
            print("  No definitions or references matched.")
        for path, hits, trunc in caller_results:
            print(f"  * {path}")
            for lineno, tag, snippet in hits:
                print(f"      - L{lineno} {tag}: {snippet}")
            if trunc:
                print(f"      - ... (+{trunc} more in file; pass --max-symbols 0 for all)")
        sys.exit(0)

    if args.changed:
        changed_set = get_git_changed_paths(target_dir)
        if changed_set is None:
            print("[RepoMap] Error: git status unavailable.", file=sys.stderr)
            sys.exit(1)
        filtered = _filter_by_scope([e for e in entries if e['path'] in changed_set], args.scope)
        print(f"[RepoMap] Changed files ({len(filtered)}):")
        for e in filtered:
            print(f"  * {e['path']} (LOC: {e['lines']})")
            for s in e['symbols']:
                print(f"      - {s}")
            if e.get('refs'):
                print(f"      refs: {', '.join(e['refs'][:8])}")
        sys.exit(0)

    if args.find:
        results = search_symbols(entries, args.find, scope=args.scope, use_regex=args.regex)
        print(f"[RepoMap] Search results for '{args.find}':")
        if not results:
            print("  No symbols or files matched.")
        for path, lines, syms in results:
            print(f"  * {path} (LOC: {lines})")
            for s in syms:
                print(f"      - {s}")
        sys.exit(0)

    scoped_entries = _filter_by_scope(entries, args.scope)
    content = generate_markdown(
        scoped_entries,
        root_name=target_dir.name,
        max_symbols=args.max_symbols,
        compact=args.compact,
        no_wiring=args.no_wiring,
    )
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(content)

    if args.output == ".repo-map.md" and not args.scope:
        try:
            cache_payload = {
                '__schema_version__': CACHE_SCHEMA_VERSION,
                'options': render_opts,
                'files': new_cache_files,
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_payload, f)
        except Exception:
            pass

    print(f"[RepoMap] Generated updated repository map at: {out_file}")
    print(f"[RepoMap] Indexed {len(scoped_entries)} files (reparsed {reparsed}) | Size: {len(content.encode('utf-8'))} bytes (~{len(content)//4} tokens)")

if __name__ == "__main__":
    main()
