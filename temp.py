import requests
import time
from typing import Optional, List, Dict, Any

def get_primary_uniprot_id(gene_name: str) -> Optional[str]:
    """
    Fetch the primary UniProt ID (canonical) for a given gene name.
    Prioritizes reviewed (SwissProt) entries.

    Args:
        gene_name: Gene symbol to search for

    Returns:
        Optional[str]: UniProt ID if found, None otherwise
    """
    # Add more specific search criteria to improve accuracy
    query = f'(gene:{gene_name}) AND (reviewed:true OR reviewed:false)'
    url = f"https://rest.uniprot.org/uniprotkb/search?query={
        query}&fields=accession,reviewed,gene_names&format=json"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise exception for bad status codes

        data = response.json()
        if not data.get('results'):
            print(f"No UniProt entries found for gene {gene_name}")
            return None

        # First try to find reviewed entries with exact gene name match
        for entry in data['results']:
            if entry.get('reviewed') and 'genes' in entry:
                gene_names = [g['value'].upper()
                                for g in entry['genes'][0].get('geneName', [])]
                if gene_name.upper() in gene_names:
                    uniprot_id = entry['primaryAccession']
                    print(f"Found reviewed UniProt ID for {
                            gene_name}: {uniprot_id}")
                    return uniprot_id

        # If no reviewed exact match, take first reviewed entry
        reviewed_entries = [
            entry for entry in data['results'] if entry.get('reviewed')]
        if reviewed_entries:
            uniprot_id = reviewed_entries[0]['primaryAccession']
            print(f"Found reviewed UniProt ID for {
                    gene_name}: {uniprot_id}")
            return uniprot_id

        # Last resort: first unreviewed entry
        uniprot_id = data['results'][0]['primaryAccession']
        print(f"Found unreviewed UniProt ID for {gene_name}: {uniprot_id}")
        return uniprot_id

    except requests.exceptions.RequestException as e:
        print(f"Error fetching UniProt ID for {gene_name}: {str(e)}")
        return None

def get_reactome_id(uniprot_id: str) -> Optional[str]:
    """
    Fetch the Reactome ID using the primary UniProt ID.

    Args:
        uniprot_id: UniProt accession number

    Returns:
        Optional[str]: Reactome ID if found, None otherwise
    """
    url = f"https://reactome.org/ContentService/data/mapping/UniProt/{
        uniprot_id}"

    try:
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()
        if not data:
            print(f"No Reactome mapping found for UniProt ID {uniprot_id}")
            return None

        # Get the first Reactome ID (there might be multiple)
        reactome_id = list(data.keys())[0]
        print(f"Found Reactome ID for {uniprot_id}: {reactome_id}")
        return reactome_id

    except requests.exceptions.RequestException as e:
        print(f"Error fetching Reactome ID for {uniprot_id}: {str(e)}")
        return None

def get_pathways(uniprot_id: str) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch pathways related to a given UniProt ID directly.

    Args:
        uniprot_id: UniProt accession number

    Returns:
        Optional[List[Dict[str, Any]]]: List of pathway information if found, None on error
    """
    url = f"https://reactome.org/ContentService/data/mapping/UniProt/{
        uniprot_id}/pathways"
    try:
        response = requests.get(url)
        response.raise_for_status()

        pathways = response.json()
        if not pathways:
            print(f"No pathways found for Reactome ID {reactome_id}")
            return []

        print(f"\nPathways for {reactome_id}:")
        for pathway in pathways:
            print(f"- {pathway['displayName']} (ID: {pathway['stId']})")
            # Print additional useful information if available
            if 'species' in pathway:
                print(f"  Species: {pathway['species']['displayName']}")
            if 'type' in pathway:
                print(f"  Type: {pathway['type']}")
        return pathways

    except requests.exceptions.RequestException as e:
        print(f"Error fetching pathways for {reactome_id}: {str(e)}")
        return None

def main():
    """Main function to run the pathway finder."""
    while True:
        gene_name = input(
            "\nEnter a gene name (e.g., TP53) or 'q' to quit: ").strip().upper()
        if gene_name.lower() == 'q':
            break

        if not gene_name:
            print("Please enter a valid gene name.")
            continue

        print(f"\nSearching for pathways related to {gene_name}...")

        # Add small delays between API calls to be nice to the servers
        uniprot_id = get_primary_uniprot_id(gene_name)
        if uniprot_id:
            time.sleep(1)
            get_pathways(uniprot_id)

if __name__ == "__main__":
    main()
