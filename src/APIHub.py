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
from tenacity import retry, stop_after_attempt, wait_exponential
import requests
from src.utils.biochat_api_logging import BioChatLogger


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
            # Create connection with proper timeouts
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            conn = aiohttp.TCPConnector(
                ssl=False,  # Disable SSL verification for testing
                limit=10,   # Limit concurrent connections
                force_close=True  # Force connection closure
            )
            self.session = aiohttp.ClientSession(
                connector=conn,
                timeout=timeout
            )

    async def _close_session(self):
        """Close aiohttp session if exists"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def _make_request(self, endpoint: str, params: Dict = None, delay: float = 0.34) -> Dict:
        """Enhanced request method with better error handling"""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                await self._init_session()
                await asyncio.sleep(delay)
                
                url = f"{self.base_url}/{endpoint}"
                async with self.session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 429:  # Rate limit
                        retry_after = int(response.headers.get('Retry-After', retry_delay))
                        await asyncio.sleep(retry_after)
                        continue
                    response.raise_for_status()
                    response_text = await response.text()
                    try:
                        if "application/json" in response.headers.get("Content-Type", "") or "text/json" in response.headers.get("Content-Type", ""):
                            return json.loads(response_text)  # Use json.loads() instead of response.json()
                        else:
                            BioChatLogger.log_error("Unexpected response format", Exception(f"Headers: {response.headers}"))
                            return None
                    except json.JSONDecodeError:
                        BioChatLogger.log_error("Failed to decode JSON", Exception(response_text[:500]))
                        return None
                    
            except aiohttp.ClientError as e:
                BioChatLogger.log_error(f"API request error", e)
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(retry_delay * (attempt + 1))
                
            except Exception as e:
                BioChatLogger.log_error(f"Unexpected error in API request", e)
                raise

    async def __aenter__(self):
        await self._init_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close_session()
    
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
            BioChatLogger.log_error(f"Raw request error", e)
            raise


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
            BioChatLogger.log_error(f"Error in search_and_analyze", e)
            return {"error": str(e)}

class StringDBClient(BioDatabaseAPI):
    def __init__(self, caller_identity: str = 'HBP'):
        super().__init__()
        self.base_url = "https://string-db.org/api"  # Updated base URL
        self.caller_identity = caller_identity
        self.headers = {"Content-Type": "text/json"}

    async def search(self, query: str) -> Dict:
        """Implement the abstract search method for STRING-DB"""
        try:
            # Convert gene/protein name to identifier format
            params = {
                "identifiers": query,
                "species": 9606,  # Human
                "network_type": "functional",
                "caller_identity": self.caller_identity
            }
            return await self._make_request("json/interaction_partners", params)
        except Exception as e:
            BioChatLogger.log_error(f"STRING-DB search error", e)
            return {"error": str(e)}
        
    async def get_interaction_partners(self, 
                                    identifiers: Union[str, List[str]], 
                                    species: int = 9606,
                                    required_score: int = 0,
                                    network_type: str = "functional") -> Dict:
        """Get protein interaction partners"""
        if isinstance(identifiers, list):
            identifiers = "%0d".join(identifiers)  # Updated separator
            
        params = {
            "identifiers": identifiers,
            "species": species,
            "required_score": required_score,
            "network_type": network_type,
            "caller_identity": self.caller_identity
        }
        return await self._make_request("json/interaction_partners", params)

    async def get_enrichment(self,
                           identifiers: Union[str, List[str]],
                           species: int = 9606) -> Dict:
        """Get functional enrichment analysis"""
        if isinstance(identifiers, list):
            identifiers = "%0d".join(identifiers)
            
        params = {
            "identifiers": identifiers,
            "species": species,
            "caller_identity": self.caller_identity
        }
        return await self._make_request("json/enrichment", params)

    async def get_ppi_enrichment(self,
                               identifiers: Union[str, List[str]],
                               background_identifiers: Optional[List[str]] = None) -> Dict:
        """Get protein-protein interaction enrichment"""
        if isinstance(identifiers, list):
            identifiers = "%0d".join(identifiers)
            
        params = {
            "identifiers": identifiers,
            "caller_identity": self.caller_identity
        }
        if background_identifiers:
            params["background_string_identifiers"] = "%0d".join(background_identifiers)
            
        return await self._make_request("json/ppi_enrichment", params)


class ReactomeClient(BioDatabaseAPI):
    """Client for Reactome Content Service API"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://reactome.org/ContentService/"
        self.headers = {"Content-Type": "application/json"}
    
    async def search(self, query: str) -> Dict:
        """Base search method implementation"""
        try:
            params = {
                "query": query,
                "species": "Homo sapiens",
                "types": "Pathway"
            }
            endpoint = "search/query"
            return await self._make_request(endpoint, params)
        except Exception as e:
            BioChatLogger.log_error(f"Reactome search error", e)
            return {"error": str(e)}

    async def get_pathways_for_gene(self, gene_name: str) -> Dict:
        try:
            BioChatLogger.log_info(f"Get uniprot id for gene {gene_name}")
            uniprot_id = self.get_primary_uniprot_id(gene_name.strip())
            if not uniprot_id:
                raise ValueError(f"No UniProt ID found for gene {gene_name}")

            reactome_id = self.get_reactome_id(uniprot_id)
            if not reactome_id:
                raise ValueError(f"No Reactome ID found for UniProt ID {uniprot_id}")

            pathways = await self.get_pathway_details(reactome_id)
            if not pathways:
                return {"error": f"No pathways found for UniProt ID {uniprot_id}"}

            return {"pathways": pathways, "count": len(pathways)}
            
        except Exception as e:
            BioChatLogger.log_error(f"Error getting pathways for gene {gene_name}", e)
            return {"error": str(e)}


    async def get_pathway_details(self, pathway_id: str) -> Dict:
        """
        Get detailed information about a specific pathway
        
        Args:
            pathway_id: Reactome pathway ID (e.g., R-HSA-1234)
            
        Returns:
            Dict containing pathway details and participants
        """
        try:
            # Get basic pathway information
            endpoint = f"data/pathway/{pathway_id}/containedEvents"
            details = await self._make_request(endpoint)
            return details
            
        except Exception as e:
            BioChatLogger.log_error(f"Error getting pathway details for {pathway_id}", e)
            return {"error": str(e)}

    def get_primary_uniprot_id(self, gene_name: str) -> Optional[str]:
        """
        Fetch the primary UniProt ID (canonical) for a given gene name.
        Prioritizes reviewed (SwissProt) entries.

        Args:
            gene_name: Gene symbol to search for

        Returns:
            Optional[str]: UniProt ID if found, None otherwise
        """
        query = f"(gene:{gene_name}) AND (reviewed:true OR reviewed:false)"
        url = f"https://rest.uniprot.org/uniprotkb/search?query={query}&fields=accession,reviewed,gene_names&format=json"


        BioChatLogger.log_info(f"Fetching UniProt ID from URL: {url}")

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            BioChatLogger.log_info(f"UniProt API Response: {json.dumps(data, indent=4)[:1000]}")

            if not data.get('results'):
                BioChatLogger.log_info(f"No UniProt entries found for gene {gene_name}")
                return None

            for entry in data['results']:
                if "Swiss-Prot" in entry.get('entryType', ''):
                    for gene in entry.get('genes', []):
                        gene_name_value = gene.get('geneName', {}).get('value', '').upper()
                        if gene_name.upper() == gene_name_value:
                            uniprot_id = entry['primaryAccession']
                            BioChatLogger.log_info(f"✅ Found reviewed UniProt ID for {gene_name}: {uniprot_id}")
                            return uniprot_id

            BioChatLogger.log_info(f"No reviewed match found for {gene_name}")
            return None

        except requests.exceptions.RequestException as e:
            BioChatLogger.log_error(f"Failed to fetch UniProt ID for {gene_name}: {str(e)}", e)
            return None

     
    def get_reactome_id(self, uniprot_id: str) -> Optional[str]:
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
            print(f"Error fetching Reactome ID for {uniprot_id}", e)
            return None
    
    async def get_uniprot_mapping(self, uniprot_id: str) -> Dict:
        """
        Get all Reactome mappings for a UniProt ID
        
        Args:
            uniprot_id: UniProt accession number
        """
        try:
            endpoint = f"data/mapping/UniProt/{uniprot_id}"
            return await self._make_request(endpoint)
        except Exception as e:
            BioChatLogger.log_error(f"Error getting UniProt mapping for {uniprot_id}", e)
            return {"error": str(e)}

    async def get_disease_events(self, disease_id: str) -> Dict:
        """
        Get events associated with a disease
        
        Args:
            disease_id: Disease identifier
        """
        try:
            endpoint = f"data/diseases/{disease_id}/events"
            return await self._make_request(endpoint)
        except Exception as e:
            BioChatLogger.log_error(f"Error getting disease events for {disease_id}", e)
            return {"error": str(e)}

