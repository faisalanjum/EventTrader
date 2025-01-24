
import pandas as pd



def load_local_csv(file_path, keep_cols=None, na_subset=None):

    # Load the data, only reading specified columns
    df = pd.read_csv(
        file_path, 
        usecols=keep_cols,
        low_memory=False, 
        on_bad_lines='warn'
    )

    # Drop completely empty rows
    df = df.dropna(how='all')
    
    # Drop NA values based on specified columns
    if na_subset:
        df = df.dropna(subset=na_subset)
    
    print(f"Loaded {file_path} with {df.shape[0]} rows and {df.shape[1]} columns")
    
    return df