import pandas as pd

df = pd.read_csv('final_data.csv')

print("Seeing if it is balanced") #since the fights are mirrored 
print(df['label_a_win'].value_counts(normalize=True) * 100) #this should be 50 percent 
#normalized means proportions 

print("top 15 missing parameters")
missing = df.isnull().sum() #data frame of true and false and sums up the trues (col) 
print(missing[missing > 0].sort_values(ascending=False).head(15))


print("\n--- NON-NUMERIC COLUMNS ---")
print(df.select_dtypes(exclude=['int64', 'float64', 'int32', 'float32', 'bool']).columns.tolist())

