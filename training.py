from data_prep import X_train, y_train, X_test, y_test
import xgboost as xgb
from sklearn.metrics import accuracy_score, roc_auc_score, log_loss

model = xgb.XGBClassifier(
    n_estimators=65,
    learning_rate=0.05,
    max_depth=5,
    subsample=0.80,
    colsample_bytree=0.80,
    min_child_weight=3,
    reg_lambda=1,
    random_state=42,
    n_jobs=-1,
    eval_metric=['logloss', 'auc'],
    early_stopping_rounds=100
)

print("Training the model...")
model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=10  #prints every 10 trees 
)

print(f"\nBest iteration: {model.best_iteration}")

y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

acc  = accuracy_score(y_test, y_pred)
auc  = roc_auc_score(y_test, y_prob)
loss = log_loss(y_test, y_prob)

print(f"\results")
print(f"Accuracy:  {acc:.4f}  ({acc*100:.2f}%)")
print(f"AUC Score: {auc:.4f}  (Ranking power)") #tells the area under the roc curve
print(f"Log Loss:  {loss:.4f} (Probability accuracy, lower is better)")

