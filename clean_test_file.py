import pandas as pd
import os

file_path = "Search Snippet/test_founder.xlsx"
try:
    df = pd.read_excel(file_path)
    print(f"Columns: {list(df.columns)}")
    
    # Identify URL column
    url_col = next((c for c in df.columns if "url" in c.lower()), "LinkedIn URL")
    print(f"Assuming URL column is: {url_col}")
    
    # Keep only URL column
    new_df = df[[url_col]].copy()
    
    # Save back
    new_df.to_excel(file_path, index=False)
    print("File cleaned.")
except Exception as e:
    print(f"Error: {e}")
