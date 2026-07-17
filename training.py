from data_prep import X_train, y_train, X_test, y_test
import xgboost as xgb
from sklearn.metrics import accuracy_score, roc_auc_score, log_loss

model = xgb.XGBClassifier(
    n_estimators=64,          # high ceiling, early stopping will cut it off
    learning_rate=0.051,
    max_depth=5,
    subsample=0.80,             # row subsampling -> reduces overfitting
    colsample_bytree=0.81,      # feature subsampling -> important with 268 features
    min_child_weight=3,        # ignore splits backed by too few samples
    reg_lambda=1,              # L2 regularization on leaf weights
    random_state=42,
    n_jobs=-1,
    eval_metric=['logloss', 'auc'],
    early_stopping_rounds=100   # stop if no improvement for 20 rounds
)

print("Training the model...")
model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=10  # Print progress to the terminal every 10 trees
)

print(f"\nBest iteration: {model.best_iteration}")

# Test the model on the 2025/2026 test set
y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

acc  = accuracy_score(y_test, y_pred)
auc  = roc_auc_score(y_test, y_prob)
loss = log_loss(y_test, y_prob)

print(f"\n--- MODEL RESULTS ---")
print(f"Accuracy:  {acc:.4f}  ({acc*100:.2f}%)")
print(f"AUC Score: {auc:.4f}  (Ranking power)")
print(f"Log Loss:  {loss:.4f} (Probability accuracy, lower is better)")

from sklearn.metrics import accuracy_score
import numpy as np

thresholds = np.arange(0.35, 0.65, 0.01)
best_acc, best_t = 0, 0.5
for t in thresholds:
    preds = (y_prob >= t).astype(int)
    a = accuracy_score(y_test, preds)
    if a > best_acc:
        best_acc, best_t = a, t

print(f"Best threshold: {best_t:.2f} -> Accuracy: {best_acc:.4f}")

# also useful: see the full curve so we know how sharp or flat the peak is
for t in [0.40, 0.45, 0.48, 0.50, 0.52, 0.55, 0.60]:
    preds = (y_prob >= t).astype(int)
    print(f"t={t:.2f}: acc={accuracy_score(y_test, preds):.4f}")