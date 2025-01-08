"""
Module for accessing various bioinformatics database APIs.
Includes NCBI E-utilities, Ensembl, GWAS Catalog, and UniProt.
"""

from typing import Dict, List, Optional, Union
import requests
from abc import ABC, abstractmethod
import json
import xml.etree.ElementTree as ET
from datetime import datetime
import time

class BioDatabaseAPI(ABC):
    """Abstract base class for biological database APIs."""
    
    def __init__(self, api_key: Optional[str] = None, tool: Optional[str] = None, email: Optional[str] = None):
        """
        Initialize the base API client.
        
        Args:
            api_key: Optional API key for authentication
            tool: Optional tool name for identification
            email: Optional email for contact purposes
        """
        self.api_key = api_key
        self.tool = tool
        self.email = email
        self.base_url = ""
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
    
    @abstractmethod
    def search(self, query: str) -> Dict:
        """Base search method to be implemented by child classes."""
        pass
    
    def _make_request(self, endpoint: str, params: Dict = None, delay: float = 0.34) -> requests.Response:
        """
        Helper method to make HTTP requests with rate limiting.
        Args:
            endpoint: API endpoint
            params: Query parameters
            delay: Time to wait between requests (default: 0.34s for NCBI compliance)
        """
        time.sleep(delay)
        url = f"{self.base_url}/{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response

class NCBIEutils(BioDatabaseAPI):
    """Enhanced NCBI E-utilities API client with advanced PubMed search capabilities."""
    
    def __init__(self, api_key: Optional[str] = None, tool: str = "python_bio_api", email: Optional[str] = None):
        super().__init__(api_key=api_key, tool=tool, email=email)
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def search(self, query: str) -> Dict:
        """Implement the abstract search method for NCBI"""
        params = self._build_base_params()
        params.update({
            "db": "pubmed",
            "term": query,
            "retmode": "json"
        })
        response = self._make_request("esearch.fcgi", params)
        return response.json()
        
    def _build_base_params(self) -> Dict:
        """Build base parameters required for E-utilities."""
        params = {
            "tool": self.tool,
            "api_key": self.api_key,
        }
        if self.email:
            params["email"] = self.email
        return params

    def search_pubmed(self, 
                      genes: Optional[List[str]] = None,
                      phenotypes: Optional[List[str]] = None,
                      additional_terms: Optional[List[str]] = None,
                      date_range: Optional[tuple] = None,
                      max_results: int = 100) -> Dict:
        """
        Advanced PubMed search combining genes, phenotypes, and other terms.
        
        Args:
            genes: List of gene names or symbols
            phenotypes: List of phenotypes or diseases
            additional_terms: Additional search terms
            date_range: Tuple of (start_date, end_date) in YYYY/MM/DD format
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary containing search results and metadata
        """
        query_parts = []
        
        # Build gene query
        if genes:
            gene_query = ' OR '.join([f"{gene}[Gene Symbol]" for gene in genes])
            query_parts.append(f"({gene_query})")
            
        # Build phenotype query
        if phenotypes:
            phenotype_query = ' OR '.join([f"{pheno}[MeSH Terms]" for pheno in phenotypes])
            query_parts.append(f"({phenotype_query})")
            
        # Add additional terms
        if additional_terms:
            terms_query = ' AND '.join([f"({term})" for term in additional_terms])
            query_parts.append(terms_query)
            
        # Combine all query parts
        final_query = ' AND '.join(query_parts)
        
        # Add date range if specified
        if date_range:
            start_date, end_date = date_range
            final_query += f" AND ({start_date}[Date - Publication] : {end_date}[Date - Publication])"
        
        # Initial search to get IDs
        search_params = self._build_base_params()
        search_params.update({
            "db": "pubmed",
            "term": final_query,
            "retmax": max_results,
            "retmode": "json",
            "usehistory": "y"
        })
        
        search_response = self._make_request("esearch.fcgi", search_params)
        search_result = search_response.json()
        
        # Get article details using ESummary
        if 'esearchresult' in search_result and 'idlist' in search_result['esearchresult']:
            ids = search_result['esearchresult']['idlist']
            return self.fetch_pubmed_details(ids)
        
        return search_result

    def fetch_pubmed_details(self, id_list: List[str]) -> Dict:
        """
        Fetch detailed information for PubMed articles.
        
        Args:
            id_list: List of PubMed IDs
            
        Returns:
            Dictionary containing detailed article information
        """
        summary_params = self._build_base_params()
        summary_params.update({
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "json"
        })
        
        summary_response = self._make_request("esummary.fcgi", summary_params)
        return summary_response.json()

    def extract_abstracts(self, id_list: List[str]) -> Dict[str, str]:
        """
        Fetch and extract abstracts for given PubMed IDs.
        
        Args:
            id_list: List of PubMed IDs
            
        Returns:
            Dictionary mapping PubMed IDs to their abstracts
        """
        fetch_params = self._build_base_params()
        fetch_params.update({
            "db": "pubmed",
            "id": ",".join(id_list),
            "rettype": "abstract",
            "retmode": "xml"
        })
        
        response = self._make_request("efetch.fcgi", fetch_params)
        root = ET.fromstring(response.text)
        
        abstracts = {}
        for article in root.findall(".//PubmedArticle"):
            pmid = article.find(".//PMID").text
            abstract_element = article.find(".//Abstract/AbstractText")
            if abstract_element is not None:
                abstracts[pmid] = abstract_element.text
            else:
                abstracts[pmid] = None
                
        return abstracts

    def search_and_analyze(self,
                          genes: Optional[List[str]] = None,
                          phenotypes: Optional[List[str]] = None,
                          additional_terms: Optional[List[str]] = None,
                          max_results: int = 100) -> Dict:
        """
        Comprehensive search and analysis of PubMed articles.
        
        Args:
            genes: List of gene names
            phenotypes: List of phenotypes
            additional_terms: Additional search terms
            max_results: Maximum number of results
            
        Returns:
            Dictionary containing search results and analysis
        """
        # Perform initial search
        search_results = self.search_pubmed(
            genes=genes,
            phenotypes=phenotypes,
            additional_terms=additional_terms,
            max_results=max_results
        )
        
        # Extract PMIDs
        if 'result' in search_results:
            pmids = list(search_results['result'].keys())
            if 'uids' in search_results['result']:
                pmids = search_results['result']['uids']
        else:
            return {"error": "No results found"}
            
        # Get abstracts
        abstracts = self.extract_abstracts(pmids)
        
        # Combine results
        combined_results = {
            "metadata": {
                "query": {
                    "genes": genes,
                    "phenotypes": phenotypes,
                    "additional_terms": additional_terms
                },
                "total_results": len(pmids)
            },
            "articles": {}
        }
        
        # Combine article details with abstracts
        for pmid in pmids:
            if pmid in search_results['result']:
                article_data = search_results['result'][pmid]
                combined_results['articles'][pmid] = {
                    "title": article_data.get('title', ''),
                    "authors": article_data.get('authors', []),
                    "journal": article_data.get('source', ''),
                    "pubdate": article_data.get('pubdate', ''),
                    "abstract": abstracts.get(pmid, '')
                }
                
        return combined_results
    
