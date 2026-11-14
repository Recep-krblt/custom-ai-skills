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
CACHE_SCHEMA_VERSION = 3

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
            if len(parts) > 1 and part in {'.github', '.vscode', '.idea'}:
                return True

    for pattern in gitignore_patterns:
        cleaned = pattern.lstrip('/')
        if fnmatch.fnmatch(norm_path, cleaned) or fnmatch.fnmatch(parts[-1] if parts else '', cleaned):
            return True
        if any(fnmatch.fnmatch(part, cleaned) for part in parts):
            return True
        if '/' in cleaned and (norm_path.startswith(cleaned + '/') or f'/{cleaned}/' in f'/{norm_path}/'):
            return True
    return False

def parse_html_symbols(lines, skip_frontmatter=False):
    symbols = []
    id_pattern = re.compile(r'id=["\']([a-zA-Z0-9_\-]+)["\']')
    tag_pattern = re.compile(r'<(title|header|nav|main|section|article|aside|footer|form|table|template|script|link)\b([^>]*)>', re.IGNORECASE)
    close_script_re = re.compile(r'</script\b[^>]*>', re.IGNORECASE)
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

                    # Skip inline <script> body so JS template strings like `<section>` aren't misread as HTML
                    if end_line is None:
                        return symbols
                    if end_line == idx:
                        cm = close_script_re.search(clean_line, pos)
                        pos = cm.end() if cm else len(clean_line)
                    else:
                        i = end_line - 1
                        idx = i + 1
                        clean_line, in_comment = _strip_html_comments_line(lines[i], False)
                        cm = close_script_re.search(clean_line)
                        pos = cm.end() if cm else len(clean_line)
            elif tag == 'link' and 'rel="stylesheet"' in attrs.lower() and 'href=' in attrs.lower():
                href_match = re.search(r'href=["\']([^"\']+)["\']', attrs, re.IGNORECASE)
                if href_match:
                    symbols.append(format_symbol(f'<link rel="stylesheet" href="{href_match.group(1)}">', idx))
        i += 1
    return symbols


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


def parse_go_symbols(lines, line_offset=0):
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
                label = f'func ({recv_type}) {fn_name}'
            else:
                label = f'func {fn_name}'
            end_line = find_brace_block_end(lines, idx - 1, is_go=True)
            end_abs = (end_line + line_offset) if end_line else None
            symbols.append(format_symbol(label, idx + line_offset, end_abs))
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


