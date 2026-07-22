from data_prep import X_train, y_train, X_test, y_test
import xgboost as xgb
import pandas as pd
from sklearn.inspection import permutation_importance

print(f"X_train shape: {X_train.shape} | y_train shape: {y_train.shape}")
print(f"X_test shape:  {X_test.shape}  | y_test shape:  {y_test.shape}")



model = xgb.XGBClassifier(
    n_estimators=150,
    learning_rate=0.1,
    max_depth=5,
    random_state=42,
    n_jobs=-1
)
model.fit(X_train, y_train)

result = permutation_importance(
    model, X_test, y_test,
    scoring='roc_auc', n_repeats=15, random_state=42, n_jobs=-1
)

perm_df = pd.DataFrame({
    'Feature': X_test.columns,
    'Importance_Mean': result.importances_mean,  # type: ignore
    'Importance_Std': result.importances_std      # type: ignore
}).sort_values('Importance_Mean', ascending=False)
#be careful that the std deviaton is less than the mean 

perm_df.to_csv("permutation_importance.csv", index=False)

print("\ntop 30")
print(perm_df.head(30).to_string(index=False))

print("\nbottom 30 stats")
print(perm_df.tail(30).to_string(index=False))


