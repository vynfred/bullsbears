#!/usr/bin/env python3
"""
Check the structure of existing data file
"""

import pandas as pd
from pathlib import Path

def check_data_structure():
    data_file = Path("data/backtest/nasdaq_6mo_full.parquet")
    
    if not data_file.exists():
        print(f"❌ File not found: {data_file}")
        return
    
    print(f"📂 Loading data from {data_file}")
    data = pd.read_parquet(data_file)
    
    print(f"📊 Data shape: {data.shape}")
    print(f"📊 Data columns: {list(data.columns)}")
    print(f"📊 Index: {data.index}")
    print(f"📊 Index levels: {data.index.nlevels}")
    
    if data.index.nlevels > 1:
        print(f"📊 Index level names: {data.index.names}")
        for i in range(data.index.nlevels):
            level_values = data.index.get_level_values(i)
            print(f"📊 Level {i} ({data.index.names[i]}): {len(level_values.unique())} unique values")
            print(f"   Sample: {level_values.unique()[:5].tolist()}")
    else:
        print(f"📊 Single-level index: {data.index.name}")
        print(f"   Sample: {data.index[:5].tolist()}")
    
    print(f"\n📊 First 5 rows:")
    print(data.head())
    
    print(f"\n📊 Data types:")
    print(data.dtypes)

if __name__ == "__main__":
    check_data_structure()