class IntActClient(BioDatabaseAPI):
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.ebi.ac.uk/intact/ws/interaction"

    async def search(self, 
                    query: str, 
                    species: Optional[str] = None,
                    negative_filter: str = "POSITIVE_ONLY",
                    page: int = 0,
                    page_size: int = 10) -> Dict:
        """Search molecular interactions using the findInteractions endpoint"""
        params = {
            "query": query,
            "page": page,
            "pageSize": page_size,
            "negativeFilter": negative_filter
        }
        if species:
            params["species"] = species
            
        return await self._make_request("findInteractions", params)

    async def get_interaction_partners(self,
                                    protein_id: str,
                                    species: Optional[str] = None) -> Dict:
        """Get detailed interaction partners for a specific protein"""
        params = {
            "query": f"id:{protein_id}",
            "format": "json"
        }
        if species:
            params["species"] = species
            
        return await self._make_request("interaction_partners", params)
        
    async def get_interaction_facets(self,
                                   query: str,
                                   interaction_types: Optional[List[str]] = None) -> Dict:
        """Get interaction statistics and metadata"""
        params = {
            "query": query
        }
        if interaction_types:
            params["interactionTypesFilter"] = ",".join(interaction_types)
            
        return await self._make_request("findInteractionFacets", params)

class PharmGKBClient(BioDatabaseAPI):
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.pharmgkb.org/v1/data"

    async def search(self, query: str) -> Dict:
        """Implement the abstract search method for PharmGKB"""
        try:
            # Use general search endpoint with query
            params = {
                "q": query,
                "view": "base"  # Basic view level
            }
            return await self._make_request("search", params)
        except Exception as e:
            BioChatLogger.log_error(f"PharmGKB search error", e)
            return {"error": str(e)}
        
    async def get_clinical_annotations(self, 
                                    drug_id: Optional[str] = None,
                                    gene_id: Optional[str] = None) -> Dict:
        """Get drug-gene clinical associations"""
        params = {}
        if drug_id:
            params["drugId"] = drug_id
        if gene_id:
            params["geneId"] = gene_id
            
        return await self._make_request("clinicalAnnotation", params)

    async def get_drug_labels(self,
                            drug_id: str,
                            source: Optional[str] = None) -> Dict:
        """Access drug labeling information"""
        params = {
            "drugId": drug_id
        }
        if source:
            params["source"] = source
            
        return await self._make_request("label", params)

    async def get_variant_annotations(self,
                                   variant_id: str,
                                   drug_id: Optional[str] = None) -> Dict:
        """Get variant-drug associations"""
        params = {
            "variantId": variant_id
        }
        if drug_id:
            params["drugId"] = drug_id
            
        return await self._make_request("variantAnnotation", params)

    async def get_pathways(self,
                          drug_id: Optional[str] = None,
                          gene_id: Optional[str] = None) -> Dict:
        """Access pharmacogenomic pathways"""
        params = {}
        if drug_id:
            params["drugId"] = drug_id
        if gene_id:
            params["geneId"] = gene_id
            
        return await self._make_request("pathway", params)

    async def get_disease_associations(self,
                                    disease_id: str,
                                    association_type: Optional[str] = None) -> Dict:
        """Get disease-drug-gene relationships"""
        params = {
            "diseaseId": disease_id
        }
        if association_type:
            params["associationType"] = association_type
            
        return await self._make_request("disease", params)