class EnsemblAPI(BioDatabaseAPI):
    """Ensembl REST API client."""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://rest.ensembl.org"
        self.headers["Content-Type"] = "application/json"
    
    def search(self, query: str, species: str = "homo_sapiens") -> Dict:
        """Implement the abstract search method for Ensembl"""
        endpoint = f"lookup/symbol/{species}/{query}"
        response = self._make_request(endpoint)
        return response.json()
    
    def get_variants(self, chromosome: str, start: int, end: int, 
                    species: str = "homo_sapiens") -> Dict:
        """
        Get genetic variants in a genomic region.
        Args:
            chromosome: Chromosome name
            start: Start position
            end: End position
            species: Species name
        """
        endpoint = f"overlap/region/{species}/{chromosome}:{start}-{end}/variation"
        response = self._make_request(endpoint)
        return response.json()

class GWASCatalog(BioDatabaseAPI):
    """GWAS Catalog API client."""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.ebi.ac.uk/gwas/rest/api"
    
    def search(self, query: str) -> Dict:
        """Implement the abstract search method for GWAS Catalog"""
        endpoint = "studies/search"
        params = {"q": query}
        response = self._make_request(endpoint, params)
        return response.json()
    
    def get_associations(self, study_id: str) -> Dict:
        """
        Get associations for a specific study.
        Args:
            study_id: GWAS study identifier
        """
        endpoint = f"studies/{study_id}/associations"
        response = self._make_request(endpoint)
        return response.json()

class UniProtAPI(BioDatabaseAPI):
    """UniProt API client."""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://rest.uniprot.org"
    
    def search(self, query: str) -> Dict:
        """Implement the abstract search method for UniProt"""
        endpoint = "uniprotkb/search"
        params = {
            "query": query,
            "format": "json"
        }
        response = self._make_request(endpoint, params)
        return response.json()
    
    def get_protein_features(self, uniprot_id: str) -> Dict:
        """
        Get protein features from UniProt.
        Args:
            uniprot_id: UniProt identifier
        """
        endpoint = f"uniprotkb/{uniprot_id}/features"
        response = self._make_request(endpoint)
        return response.json()

# # Example usage:
# if __name__ == "__main__":
#     # Initialize clients
#     ncbi = NCBIEutils(
#         api_key="your_api_key",
#         tool="your_tool_name",
#         email="your_email@example.com"
#     )
    
#     # Example search combining gene and phenotype
#     results = ncbi.search_and_analyze(
#         genes=["DSP", "BRCA2"],
#         phenotypes=["Breast Neoplasms"],
#         additional_terms=["prognosis"],
#         max_results=50
#     )
    
#     # Process results
#     for pmid, article in results['articles'].items():
#         print(f"Title: {article['title']}")
#         print(f"Abstract: {article['abstract'][:200]}...")
#         print("-" * 80)
    
#     ensembl = EnsemblAPI()
#     gwas = GWASCatalog()
#     uniprot = UniProtAPI()
    
#     # Example searches
#     ensembl_results = ensembl.search("DSP")
#     gwas_results = gwas.search("diabetes")
#     uniprot_results = uniprot.search("insulin")

