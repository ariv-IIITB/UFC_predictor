from data_prep import X_train
import pandas as pd
import numpy as np

corr_matrix = X_train.corr().abs()

# Only look at the upper triangle so we don't get duplicate pairs (A-B and B-A)
# or a feature correlated with itself (always 1.0)
upper = corr_matrix.where(
    np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
)

high_corr = []
for col in upper.columns:
    for row in upper.index:
        val = upper.loc[row, col]
        if pd.notna(val) and val > 0.85:
            high_corr.append((row, col, val))

corr_df = pd.DataFrame(high_corr, columns=['Feature1', 'Feature2', 'Correlation'])
corr_df = corr_df.sort_values('Correlation', ascending=False)

corr_df.to_csv("high_correlation_pairs.csv", index=False)
print(corr_df.to_string(index=False))


