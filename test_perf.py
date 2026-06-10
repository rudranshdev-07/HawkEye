import sys
import time
sys.path.insert(0, '.')

import pandas as pd
from src.risk.intelligence_engine import get_location_intelligence

print('[TEST] Loading dataset...')
df = pd.read_csv('data/raw/india_crime_data.csv')
print(f'[TEST] Dataset loaded: {len(df)} records')

print('[TEST] Starting intelligence query...')
start = time.time()
result = get_location_intelligence(28.61, 77.20, df)
elapsed = time.time() - start

print(f'[TEST] ✓ Query completed in {elapsed:.3f}s')
print(f'[TEST] Risk score: {result.get("risk_score")}')
print(f'[TEST] Risk level: {result.get("risk_level")}')
print(f'[TEST] Risk components: {result.get("risk_components")}')
print(f'[TEST] Crime count: {result.get("crime_count")}')
