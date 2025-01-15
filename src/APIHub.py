"""
Module for accessing various bioinformatics database APIs.
Includes NCBI E-utilities, Ensembl, GWAS Catalog, UniProt, STRING, Reactome, IntAct, PharmGKB, and BioGRID.
"""

from typing import Dict, List, Optional, Union
import requests
from abc import ABC, abstractmethod
import json
import xml.etree.ElementTree as ET
from datetime import datetime
import time
import aiohttp

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

class StringDBClient(BioDatabaseAPI):
    """Client for STRING protein-protein interaction database"""
    
    def __init__(self, caller_identity: str='HBP'):
        """
        Initialize STRING client.
        
        Args:
            caller_identity: Identifier for your application
        """
        super().__init__()
        self.base_url = "https://version-12-0.string-db.org/api"
        self.caller_identity = caller_identity
        
    async def search(self, identifiers: Union[str, List[str]], 
                    species: int = 9606,
                    required_score: int = 400,
                    network_type: str = "functional") -> Dict:
        """
        Search STRING database for protein interactions.
        
        Args:
            identifiers: Protein identifier(s)
            species: Species NCBI taxonomy ID (default: 9606 for human)
            required_score: Threshold score (0-1000)
            network_type: Either 'functional' or 'physical'
        """
        if isinstance(identifiers, list):
            identifiers = "\r".join(identifiers)
            
        params = {
            "identifiers": identifiers,
            "species": species,
            "required_score": required_score,
            "network_type": network_type,
            "caller_identity": self.caller_identity
        }
        return await self._make_request("tsv/interaction_partners", params)

    async def get_network_image(self, identifiers: List[str], 
                              species: int = 9606,
                              network_flavor: str = "confidence",
                              required_score: int = 400) -> bytes:
        """
        Get network image visualization for proteins.
        
        Args:
            identifiers: List of protein identifiers
            species: Species NCBI taxonomy ID
            network_flavor: Type of network (confidence, evidence, actions)
            required_score: Minimum interaction score (0-1000)
        """
        params = {
            "identifiers": "\r".join(identifiers),
            "species": species,
            "network_flavor": network_flavor,
            "required_score": required_score,
            "format": "image"
        }
        response = await self._make_request("image/network", params)
        return response.content

    async def get_functional_enrichment(self, identifiers: List[str],
                                      species: int = 9606) -> Dict:
        """
        Get functional enrichment analysis for proteins.
        
        Args:
            identifiers: List of protein identifiers  
            species: Species NCBI taxonomy ID
        """
        params = {
            "identifiers": "\r".join(identifiers),
            "species": species,
            "format": "json"
        }
        return await self._make_request("enrichment", params)

class ReactomeClient(BioDatabaseAPI):
    """Client for Reactome pathway database"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://reactome.org/ContentService/data"

    async def search(self, query: str) -> Dict:
        """
        Search Reactome database.
        
        Args:
            query: Search query string
        """
        params = {
            "query": query,
            "species": "Homo sapiens",
            "types": "Pathway"
        }
        return await self._make_request("query/enhanced", params)

    async def get_pathway_containment(self, pathway_id: str) -> Dict:
        """
        Get events contained in a pathway.
        
        Args:
            pathway_id: Reactome pathway identifier
        """
        return await self._make_request(f"pathway/{pathway_id}/containedEvents")

    async def get_pathway_ancestors(self, event_id: str) -> Dict:
        """
        Get ancestor pathways for an event.
        
        Args:
            event_id: Reactome event identifier  
        """
        return await self._make_request(f"event/{event_id}/ancestors")

class IntActClient(BioDatabaseAPI):
    """Client for IntAct molecular interaction database"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.ebi.ac.uk/intact/ws/interaction"

    async def search(self, query: str, 
                    page: int = 0,
                    page_size: int = 10,
                    negative_filter: str = "POSITIVE_ONLY",
                    min_mi_score: float = 0.0,
                    max_mi_score: float = 1.0) -> Dict:
        """
        Search IntAct database.
        
        Args:
            query: Search query string
            page: Page number for pagination
            page_size: Number of results per page
            negative_filter: Filter type (POSITIVE_ONLY, POSITIVE_AND_NEGATIVE, NEGATIVE_ONLY)
            min_mi_score: Minimum interaction score (0.0-1.0)
            max_mi_score: Maximum interaction score (0.0-1.0)
        """
        params = {
            "query": query,
            "page": page,
            "pageSize": page_size,
            "negativeFilter": negative_filter,
            "minMIScore": min_mi_score,
            "maxMIScore": max_mi_score
        }
        return await self._make_request("findInteractions", params)

    async def get_interactions_by_interactor(self, protein: str,
                                          negative: str = "POSITIVE_ONLY",
                                          min_mi_score: float = 0.0,
                                          max_mi_score: float = 1.0) -> Dict:
        """
        Get interactions for a specific protein.
        
        Args:
            protein: Protein identifier
            negative: Filter for interaction type
            min_mi_score: Minimum interaction score
            max_mi_score: Maximum interaction score
        """
        params = {
            "query": f"id:{protein}",
            "format": "json",
            "negative": negative,
            "minMIScore": min_mi_score,
            "maxMIScore": max_mi_score
        }
        return await self._make_request("findInteractions", params)

