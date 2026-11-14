# Tabular ML Workflow & Zero Data Leakage Discipline

Standards for preprocessing, leakage-free pipeline design, gradient boosting ensembles, and model explainability (XAI).

## 1. Zero Data Leakage Discipline
- Never run `fit` or `fit_transform` (imputation, scaling, target/one-hot encoding) on the full dataset before splitting; encapsulate all transforms inside a Scikit-learn `Pipeline` / `ColumnTransformer`.
- On imbalanced datasets, never rely on raw `accuracy`; evaluate with `StratifiedKFold`, `scale_pos_weight`, and `PR-AUC` / `ROC-AUC`.

## 2. Ensemble Modeling & Threshold Tuning
- Prioritize gradient-boosted decision trees (`LightGBM`, `XGBoost`, `CatBoost`) for tabular data.
- Tune classification decision thresholds on out-of-fold validation predictions to optimize F1-Score or cost-sensitive metrics rather than defaulting to `0.5` (see [ml-pipeline-and-shap.md](ml-pipeline-and-shap.md)).

## 3. Model Explainability (SHAP & XAI)
- Generate global (`summary_plot`) and local (`waterfall_plot`) attributions via `shap.TreeExplainer` to audit feature contributions.

## 4. Verification Gate
- Before reporting model metrics, execute out-of-sample (hold-out/cross-validation) evaluation and verify zero target/temporal leakage (`quality-testing-review` (`references/verification-before-completion.md`)).