def parse_code_symbols(lines, ext, line_offset=0):
    if ext == '.go':
        return parse_go_symbols(lines, line_offset=line_offset)

    symbols = []

    # Python
    if ext == '.py':
        cls_def = re.compile(r'^\s*(class\s+[a-zA-Z0-9_]+(?:\([^)]*\))?):')
        fn_def = re.compile(r'^\s*((?:async\s+)?def\s+[a-zA-Z0-9_]+\s*\([^)]*\))(?:\s*->\s*[^:]+)?:')
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
                label = f_match.group(1) if f_match.re is fn_def else f'{f_match.group(1)}(...)'
                symbols.append(format_symbol(label, idx + line_offset, end_abs))

    # JavaScript / TypeScript / JSX / TSX
    elif ext in {'.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'}:
        patterns = [
            re.compile(r'^\s*(?:export\s+(?:default\s+)?)?(?:abstract\s+)?class\s+([a-zA-Z0-9_]+)'),
            re.compile(r'^\s*(?:export\s+(?:default\s+)?)?interface\s+([a-zA-Z0-9_]+)'),
            re.compile(r'^\s*(?:export\s+)?type\s+([a-zA-Z0-9_]+)\s*='),
            re.compile(r'^\s*(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+([a-zA-Z0-9_]+)\s*\('),
            re.compile(r'^\s*(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?\('),
            re.compile(r'^\s*(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?[a-zA-Z0-9_]+\s*=>'),
            re.compile(r'^\s*(?:router|app)\.(get|post|put|delete|patch|use)\s*\(\s*[\'"`]([^\'"`]+)[\'"`]')
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
            for p_idx, p in enumerate(patterns):
                m = p.match(line)
                if m:
                    if p_idx == 4 and not _has_arrow_after_params(lines, idx - 1, m.end() - 1):
                        continue
                    if p_idx == 6:
                        symbols.append(format_symbol(f'route {m.group(1).upper()} {m.group(2)}', idx + line_offset))
                        break
                    end_line = find_brace_block_end(lines, idx - 1, is_js=True)
                    end_abs = (end_line + line_offset) if end_line else None
                    if p_idx == 0:
                        label = f'class {m.group(1)}'
                    elif p_idx == 1:
                        label = f'interface {m.group(1)}'
                    elif p_idx == 2:
                        label = f'type {m.group(1)}'
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
                symbols.append(format_symbol(f'{m.group(1)} {m.group(2)}', idx + line_offset, end_abs))

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
                    symbols.append(format_symbol(f'function {pm.group(1)}', idx + line_offset, end_abs))
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
                symbols.append(format_symbol(f'method {fm.group(1)}()', idx + line_offset, end_abs))

    return symbols

def get_project_file_snapshot(root_path: Path, gitignore_patterns: list):
    snapshot = {"__schema_version__": CACHE_SCHEMA_VERSION}
    for dirpath, dirnames, filenames in os.walk(root_path):
        rel_dir = os.path.relpath(dirpath, root_path)
        if rel_dir == '.':
            rel_dir = ''
        dirnames[:] = [d for d in dirnames if not is_ignored(os.path.join(rel_dir, d), root_path, gitignore_patterns)]
        for fname in sorted(filenames):
            rel_file_path = os.path.normpath(os.path.join(rel_dir, fname)).replace('\\', '/')
            if is_ignored(rel_file_path, root_path, gitignore_patterns):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext in BINARY_EXTENSIONS or fname in {CACHE_FILENAME, '.repo-map.md'}:
                continue
            full_file_path = Path(dirpath) / fname
            try:
                snapshot[rel_file_path] = full_file_path.stat().st_mtime
            except Exception:
                pass
    return snapshot

def scan_project(root_dir: str):
    root_path = Path(root_dir).resolve()
    gitignore_patterns = load_gitignore(root_path)
    file_entries = []
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        rel_dir = os.path.relpath(dirpath, root_path)
        if rel_dir == '.':
            rel_dir = ''
        dirnames[:] = [d for d in dirnames if not is_ignored(os.path.join(rel_dir, d), root_path, gitignore_patterns)]
        
        for fname in sorted(filenames):
            rel_file_path = os.path.normpath(os.path.join(rel_dir, fname)).replace('\\', '/')
            if is_ignored(rel_file_path, root_path, gitignore_patterns):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext in BINARY_EXTENSIONS or fname in {CACHE_FILENAME, '.repo-map.md'}:
                continue
            
            full_file_path = Path(dirpath) / fname
            try:
                with open(full_file_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                    lines = f.readlines()
                line_count = len(lines)
            except Exception:
                continue
            
            symbols = []
            if ext in {'.html', '.htm'}:
                symbols = parse_html_symbols(lines)
                for block_offset, block_lines in extract_inline_script_blocks(lines):
                    symbols.extend(parse_code_symbols(block_lines, '.js', line_offset=block_offset))
                symbols = sort_symbols_by_line(symbols)
            elif ext in {'.astro', '.svelte', '.vue'}:
                symbols = sort_symbols_by_line(parse_code_symbols(lines, '.ts') + parse_html_symbols(lines, skip_frontmatter=(ext == '.astro')))
            elif ext in {'.css', '.scss', '.sass'}:
                symbols = parse_css_symbols(lines)
            elif ext in {'.md', '.mdx'}:
                symbols = parse_markdown_symbols(lines)
            elif ext == '.sql':
                symbols = parse_sql_symbols(lines)
            elif ext in {'.py', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.java', '.cs', '.go', '.php', '.c', '.cpp', '.h', '.hpp', '.rs', '.ps1', '.psm1'}:
                symbols = parse_code_symbols(lines, ext)

            file_entries.append({
                'path': rel_file_path,
                'lines': line_count,
                'symbols': symbols
            })
            
    return file_entries

def generate_markdown(file_entries, root_name="Project", max_symbols=60):
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
            
        sym_str = ""
        syms = entry['symbols']
        if syms:
            shown = syms[:max_symbols] if max_symbols > 0 else syms
            indent = "  "
            sym_items = "\n".join([f"{indent}  - {s}" for s in shown])
            if max_symbols > 0 and len(syms) > max_symbols:
                sym_items += f"\n{indent}  - ... (+{len(syms) - max_symbols} more; use --find)"
            sym_str = f"\n{sym_items}"
            
        md.append(f"- **`{fname}`** (Lines: {entry['lines']}){sym_str}")
        
    return "\n".join(md)

def search_symbols(file_entries, query):
    terms = [t.strip().lower() for t in query.split('|') if t.strip()]
    if not terms:
        return []
    matches = []
    for entry in file_entries:
        p = entry['path']
        p_low = p.lower()
        matched_symbols = [s for s in entry['symbols'] if any(t in s.lower() for t in terms)]
        if any(t in p_low for t in terms) or matched_symbols:
            matches.append((p, entry['lines'], matched_symbols))
    return matches

def main():
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Generate compact repository map for token-efficient agent navigation.")
    parser.add_argument("path", nargs="?", default=".", help="Root directory of the project")
    parser.add_argument("--output", "-o", default=".repo-map.md", help="Output markdown file path (relative to root)")
    parser.add_argument("--check", action="store_true", help="Only check if map is stale without regenerating")
    parser.add_argument("--find", "-f", help="Instant symbol search across project (supports '|' OR queries, e.g. 'Foo|Bar')")
    parser.add_argument("--max-symbols", type=int, default=60, help="Max symbols per file in .repo-map.md (0 = unlimited; --find searches all symbols)")
    args = parser.parse_args()
    
    target_dir = Path(args.path).resolve()
    if not target_dir.is_dir():
        print(f"Error: Directory '{target_dir}' does not exist.")
        sys.exit(1)
        
    out_file = target_dir / args.output
    cache_file = target_dir / CACHE_FILENAME
    gitignore_patterns = load_gitignore(target_dir)
    
    current_snapshot = get_project_file_snapshot(target_dir, gitignore_patterns)
    
    # Check cache freshness
    is_fresh = False
    if out_file.exists() and cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached_snapshot = json.load(f)
            if cached_snapshot == current_snapshot:
                is_fresh = True
        except Exception:
            is_fresh = False
            
    if args.check:
        status_msg = "UP_TO_DATE" if is_fresh else "STALE"
        print(f"[RepoMap] Status: {status_msg}")
        sys.exit(0 if is_fresh else 2)

    if is_fresh and not args.find:
        print(f"[RepoMap] Map is already fresh (0 changes detected). Output: {out_file}")
        sys.exit(0)
        
    entries = scan_project(str(target_dir))
    
    if args.find:
        results = search_symbols(entries, args.find)
        print(f"[RepoMap] Search results for '{args.find}':")
        if not results:
            print("  No symbols or files matched.")
        for path, lines, syms in results:
            print(f"  • {path} (LOC: {lines})")
            for s in syms:
                print(f"      - {s}")
        sys.exit(0)
        
    content = generate_markdown(entries, root_name=target_dir.name, max_symbols=args.max_symbols)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(content)
        
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(current_snapshot, f)
    except Exception:
        pass
        
    print(f"[RepoMap] Generated updated repository map at: {out_file}")
    print(f"[RepoMap] Indexed {len(entries)} files | Size: {len(content.encode('utf-8'))} bytes (~{len(content)//4} tokens)")

if __name__ == "__main__":
    main()
