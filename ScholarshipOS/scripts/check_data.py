"""Check current data and verify app startup."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from data.data_loader import load_core_scholarships, load_core_universities, load_core_professors

scholarships = load_core_scholarships()
unis = load_core_universities()
profs = load_core_professors()

countries = {}
for s in scholarships:
    c = s.get('country', 'Unknown')
    countries[c] = countries.get(c, 0) + 1

print('Scholarships by country:')
for c, n in sorted(countries.items()):
    print(f'  {c}: {n}')

print(f'\nTotal scholarships: {len(scholarships)}')
print(f'Total universities: {len(unis)}')
print(f'Total professors: {len(profs)}')

prof_countries = {}
for p in profs:
    c = p.get('country', 'Unknown')
    prof_countries[c] = prof_countries.get(c, 0) + 1

print('\nProfessors by country:')
for c, n in sorted(prof_countries.items()):
    print(f'  {c}: {n}')

has_li = sum(1 for p in profs if p.get('linkedin_url'))
print(f'\nProfessors with LinkedIn URLs: {has_li}/{len(profs)}')

# Check for Bangladesh/India/Pakistan content
for keyword in ['bangladesh', 'india', 'pakistan', 'south asia', 'developing']:
    found = [s['name'] for s in scholarships if keyword in s.get('name', '').lower() or keyword in s.get('country', '').lower()]
    if found:
        print(f'\n"{keyword}" related scholarships:')
        for f in found:
            print(f'  - {f}')
