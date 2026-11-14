# Machine Learning Pipeline, Leakage Prevention & SHAP XAI Guide

## 1. Leakage-Free Scikit-Learn `Pipeline`
Encapsulate all preprocessing steps (imputation, scaling, one-hot encoding) inside a `Pipeline` so validation folds and hold-out test sets never leak into `fit`:

```python
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from lightgbm import LGBMClassifier

num_features = ['age', 'income', 'credit_score']
cat_features = ['occupation', 'city']

num_pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])

cat_pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
    ('encoder', OneHotEncoder(handle_unknown='ignore'))
])

preprocessor = ColumnTransformer([
    ('num', num_pipeline, num_features),
    ('cat', cat_pipeline, cat_features)
])

full_model = Pipeline([
    ('preprocessor', preprocessor),
    ('classifier', LGBMClassifier(n_estimators=300, random_state=42))
])
```

---

## 2. SHAP (Explainable AI - XAI) Template
Generate global and local feature attribution plots for tree ensembles:

```python
import shap
import matplotlib.pyplot as plt

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

# 1. Global Feature Importance Summary Plot
plt.figure()
shap.summary_plot(shap_values, X_test, show=False)
plt.tight_layout()
plt.savefig('shap_summary.png', dpi=300)

# 2. Single-Prediction Local Waterfall Plot
plt.figure()
shap.plots.waterfall(explainer(X_test)[0], show=False)
plt.tight_layout()
plt.savefig('shap_waterfall_sample.png', dpi=300)
```
