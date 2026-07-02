"""Quick DDGS test to see what it returns for natural queries."""
import asyncio
from ddgs import DDGS

queries = [
    "Bangladesh statistics professor researchgate",
    "Bangladesh statistics professor linkedin",
    "machine learning classification scikit-learn researchgate",
    "PhD student statistics researchgate",
    "data analysis researchgate",
    "Bangladesh PhD statistics student",
    "Dhaka University statistics professor",
]

for q in queries:
    print(f"\n=== {q!r} ===")
    try:
        results = DDGS().text(q, max_results=10)
    except Exception as e:
        print(f"  error: {e}")
        continue
    for r in results:
        print(f"  {r['href'][:90]}")
