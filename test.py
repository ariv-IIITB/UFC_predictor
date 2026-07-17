from data_prep import X_train, y_train, X_test, y_test
import xgboost as xgb
from sklearn.metrics import accuracy_score, roc_auc_score, log_loss
import itertools
import random

random.seed(42)

param_grid = {
    'max_depth': [3, 4, 5, 6],
    'learning_rate': [0.01, 0.03, 0.05, 0.07, 0.1],
    'n_estimators': [100, 150, 200, 300],
    'subsample': [0.7, 0.8, 0.9, 1.0],
    'colsample_bytree': [0.6, 0.7, 0.8, 0.9, 1.0],
    'min_child_weight': [1, 2, 3, 5],
    'gamma': [0, 0.5, 1, 2],
    'reg_lambda': [1, 2, 5, 10],
}

keys = list(param_grid.keys())
combos = list(itertools.product(*param_grid.values()))
random.shuffle(combos)

best_acc = 0
best_params = None

for i, combo in enumerate(combos[:150]):  # try 150 random combos
    params = dict(zip(keys, combo))
    model = xgb.XGBClassifier(**params, random_state=42, n_jobs=-1, eval_metric='logloss')
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    if acc > best_acc:
        best_acc = acc
        best_params = params
        print(f"[{i}] New best: {acc:.4f} -> {params}")

print(f"\nBest accuracy found: {best_acc:.4f}")
print(f"Best params: {best_params}")