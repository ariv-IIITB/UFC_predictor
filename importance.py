from data_prep import X_train, y_train, X_test, y_test
import xgboost as xgb
import pandas as pd
from sklearn.inspection import permutation_importance

print(f"X_train shape: {X_train.shape} | y_train shape: {y_train.shape}")
print(f"X_test shape:  {X_test.shape}  | y_test shape:  {y_test.shape}")

# Train the model
print("\nTraining model to evaluate all features...")
model = xgb.XGBClassifier(
    n_estimators=150,
    learning_rate=0.1,
    max_depth=5,
    random_state=42,
    n_jobs=-1
)
model.fit(X_train, y_train)

# Run permutation importance on the held-out test set
print("\nRunning permutation importance (this may take a bit)...")
result = permutation_importance(
    model, X_test, y_test,
    scoring='roc_auc', n_repeats=15, random_state=42, n_jobs=-1
)

perm_df = pd.DataFrame({
    'Feature': X_test.columns,
    'Importance_Mean': result.importances_mean,  # type: ignore
    'Importance_Std': result.importances_std      # type: ignore
}).sort_values('Importance_Mean', ascending=False)

perm_df.to_csv("permutation_importance.csv", index=False)

print("\n--- TOP 30 MOST USEFUL FEATURES (test-set generalization) ---")
print(perm_df.head(30).to_string(index=False))

print("\n--- BOTTOM 30 WEAKEST / MOST HARMFUL FEATURES ---")
print(perm_df.tail(30).to_string(index=False))

print("\nSaved full report to 'permutation_importance.csv'")

