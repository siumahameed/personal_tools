"""Test DDGS for ORCID queries."""
import asyncio
from ddgs import DDGS

queries = [
    "Bangladesh statistics professor orcid",
    "Bangladesh machine learning orcid",
    "machine learning classification scikit-learn orcid",
    "Bangladesh statistics orcid",
    "Bangladesh PhD statistics orcid",
]

for q in queries:
    print(f"\n=== {q!r} ===")
    try:
        results = DDGS().text(q, max_results=10)
    except Exception as e:
        print(f"  error: {e}")
        continue
    for r in results[:5]:
        print(f"  {r['href'][:90]}")