class PharmGKBClient(BioDatabaseAPI):
    """Client for PharmGKB pharmacogenomics database"""
    
    def __init__(self):
        super().__init__(self)
        self.base_url = "https://api.pharmgkb.org/v1/data"

    async def search(self, query: str) -> Dict:
        """
        Search PharmGKB database.
        
        Args:
            query: Search query string
        """
        return await self._make_request(f"search?q={query}")

    async def get_pathway(self, pathway_id: str, view: str = "base") -> Dict:
        """
        Get pathway information.
        
        Args:
            pathway_id: PharmGKB pathway identifier
            view: Data view level (min, base, max)
        """
        params = {"view": view}
        return await self._make_request(f"pathway/{pathway_id}", params)

    async def get_gene(self, gene_id: str) -> Dict:
        """
        Get gene information.
        
        Args:
            gene_id: PharmGKB gene identifier
        """
        return await self._make_request(f"gene/{gene_id}")

    async def get_drug_gene_relationships(self, gene_id: str) -> Dict:
        """
        Get drug-gene relationships.
        
        Args:
            gene_id: PharmGKB gene identifier
        """
        return await self._make_request(f"relationships/gene/{gene_id}")

class BioGridClient(BioDatabaseAPI):
    """Client for BioGRID interaction database"""
    
    def __init__(self, access_key: str):
        """
        Initialize BioGRID client.
        
        Args:
            access_key: Required 32-character access key from BioGRID
        """
        super().__init__(api_key=access_key)
        self.base_url = "https://webservice.thebiogrid.org"

    async def search(self, gene_list: List[str],
                    tax_id: Optional[str] = None,
                    search_ids: bool = False,
                    search_names: bool = True,  
                    search_biogrid_ids: bool = False,
                    include_interactors: bool = True,
                    max_results: int = 10000,
                    start: int = 0,
                    format: str = "tab2") -> Dict:
        """
        Search BioGRID database.
        
        Args:
            gene_list: List of gene identifiers
            tax_id: NCBI taxonomy ID (e.g., "9606" for human)
            search_ids: Search ENTREZ_GENE, ORDERED LOCUS and SYSTEMATIC_NAME
            search_names: Search OFFICIAL_SYMBOL
            search_biogrid_ids: Search BioGRID internal IDs
            include_interactors: Include first-order interactors
            max_results: Number of results (1-10000)
            start: Starting result index
            format: Output format (tab1, tab2, json)
        """
        params = {
            "geneList": "|".join(gene_list),
            "searchIds": str(search_ids).lower(),
            "searchNames": str(search_names).lower(),
            "searchBiogridIds": str(search_biogrid_ids).lower(),
            "includeInteractors": str(include_interactors).lower(),
            "max": max_results,
            "start": start,
            "format": format,
            "accessKey": self.api_key
        }
        
        if tax_id:
            params["taxId"] = tax_id
            
        return await self._make_request("interactions", params)

    async def get_interactions(self,
                             gene_list: List[str],
                             tax_id: Optional[str] = None,
                             include_interactors: bool = True,
                             evidence_list: Optional[List[str]] = None,
                             format: str = "tab2") -> Dict:
        """
        Get protein interactions filtered by various parameters.
        
        Args:
            gene_list: List of gene identifiers
            tax_id: NCBI taxonomy ID
            include_interactors: Include first-order interactors
            evidence_list: List of experimental evidence codes
            format: Output format (tab2, json)
        """
        params = {
            "geneList": "|".join(gene_list),
            "includeInteractors": str(include_interactors).lower(),
            "format": format,
            "accessKey": self.api_key
        }
        
        if tax_id:
            params["taxId"] = tax_id
            
        if evidence_list:
            params["evidenceList"] = "|".join(evidence_list)
            
        return await self._make_request("interactions", params)

    async def get_version(self) -> str:
        """Get current BioGRID version."""
        response = await self._make_request("version", {"accessKey": self.api_key})
        return response.text

class BioCyc(BioDatabaseAPI):
    """Client for BioCyc pathway/genome database"""
    def __init__(self,):
        super().__init__()
        self.base_url = "https://websvc.biocyc.org"
        
    async def search(self, query: str) -> Dict:
        """Implement required search method"""
        params = {
            "query": query,
            "organism": "HUMAN",
            "detail": "full"
        }
        return await self._make_request("getSearch", params)

    async def get_metabolic_pathways(self, gene: str) -> Dict:
        """Get metabolic pathways for a gene"""
        params = {
            "gene": gene,
            "organism": "HUMAN"
        }
        return await self._make_request("getMetabolicPathways", params)

    async def get_pathway_details(self, pathway_id: str) -> Dict:
        """Get detailed information about a specific pathway"""
        params = {
            "pathway": pathway_id,
            "detail": "full"
        }
        return await self._make_request("getPathwayData", params)

    async def get_gene_regulation(self, gene: str) -> Dict:
        """Get regulation information for a gene"""
        params = {
            "gene": gene,
            "organism": "HUMAN"
        }
        return await self._make_request("getRegulation", params)
    
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
    