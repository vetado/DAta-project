
import pandas as pd
import numpy as np
from pathlib import Path

RAW = Path("../data/raw")
csvs = list(RAW.glob("*.csv"))
print("CSVs found:", csvs)
PATH = csvs[0]
df = pd.read_csv(PATH, low_memory=False)
print(f"\nShape: {df.shape[0]:,} rows × {df.shape[1]} columns")
print(f"Memory: {df.memory_usage(deep=True).sum() / 1e9:.2f} GB")