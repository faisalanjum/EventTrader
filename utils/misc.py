import yfinance as yf
from tqdm import tqdm
import time

def check_options_yfinance(symbols):

    options_available = []
    for symbol in tqdm(symbols, desc="Checking options availability"):
        try:
            stock = yf.Ticker(symbol)
            if stock.options:
                options_available.append(symbol)
            time.sleep(0.1)  # Small delay to avoid rate limits
        except Exception as e:
            print(f"Error checking {symbol}: {str(e)}")
            continue
            
    print(f"\nFound {len(options_available)} stocks with options out of {len(symbols)} total")
    return options_available


def get_unique_items(df, column, show_items=False):

    unique_values = df[column].dropna().unique()
    unique_count = len(unique_values)
    
    if show_items:
        unique_items = sorted([str(x) for x in unique_values])
        return unique_count, unique_items
    
    return unique_count