class BioGridClient(BioDatabaseAPI):
    def __init__(self, access_key: str):
        super().__init__(api_key=access_key)
        self.base_url = "https://webservice.thebiogrid.org"

    async def search(self, query: str) -> Dict:
        """Implement the abstract search method for BioGRID"""
        try:
            params = {
                "geneList": query,
                "searchIds": "true",
                "searchNames": "true",
                "format": "json",
                "accessKey": self.api_key
            }
            return await self._make_request("interactions", params)
        except Exception as e:
            BioChatLogger.log_error(f"BioGRID search error", e)
            return {"error": str(e)}
    
    async def get_core_interactions(self,
                                  gene_list: List[str],
                                  include_interactors: bool = False,
                                  tax_id: Optional[str] = None) -> Dict:
        """Get protein-protein interactions"""
        params = {
            "geneList": "|".join(gene_list),
            "includeInteractors": str(include_interactors).lower(),
            "format": "json",
            "accessKey": self.api_key
        }
        if tax_id:
            params["taxId"] = tax_id
            
        return await self._make_request("interactions", params)

    async def get_experimental_evidence(self, format: str = "json") -> Dict:
        """Get interaction evidence types"""
        params = {
            "accessKey": self.api_key,
            "format": format
        }
        return await self._make_request("evidence", params)

    async def get_chemical_interactions(self,
                                     gene_list: List[str],
                                     chemical_list: Optional[List[str]] = None,
                                     evidence_list: Optional[List[str]] = None) -> Dict:
        """Get protein-chemical interactions"""
        params = {
            "geneList": "|".join(gene_list),
            "format": "json",
            "accessKey": self.api_key
        }
        if chemical_list:
            params["chemicalList"] = "|".join(chemical_list)
        if evidence_list:
            params["evidenceList"] = "|".join(evidence_list)
            
        return await self._make_request("interactions", params)

    async def get_disease_interactions(self,
                                    gene_list: List[str],
                                    throughput_tag: Optional[str] = None,
                                    evidence_list: Optional[List[str]] = None) -> Dict:
        """Get disease-related interactions"""
        params = {
            "geneList": "|".join(gene_list),
            "format": "json",
            "accessKey": self.api_key
        }
        if throughput_tag:
            params["throughputTag"] = throughput_tag
        if evidence_list:
            params["evidenceList"] = "|".join(evidence_list)
            
        return await self._make_request("interactions", params)

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
                BioChatLogger.log_error(f"Error getting BioCyc data for {gene}", e)
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
            BioChatLogger.log_error(f"Ensembl search error", e)
            return {"error": str(e)}
    
    async def get_variants(self, chromosome: str, start: int, end: int, 
                       species: str = "homo_sapiens") -> Dict:
        """Get genetic variants in a genomic region."""
        try:
            endpoint = f"overlap/region/{species}/{chromosome}:{start}-{end}/variation"
            return await self._make_request(endpoint)
        except Exception as e:
            BioChatLogger.log_error(f"Variant search error", e)
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
            BioChatLogger.log_error(f"GWAS search error", e)
            return {"error": str(e)}
    
    async def get_associations(self, study_id: str) -> Dict:
        """Get associations for a study."""
        try:
            return await self._make_request(f"studies/{study_id}/associations")
        except Exception as e:
            BioChatLogger.log_error(f"GWAS associations error", e)
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
            BioChatLogger.log_error(f"UniProt search error", e)
            return {"error": str(e)}
    
    async def get_protein_features(self, uniprot_id: str) -> Dict:
        """Get protein features."""
        try:
            response = await self._make_request(f"uniprotkb/{uniprot_id}")
            return response
        except Exception as e:
            BioChatLogger.log_error(f"Protein features error", e)
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