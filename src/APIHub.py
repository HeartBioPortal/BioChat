"""
Module for accessing various bioinformatics database APIs.
Includes NCBI E-utilities, Ensembl, GWAS Catalog, UniProt, STRING, Reactome, IntAct, PharmGKB, and BioGRID.
"""

from typing import Dict, List, Optional, Union
from abc import ABC, abstractmethod
import json
import xml.etree.ElementTree as ET
from datetime import datetime
import time
import aiohttp
import asyncio
import logging
import ssl

logger = logging.getLogger(__name__)

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
        self.session: Optional[aiohttp.ClientSession] = None
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    async def _init_session(self):
        """Initialize aiohttp session if not exists"""
        if self.session is None or self.session.closed:
            # Create SSL context that doesn't verify certificates
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            conn = aiohttp.TCPConnector(ssl=ssl_context)
            self.session = aiohttp.ClientSession(connector=conn)

    async def _close_session(self):
        """Close aiohttp session if exists"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def _make_request(self, endpoint: str, params: Dict = None, delay: float = 0.34) -> Dict:
        """
        Helper method to make async HTTP requests with rate limiting.
        Args:
            endpoint: API endpoint
            params: Query parameters
            delay: Time to wait between requests (default: 0.34s for NCBI compliance)
        """
        await self._init_session()
        await asyncio.sleep(delay)
        
        url = f"{self.base_url}/{endpoint}"
        try:
            async with self.session.get(url, headers=self.headers, params=params) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"API request error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in API request: {str(e)}")
            raise
    
    @abstractmethod
    async def search(self, query: str) -> Dict:
        """Base search method to be implemented by child classes."""
        pass

    async def _make_raw_request(self, endpoint: str, params: Dict = None, delay: float = 0.34) -> str:
        """Make request and return raw text response"""
        await self._init_session()
        await asyncio.sleep(delay)
        
        url = f"{self.base_url}/{endpoint}"
        try:
            async with self.session.get(url, headers=self.headers, params=params) as response:
                response.raise_for_status()
                return await response.text()
        except Exception as e:
            logger.error(f"Raw request error: {str(e)}")
            raise

    async def __aenter__(self):
        """Async context manager enter"""
        await self._init_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._close_session()

class NCBIEutils(BioDatabaseAPI):
    """Enhanced NCBI E-utilities API client with advanced PubMed search capabilities."""
    
    def __init__(self, api_key: Optional[str] = None, tool: str = "python_bio_api", email: Optional[str] = None):
        super().__init__(api_key=api_key, tool=tool, email=email)
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    async def search(self, query: str) -> Dict:
        """Implement the abstract search method for NCBI"""
        params = self._build_base_params()
        params.update({
            "db": "pubmed",
            "term": query,
            "retmode": "json"
        })
        return await self._make_request("esearch.fcgi", params)
        
    def _build_base_params(self) -> Dict:
        """Build base parameters required for E-utilities."""
        params = {
            "tool": self.tool
        }
        if self.api_key:
            params["api_key"] = self.api_key
        if self.email:
            params["email"] = self.email
        return params

    async def search_pubmed(self, 
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
        """
        query_parts = []
        
        if genes:
            gene_query = ' OR '.join([f"{gene}[Gene Symbol]" for gene in genes])
            query_parts.append(f"({gene_query})")
            
        if phenotypes:
            phenotype_query = ' OR '.join([f"{pheno}[MeSH Terms]" for pheno in phenotypes])
            query_parts.append(f"({phenotype_query})")
            
        if additional_terms:
            terms_query = ' AND '.join([f"({term})" for term in additional_terms])
            query_parts.append(terms_query)
            
        final_query = ' AND '.join(query_parts)
        
        if date_range:
            start_date, end_date = date_range
            final_query += f" AND ({start_date}[Date - Publication] : {end_date}[Date - Publication])"
        
        search_params = self._build_base_params()
        search_params.update({
            "db": "pubmed",
            "term": final_query,
            "retmax": max_results,
            "retmode": "json",
            "usehistory": "y"
        })
        
        search_result = await self._make_request("esearch.fcgi", search_params)
        
        if 'esearchresult' in search_result and 'idlist' in search_result['esearchresult']:
            ids = search_result['esearchresult']['idlist']
            return await self.fetch_pubmed_details(ids)
        
        return search_result

    async def fetch_pubmed_details(self, id_list: List[str]) -> Dict:
        """
        Fetch detailed information for PubMed articles.
        
        Args:
            id_list: List of PubMed IDs
        """
        summary_params = self._build_base_params()
        summary_params.update({
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "json"
        })
        
        return await self._make_request("esummary.fcgi", summary_params)

    async def extract_abstracts(self, id_list: List[str]) -> Dict[str, str]:
        """
        Fetch and extract abstracts for given PubMed IDs.
        
        Args:
            id_list: List of PubMed IDs
        """
        fetch_params = self._build_base_params()
        fetch_params.update({
            "db": "pubmed",
            "id": ",".join(id_list),
            "rettype": "abstract",
            "retmode": "xml"
        })
        
        response = await self._make_raw_request("efetch.fcgi", fetch_params)
        root = ET.fromstring(response)
        
        abstracts = {}
        for article in root.findall(".//PubmedArticle"):
            pmid = article.find(".//PMID").text
            abstract_element = article.find(".//Abstract/AbstractText")
            if abstract_element is not None:
                abstracts[pmid] = abstract_element.text
            else:
                abstracts[pmid] = None
                
        return abstracts

    async def search_and_analyze(self,
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
        """
        try:
            search_results = await self.search_pubmed(
                genes=genes,
                phenotypes=phenotypes,
                additional_terms=additional_terms,
                max_results=max_results
            )
            
            if 'result' in search_results:
                pmids = list(search_results['result'].keys())
                if 'uids' in search_results['result']:
                    pmids = search_results['result']['uids']
            else:
                return {"error": "No results found"}
                
            abstracts = await self.extract_abstracts(pmids)
            
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
            
        except Exception as e:
            logger.error(f"Error in search_and_analyze: {str(e)}")
            return {"error": str(e)}

class StringDBClient(BioDatabaseAPI):
    def __init__(self, caller_identity: str = 'HBP'):
        super().__init__()
        # Correct base URL from documentation
        self.base_url = "https://version-12-0.string-db.org/api"
        self.caller_identity = caller_identity
        
    async def search(self, 
                           identifiers: Union[str, List[str]], 
                           species: int = 9606,
                           required_score: int = 0,  # Changed to match docs (0-1000)
                           network_type: str = "functional") -> Dict:
        """
        Get protein interactions matching documented parameters.
        
        Args:
            identifiers: protein identifiers (separated by \r)
            species: NCBI taxonomy ID (e.g., 9606 for human)
            required_score: threshold (0-1000)
            network_type: functional (default) or physical
        """
        if isinstance(identifiers, list):
            identifiers = "\r".join(identifiers)
            
        params = {
            "identifiers": identifiers,
            "species": species,
            "required_score": required_score,
            "network_type": network_type,
            "caller_identity": self.caller_identity  # Required per docs
        }
        return await self._make_request("tsv/interaction_partners", params)

    async def get_network_image(self, 
                            identifiers: List[str], 
                            species: int = 9606,
                            network_flavor: str = "confidence",
                            required_score: int = 400) -> bytes:
        """
        Get network image visualization for proteins.
        """
        params = {
            "identifiers": "\r".join(identifiers),
            "species": species,
            "network_flavor": network_flavor,
            "required_score": required_score,
            "format": "image"
        }
        response = await self._make_raw_request("image/network", params)
        return response

    async def get_functional_enrichment(self, 
                                    identifiers: List[str],
                                    species: int = 9606) -> Dict:
        """
        Get functional enrichment analysis for proteins.
        """
        params = {
            "identifiers": "\r".join(identifiers),
            "species": species,
            "format": "json"
        }
        return await self._make_request("enrichment", params)


class ReactomeClient(BioDatabaseAPI):
    """Client for Reactome Content Service API"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://reactome.org/ContentService/data"
        self.headers = {"Content-Type": "application/json"}

    async def search(self, query: str) -> Dict:
        """Base search method implementation"""
        try:
            # Use search/query endpoint with pathway type
            params = {
                "query": query,
                "species": "Homo sapiens",
                "types": "Pathway"
            }
            endpoint = "search/query"
            return await self._make_request(endpoint, params)
        except Exception as e:
            logger.error(f"Reactome search error: {str(e)}")
            return {"error": str(e)}

    async def get_pathways_for_gene(self, gene_id: str) -> Dict:
        """Get pathways involving a specific gene/protein"""
        try:
            # Use entity/pathways endpoint with UniProt ID
            endpoint = f"entity/{gene_id}/pathways"
            return await self._make_request(endpoint)
        except Exception as e:
            logger.error(f"Error getting pathways for gene {gene_id}: {str(e)}")
            return {"error": str(e)}

    async def get_pathway_details(self, pathway_id: str) -> Dict:
        """Get detailed information about a specific pathway"""
        try:
            # Use pathway endpoint
            endpoint = f"pathway/{pathway_id}"
            details = await self._make_request(endpoint)
            
            # Get additional pathway information
            summation = await self._make_request(f"event/{pathway_id}/summation")
            participants = await self._make_request(f"pathway/{pathway_id}/participants")
            
            return {
                "details": details,
                "summation": summation,
                "participants": participants
            }
        except Exception as e:
            logger.error(f"Error getting pathway details for {pathway_id}: {str(e)}")
            return {"error": str(e)}

    async def get_pathway_hierarchy(self, pathway_id: str) -> Dict:
        """Get the hierarchical structure of a pathway"""
        try:
            endpoint = f"pathway/{pathway_id}/hierarchy"
            return await self._make_request(endpoint)
        except Exception as e:
            logger.error(f"Error getting pathway hierarchy for {pathway_id}: {str(e)}")
            return {"error": str(e)}

    async def get_disease_events(self, disease_id: str) -> Dict:
        """Get events associated with a disease"""
        try:
            endpoint = f"disease/{disease_id}/events"
            return await self._make_request(endpoint)
        except Exception as e:
            logger.error(f"Error getting disease events for {disease_id}: {str(e)}")
            return {"error": str(e)}


class IntActClient(BioDatabaseAPI):
    """Client for IntAct molecular interaction database"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.ebi.ac.uk/intact/ws/interaction"

    async def search(self, 
                  query: str, 
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

    async def get_molecular_interactions(self, 
                                    protein: str,
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
        try:
            return await self._make_request("findInteractions", params)
        except Exception as e:
            logger.error(f"Error getting molecular interactions for {protein}: {str(e)}")
            return {"error": str(e)}

class PharmGKBClient(BioDatabaseAPI):
    """Client for PharmGKB pharmacogenomics database"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.pharmgkb.org/v1/data"

    async def search(self, query: str) -> Dict:
        """
        Search PharmGKB database.
        
        Args:
            query: Search query string
        """
        try:
            return await self._make_request(f"search?q={query}")
        except Exception as e:
            logger.error(f"PharmGKB search error: {str(e)}")
            return {"error": str(e)}

    async def get_pathway(self, pathway_id: str, view: str = "base") -> Dict:
        """
        Get pathway information.
        
        Args:
            pathway_id: PharmGKB pathway identifier
            view: Data view level (min, base, max)
        """
        params = {"view": view}
        try:
            return await self._make_request(f"pathway/{pathway_id}", params)
        except Exception as e:
            logger.error(f"Error getting pathway {pathway_id}: {str(e)}")
            return {"error": str(e)}

    async def get_gene(self, gene_id: str) -> Dict:
        """
        Get gene information.
        
        Args:
            gene_id: PharmGKB gene identifier
        """
        try:
            return await self._make_request(f"gene/{gene_id}")
        except Exception as e:
            logger.error(f"Error getting gene {gene_id}: {str(e)}")
            return {"error": str(e)}

    async def get_drug_gene_relationships(self, gene_id: str) -> Dict:
        """
        Get drug-gene relationships.
        
        Args:
            gene_id: PharmGKB gene identifier
        """
        try:
            return await self._make_request(f"relationships/gene/{gene_id}")
        except Exception as e:
            logger.error(f"Error getting drug-gene relationships for {gene_id}: {str(e)}")
            return {"error": str(e)}

class BioGridClient(BioDatabaseAPI):
    """Client for BioGRID interaction database"""
    
    def __init__(self, access_key: str):
        super().__init__(api_key=access_key)
        self.base_url = "https://webservice.thebiogrid.org"

    async def search(self, gene_list: List[str],
                  tax_id: Optional[str] = None,
                  max_results: int = 10000) -> Dict:
        """Search BioGRID database."""
        params = {
            "geneList": "|".join(gene_list),
            "searchIds": "true",
            "searchNames": "true",
            "max": max_results,
            "format": "json",
            "accessKey": self.api_key
        }
        if tax_id:
            params["taxId"] = tax_id
            
        return await self._make_request("interactions", params)

    async def get_interactions(self,
                           protein_id: str,
                           max_results: int = 100) -> Dict:
        """Get protein interactions."""
        try:
            params = {
                "geneList": protein_id,
                "searchNames": "true",
                "max": max_results,
                "format": "json",
                "accessKey": self.api_key
            }
            return await self._make_request("interactions", params)
        except Exception as e:
            logger.error(f"BioGRID interaction error for {protein_id}: {str(e)}")
            return {"error": str(e)}

class BioCyc(BioDatabaseAPI):
    """Client for BioCyc pathway/genome database"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://websvc.biocyc.org"
        
    async def search(self, query: str) -> Dict:
        """Search BioCyc database."""
        params = {
            "query": query,
            "organism": "HUMAN",
            "detail": "full"
        }
        return await self._make_request("getSearch", params)

    async def get_pathways(self, genes: List[str], include_children: bool = True) -> Dict:
        """Get pathway data for genes."""
        results = {}
        for gene in genes:
            try:
                gene_results = {
                    "pathways": await self.get_metabolic_pathways(gene),
                    "regulation": await self.get_gene_regulation(gene)
                }
                results[gene] = gene_results
            except Exception as e:
                logger.error(f"Error getting BioCyc data for {gene}: {str(e)}")
                results[gene] = {"error": str(e)}
        return results

    async def get_metabolic_pathways(self, gene: str) -> Dict:
        """Get metabolic pathways for a gene."""
        params = {"gene": gene, "organism": "HUMAN"}
        return await self._make_request("getMetabolicPathways", params)

    async def get_pathway_details(self, pathway_id: str) -> Dict:
        """Get detailed pathway information."""
        params = {"pathway": pathway_id, "detail": "full"}
        return await self._make_request("getPathwayData", params)

class EnsemblAPI(BioDatabaseAPI):
    """Ensembl REST API client."""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://rest.ensembl.org"
        self.headers["Content-Type"] = "application/json"
    
    async def search(self, query: str, species: str = "homo_sapiens") -> Dict:
        """Search Ensembl database."""
        try:
            endpoint = f"lookup/symbol/{species}/{query}"
            return await self._make_request(endpoint)
        except Exception as e:
            logger.error(f"Ensembl search error: {str(e)}")
            return {"error": str(e)}
    
    async def get_variants(self, chromosome: str, start: int, end: int, 
                       species: str = "homo_sapiens") -> Dict:
        """Get genetic variants in a genomic region."""
        try:
            endpoint = f"overlap/region/{species}/{chromosome}:{start}-{end}/variation"
            return await self._make_request(endpoint)
        except Exception as e:
            logger.error(f"Variant search error: {str(e)}")
            return {"error": str(e)}

class GWASCatalog(BioDatabaseAPI):
    """GWAS Catalog API client."""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.ebi.ac.uk/gwas/rest/api"
    
    async def search(self, query: str) -> Dict:
        """Search GWAS Catalog."""
        try:
            params = {"q": query}
            return await self._make_request("studies/search", params)
        except Exception as e:
            logger.error(f"GWAS search error: {str(e)}")
            return {"error": str(e)}
    
    async def get_associations(self, study_id: str) -> Dict:
        """Get associations for a study."""
        try:
            return await self._make_request(f"studies/{study_id}/associations")
        except Exception as e:
            logger.error(f"GWAS associations error: {str(e)}")
            return {"error": str(e)}

# In APIHub.py - Updated UniProtAPI class
class UniProtAPI(BioDatabaseAPI):
    """UniProt API client."""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://rest.uniprot.org"
    
    async def search(self, query: str) -> Dict:
        """Search UniProt database."""
        try:
            params = {
                "query": query,
                "format": "json"
            }
            response = await self._make_request("uniprotkb/search", params)
            # Format the response to ensure it has the expected structure
            if 'results' in response:
                return {
                    'results': [{
                        'id': item.get('primaryAccession'),
                        'entry': item.get('entryType'),
                        'protein_name': item.get('proteinDescription', {}).get('recommendedName', {}).get('fullName', {}).get('value'),
                        'gene_names': [gene.get('value') for gene in item.get('genes', []) if gene.get('value')],
                        'organism': item.get('organism', {}).get('scientificName')
                    } for item in response['results']]
                }
            return {'results': []}
        except Exception as e:
            logger.error(f"UniProt search error: {str(e)}")
            return {"error": str(e)}
    
    async def get_protein_features(self, uniprot_id: str) -> Dict:
        """Get protein features."""
        try:
            response = await self._make_request(f"uniprotkb/{uniprot_id}")
            return response
        except Exception as e:
            logger.error(f"Protein features error: {str(e)}")
            return {"error": str(e)}


class OpenTargetsClient:
    """Client for interacting with Open Targets Platform API"""
    
    def __init__(self):
        self.base_url = "https://platform.opentargets.org/api/public"
        self.headers = {"Content-Type": "application/json"}

    async def search(self, query: str, entity: str = None, size: int = 10) -> Dict:
        """Search across targets, diseases, and drugs"""
        params = {
            "q": query,
            "size": size
        }
        if entity:
            params["entity"] = entity
            
        response = await self._make_request("search", params=params)
        return response

    async def get_target_info(self, target_id: str) -> Dict:
        """Get detailed information about a target"""
        response = await self._make_request(f"target/{target_id}")
        return response

    async def get_disease_info(self, disease_id: str) -> Dict:
        """Get detailed information about a disease"""
        response = await self._make_request(f"disease/{disease_id}")
        return response

    async def get_target_disease_associations(self, 
        target_id: str = None,
        disease_id: str = None,
        score_min: float = 0.0,
        size: int = 10
    ) -> Dict:
        """Get associations between targets and diseases"""
        payload = {
            "scorevalue_min": score_min,
            "size": size
        }
        if target_id:
            payload["target"] = target_id
        if disease_id:
            payload["disease"] = disease_id

        response = await self._make_request("association/filter", method="POST", json=payload)
        return response

    async def get_target_safety(self, target_id: str) -> Dict:
        """Get safety information for a target"""
        response = await self._make_request(f"target/{target_id}/safety")
        return response

    async def get_known_drugs(self, target_id: str, size: int = 10) -> Dict:
        """Get known drugs for a target"""
        params = {"size": size}
        response = await self._make_request(f"target/{target_id}/known_drugs", params=params)
        return response

    async def get_target_expression(self, target_id: str) -> Dict:
        """Get expression data for a target"""
        response = await self._make_request(f"target/{target_id}/expression")
        return response

    async def _make_request(
        self, 
        endpoint: str, 
        method: str = "GET",
        params: Dict = None,
        json: Dict = None
    ) -> Dict:
        """Make HTTP request to Open Targets API"""
        url = f"{self.base_url}/{endpoint}"
        
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, params=params, headers=self.headers)
            else:  # POST
                response = await client.post(url, params=params, json=json, headers=self.headers)
            
            response.raise_for_status()
            return response.json()