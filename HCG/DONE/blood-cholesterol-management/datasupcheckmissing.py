import pandas as pd
import json

# Import list of missing PMIDs
df = pd.read_csv('data-supplement-bugs.csv') 
pmids = list(df['PMID'])

# Import datasup json file
with open('datasup.json') as f:
  data = json.load(f)

# Extract all the PMIDs in the json file
referencepmids = []
for entry in data:
	referencepmids.append(entry.get('pmid'))

# Find missing PMIDs 
missing = 0
for pmid in pmids:
	if pmid not in referencepmids:
		print("value is not present for given JSON key")
		print(pmid)
		missing += 1
	else:
	    continue

print("Missing is " + str(missing))