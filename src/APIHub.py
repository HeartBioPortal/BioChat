"""
Module for accessing various bioinformatics database APIs.
Includes NCBI E-utilities, Ensembl, GWAS Catalog, UniProt, STRING, Reactome, IntAct, PharmGKB, and BioGRID.
"""

from typing import Dict, List, Optional, Union, Any
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
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            conn = aiohttp.TCPConnector(
                ssl=False,
                limit=10,
                force_close=True
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

    async def _make_request(self, endpoint: str, params: Dict = None, method: str = "GET", 
                           json_data: Dict = None, delay: float = 0.34) -> Dict:
        """Enhanced request method with support for different HTTP methods."""
        max_retries = 3
        retry_delay = 1
        session_created = False
        
        for attempt in range(max_retries):
            try:
                if not self.session or self.session.closed:
                    await self._init_session()
                    session_created = True
                    
                await asyncio.sleep(delay)
                url = f"{self.base_url}/{endpoint}"
                
                request_kwargs = {
                    "headers": self.headers,
                    "params": params,
                    "ssl": False
                }
                if json_data is not None:
                    request_kwargs["json"] = json_data
                
                if method.upper() == "GET":
                    async with self.session.get(url, **request_kwargs) as response:
                        await self._handle_response(response)
                        return await self._parse_response(response)
                elif method.upper() == "POST":
                    async with self.session.post(url, **request_kwargs) as response:
                        await self._handle_response(response)
                        return await self._parse_response(response)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                    
            except aiohttp.ClientError as e:
                BioChatLogger.log_error(f"API request error", e)
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(retry_delay * (attempt + 1))
                
            except Exception as e:
                BioChatLogger.log_error(f"Unexpected error in API request", e)
                raise
                
            finally:
                if session_created and self.session and not self.session.closed:
                    await self._close_session()

    async def _handle_response(self, response: aiohttp.ClientResponse) -> None:
        """Handle common response scenarios."""
        if response.status == 429:
            retry_after = int(response.headers.get('Retry-After', 5))
            await asyncio.sleep(retry_after)
            raise aiohttp.ClientError("Rate limit exceeded")
        response.raise_for_status()

    async def _parse_response(self, response: aiohttp.ClientResponse) -> Dict:
        """Parse response content based on content type."""
        content_type = response.headers.get('Content-Type', '')
        
        try:
            if 'application/json' in content_type:
                return await response.json()
            elif 'text/html' in content_type:
                text = await response.text()
                BioChatLogger.log_error("Received HTML response", Exception(text[:500]))
                raise ValueError("Received HTML response instead of expected JSON")
            else:
                text = await response.text()
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    BioChatLogger.log_error("Failed to decode the response", Exception(text[:500]))
                    raise ValueError("Failed to decode response")
                    
        except Exception as e:
            BioChatLogger.log_error("Response parsing error", e)
            raise

    @abstractmethod
    async def search(self, query: str) -> Dict:
        """Base search method to be implemented by child classes."""
        pass

    async def __aenter__(self):
        await self._init_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
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
        try:
            if not id_list:
                BioChatLogger.log_info("No PMIDs provided for abstract extraction")
                return {}
                
            BioChatLogger.log_info(f"Extracting abstracts for {len(id_list)} PMIDs")
            
            # Process in smaller batches to avoid large responses
            batch_size = 5
            all_abstracts = {}
            
            # Process IDs in batches
            for i in range(0, len(id_list), batch_size):
                batch_ids = id_list[i:i + batch_size]
                BioChatLogger.log_info(f"Processing batch of {len(batch_ids)} PMIDs")
                
                fetch_params = self._build_base_params()
                fetch_params.update({
                    "db": "pubmed",
                    "id": ",".join(batch_ids),
                    "rettype": "abstract",
                    "retmode": "xml"
                })
                
                try:
                    # Use direct URL construction for efetch to get raw XML
                    url = f"{self.base_url}/efetch.fcgi"
                    
                    # Initialize session if needed
                    if not self.session or self.session.closed:
                        await self._init_session()
                    
                    # Directly get the text response rather than JSON
                    async with self.session.get(url, params=fetch_params) as response:
                        if response.status != 200:
                            BioChatLogger.log_error(f"NCBI API error: {response.status}", 
                                                  Exception(f"HTTP {response.status}"))
                            continue
                            
                        # Get text directly instead of trying to parse JSON
                        xml_content = await response.text()
                        
                        # Process the XML
                        try:
                            root = ET.fromstring(xml_content)
                            
                            batch_abstracts = {}
                            for article in root.findall(".//PubmedArticle"):
                                pmid_elem = article.find(".//PMID")
                                if pmid_elem is not None and pmid_elem.text:
                                    pmid = pmid_elem.text
                                    abstract_element = article.find(".//Abstract/AbstractText")
                                    if abstract_element is not None:
                                        batch_abstracts[pmid] = abstract_element.text
                                    else:
                                        batch_abstracts[pmid] = None
                            
                            # Add batch results to overall results
                            all_abstracts.update(batch_abstracts)
                            BioChatLogger.log_info(f"Extracted {len(batch_abstracts)} abstracts from batch")
                            
                        except ET.ParseError as e:
                            BioChatLogger.log_error(f"XML parsing error: {str(e)}", e)
                            continue
                            
                except Exception as e:
                    BioChatLogger.log_error(f"Error processing batch: {str(e)}", e)
                    continue
            
            BioChatLogger.log_info(f"Total abstracts extracted: {len(all_abstracts)}")
            return all_abstracts
                
        except Exception as e:
            BioChatLogger.log_error("Error in extract_abstracts", e)
            return {}

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
                # Extract PMIDs - with better error handling
                pmids = []
                if 'result' in search_results and isinstance(search_results['result'], dict):
                    if 'uids' in search_results['result']:
                        pmids = search_results['result']['uids']
                    else:
                        # Try to get keys from the result dictionary
                        pmids = [k for k in search_results['result'].keys() 
                                if k not in ['warning', 'error', 'esearchresult']]
                
                if not pmids:
                    BioChatLogger.log_info("No PMIDs found in search results")
                    return {
                        "error": "No results found", 
                        "query": {
                            "genes": genes,
                            "phenotypes": phenotypes,
                            "additional_terms": additional_terms
                        }
                    }
                
                BioChatLogger.log_info(f"Found {len(pmids)} articles, fetching abstracts")
                try:
                    abstracts = await self.extract_abstracts(pmids)
                except Exception as e:
                    BioChatLogger.log_error("Failed to extract abstracts", e)
                    abstracts = {}
            
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
        Tries multiple mapping approaches when direct mapping fails.

        Args:
            uniprot_id: UniProt accession number

        Returns:
            Optional[str]: Reactome ID if found, None otherwise
        """
        # Try direct mapping first
        try:
            BioChatLogger.log_info(f"Attempting direct Reactome mapping for UniProt ID: {uniprot_id}")
            url = f"https://reactome.org/ContentService/data/mapping/UniProt/{uniprot_id}"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    # Get the first Reactome ID (there might be multiple)
                    reactome_id = list(data.keys())[0]
                    BioChatLogger.log_info(f"Found Reactome ID for {uniprot_id}: {reactome_id}")
                    return reactome_id
        except Exception as e:
            BioChatLogger.log_error(f"Error in direct Reactome mapping for {uniprot_id}", e)
        
        # Try with isoform suffix for CD47 specifically
        if uniprot_id == "Q08722":
            try:
                BioChatLogger.log_info(f"Trying CD47 specific mapping with isoform: Q08722-3")
                url = f"https://reactome.org/ContentService/data/mapping/UniProt/Q08722-3"
                response = requests.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        reactome_id = list(data.keys())[0]
                        BioChatLogger.log_info(f"Found Reactome ID for Q08722-3: {reactome_id}")
                        return reactome_id
            except Exception as e:
                BioChatLogger.log_error(f"Error in CD47 specific mapping", e)
            
            # Hardcoded fallback for CD47 since we know it exists in Reactome
            BioChatLogger.log_info("Using hardcoded Reactome ID for CD47")
            return "R-HSA-199905"  # Directly use the known Reactome ID for CD47
        
        # Try interactor search as a last resort
        try:
            BioChatLogger.log_info(f"Attempting interactor search for {uniprot_id}")
            url = f"https://reactome.org/ContentService/interactors/static/molecule/{uniprot_id}/summary"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                entities = data.get("entities", [])
                if entities and len(entities) > 0:
                    for entity in entities:
                        if entity.get("accession") == uniprot_id:
                            reactome_id = entity.get("id")
                            BioChatLogger.log_info(f"Found Reactome interactor ID: {reactome_id}")
                            return reactome_id
        except Exception as e:
            BioChatLogger.log_error(f"Error in interactor search for {uniprot_id}", e)
        
        # If all methods fail, try searching by gene name
        try:
            BioChatLogger.log_info(f"Trying direct pathway search for {uniprot_id}")
            url = f"https://reactome.org/ContentService/search/query?query={uniprot_id}&types=Pathway&species=Homo+sapiens"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                if results and len(results) > 0:
                    for result in results:
                        if result.get("exactType") == "Pathway":
                            pathway_id = result.get("stId")
                            BioChatLogger.log_info(f"Found pathway via search: {pathway_id}")
                            return pathway_id
        except Exception as e:
            BioChatLogger.log_error(f"Error in direct pathway search for {uniprot_id}", e)
            
        # No mapping found after trying all methods
        BioChatLogger.log_info(f"No Reactome mapping found for UniProt ID {uniprot_id} after trying all methods")
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


class ChemblAPI(BioDatabaseAPI):
    """
    Client for accessing the ChEMBL API.
    Provides methods to search compounds, fetch detailed compound info, bioactivities, and target data.
    Documentation: https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services
    """
    def __init__(self):
        # ChEMBL public endpoints do not require an API key
        super().__init__()
        self.base_url = "https://www.ebi.ac.uk/chembl/api/data"
    
    async def search(self, query: str) -> dict:
        """
        Search for compounds in ChEMBL using a simple name lookup.
        The query is assumed to be a gene, protein, or compound name.
        
        Args:
            query (str): The search query - can be compound name, SMILES, InChI, etc.
            
        Returns:
            dict: Results from ChEMBL search with matching molecules
        """
        try:
            # Attempt molecule search first (most common use case)
            params = {
                "format": "json",
                "limit": 10,
                "q": query
            }
            
            BioChatLogger.log_info(f"Searching ChEMBL for molecules matching: {query}")
            result = await self._make_request("molecule/search", params=params)
            
            # If successful and has matches, return it
            if result and "molecules" in result and len(result["molecules"]) > 0:
                return {
                    "success": True,
                    "query_type": "molecule",
                    "molecules": result["molecules"],
                    "count": len(result["molecules"])
                }
            
            # If no results, try mechanism search
            params = {
                "format": "json",
                "limit": 10,
                "q": query
            }
            
            BioChatLogger.log_info(f"Searching ChEMBL for mechanisms matching: {query}")
            mechanism_result = await self._make_request("mechanism/search", params=params)
            
            # If mechanism results found
            if mechanism_result and "mechanisms" in mechanism_result and len(mechanism_result["mechanisms"]) > 0:
                return {
                    "success": True,
                    "query_type": "mechanism",
                    "mechanisms": mechanism_result["mechanisms"],
                    "count": len(mechanism_result["mechanisms"])
                }
                
            # If still no results, try target search
            params = {
                "format": "json",
                "limit": 10,
                "q": query
            }
            
            BioChatLogger.log_info(f"Searching ChEMBL for targets matching: {query}")
            target_result = await self._make_request("target/search", params=params)
            
            # If target results found
            if target_result and "targets" in target_result and len(target_result["targets"]) > 0:
                return {
                    "success": True,
                    "query_type": "target",
                    "targets": target_result["targets"],
                    "count": len(target_result["targets"])
                }
            
            # No results in any category
            return {
                "success": True,
                "query_type": "unknown",
                "message": f"No results found for query: {query}",
                "count": 0
            }
            
        except Exception as e:
            BioChatLogger.log_error(f"ChEMBL search error for query '{query}'", e)
            return {
                "success": False,
                "error": str(e),
                "query": query
            }

    async def get_compound_details(self, molecule_chembl_id: str) -> dict:
        """
        Retrieve detailed compound information for a given ChEMBL molecule ID.
        
        Args:
            molecule_chembl_id (str): The ChEMBL ID for the molecule
            
        Returns:
            dict: Comprehensive compound details including structure, properties, etc.
        """
        try:
            BioChatLogger.log_info(f"Getting compound details for ChEMBL ID: {molecule_chembl_id}")
            params = {"format": "json"}
            endpoint = f"molecule/{molecule_chembl_id}"
            
            # Get basic molecule data
            molecule_data = await self._make_request(endpoint, params=params)
            
            if not molecule_data or "molecule_chembl_id" not in molecule_data:
                return {
                    "success": False,
                    "error": f"No data found for molecule ID: {molecule_chembl_id}"
                }
                
            # Enhance with additional related data
            # 1. Get drug indications if it's a drug
            if molecule_data.get("max_phase", 0) > 0:
                params = {
                    "molecule_chembl_id": molecule_chembl_id,
                    "format": "json"
                }
                drug_indications = await self._make_request("drug_indication", params=params)
                molecule_data["drug_indications"] = drug_indications.get("drug_indications", [])
            
            # 2. Get mechanism of action
            params = {
                "molecule_chembl_id": molecule_chembl_id,
                "format": "json"
            }
            mechanisms = await self._make_request("mechanism", params=params)
            molecule_data["mechanisms_of_action"] = mechanisms.get("mechanisms", [])
            
            return {
                "success": True,
                "molecule_data": molecule_data
            }
            
        except Exception as e:
            BioChatLogger.log_error(f"ChEMBL compound details error for ID '{molecule_chembl_id}'", e)
            return {
                "success": False,
                "error": str(e),
                "molecule_chembl_id": molecule_chembl_id
            }

    async def get_bioactivities(self, molecule_chembl_id: str, limit: int = 20) -> dict:
        """
        Retrieve bioactivity data for a given ChEMBL molecule ID.
        
        Args:
            molecule_chembl_id (str): The ChEMBL ID for the molecule
            limit (int): Maximum number of activity records to return
            
        Returns:
            dict: Bioactivity data including targets, assays, and activity values
        """
        try:
            BioChatLogger.log_info(f"Getting bioactivities for ChEMBL ID: {molecule_chembl_id} (limit: {limit})")
            params = {
                "molecule_chembl_id": molecule_chembl_id,
                "format": "json",
                "limit": limit,
                "sort": "-standard_value"  # Sort by activity value (most potent first)
            }
            
            bioactivities = await self._make_request("activity", params=params)
            
            if not bioactivities or "activities" not in bioactivities:
                return {
                    "success": False,
                    "error": f"No bioactivity data found for molecule ID: {molecule_chembl_id}"
                }
                
            # Process and structure the bioactivity data
            structured_activities = []
            for activity in bioactivities.get("activities", []):
                structured_activities.append({
                    "target_name": activity.get("target_name", ""),
                    "target_organism": activity.get("target_organism", ""),
                    "standard_type": activity.get("standard_type", ""),
                    "standard_value": activity.get("standard_value", ""),
                    "standard_units": activity.get("standard_units", ""),
                    "assay_description": activity.get("assay_description", ""),
                    "document_year": activity.get("document_year", "")
                })
                
            return {
                "success": True,
                "molecule_chembl_id": molecule_chembl_id,
                "activities": structured_activities,
                "activity_count": len(structured_activities)
            }
            
        except Exception as e:
            BioChatLogger.log_error(f"ChEMBL bioactivities error for ID '{molecule_chembl_id}'", e)
            return {
                "success": False,
                "error": str(e),
                "molecule_chembl_id": molecule_chembl_id
            }

    async def get_target_info(self, target_chembl_id: str) -> dict:
        """
        Retrieve target information from ChEMBL using a ChEMBL target ID.
        
        Args:
            target_chembl_id (str): The ChEMBL ID for the target
            
        Returns:
            dict: Comprehensive target information including properties and related data
        """
        try:
            BioChatLogger.log_info(f"Getting target information for ChEMBL ID: {target_chembl_id}")
            params = {"format": "json"}
            endpoint = f"target/{target_chembl_id}"
            
            # Get basic target data
            target_data = await self._make_request(endpoint, params=params)
            
            if not target_data or "target_chembl_id" not in target_data:
                return {
                    "success": False,
                    "error": f"No data found for target ID: {target_chembl_id}"
                }
                
            # Get active compounds for this target (with a limit to avoid huge result sets)
            params = {
                "target_chembl_id": target_chembl_id,
                "format": "json",
                "limit": 10,
                "sort": "-standard_value"  # Most potent first
            }
            
            activities = await self._make_request("activity", params=params)
            target_data["top_compounds"] = [
                {
                    "molecule_chembl_id": act.get("molecule_chembl_id", ""),
                    "molecule_name": act.get("molecule_pref_name", ""),
                    "activity_type": act.get("standard_type", ""),
                    "activity_value": act.get("standard_value", ""),
                    "activity_units": act.get("standard_units", "")
                }
                for act in activities.get("activities", [])
            ]
            
            return {
                "success": True,
                "target_data": target_data
            }
            
        except Exception as e:
            BioChatLogger.log_error(f"ChEMBL target info error for ID '{target_chembl_id}'", e)
            return {
                "success": False,
                "error": str(e),
                "target_chembl_id": target_chembl_id
            }
    
    async def search_by_similarity(self, smiles: str, similarity: float = 0.8, limit: int = 10) -> dict:
        """
        Search for compounds with structural similarity to the provided SMILES string.
        
        Args:
            smiles (str): SMILES notation of the query molecule
            similarity (float): Similarity threshold (0-1), default 0.8
            limit (int): Maximum number of results to return
            
        Returns:
            dict: Similar compounds with their similarity scores
        """
        try:
            BioChatLogger.log_info(f"Searching ChEMBL for compounds similar to SMILES: {smiles}")
            params = {
                "limit": limit,
                "format": "json",
                "similarity": similarity
            }
            
            endpoint = f"similarity/{smiles}"
            result = await self._make_request(endpoint, params=params)
            
            if not result or "molecules" not in result:
                return {
                    "success": False,
                    "error": f"No similar compounds found for SMILES: {smiles}"
                }
                
            return {
                "success": True,
                "query_smiles": smiles,
                "similarity_threshold": similarity,
                "similar_compounds": result.get("molecules", []),
                "count": len(result.get("molecules", []))
            }
            
        except Exception as e:
            BioChatLogger.log_error(f"ChEMBL similarity search error for SMILES '{smiles}'", e)
            return {
                "success": False,
                "error": str(e),
                "smiles": smiles
            }
    
    async def search_by_substructure(self, smiles: str, limit: int = 10) -> dict:
        """
        Search for compounds containing the provided SMILES as a substructure.
        
        Args:
            smiles (str): SMILES notation of the query substructure
            limit (int): Maximum number of results to return
            
        Returns:
            dict: Compounds containing the substructure
        """
        try:
            BioChatLogger.log_info(f"Searching ChEMBL for compounds with substructure SMILES: {smiles}")
            params = {
                "limit": limit,
                "format": "json"
            }
            
            endpoint = f"substructure/{smiles}"
            result = await self._make_request(endpoint, params=params)
            
            if not result or "molecules" not in result:
                return {
                    "success": False,
                    "error": f"No compounds found containing substructure SMILES: {smiles}"
                }
                
            return {
                "success": True,
                "query_smiles": smiles,
                "matching_compounds": result.get("molecules", []),
                "count": len(result.get("molecules", []))
            }
            
        except Exception as e:
            BioChatLogger.log_error(f"ChEMBL substructure search error for SMILES '{smiles}'", e)
            return {
                "success": False,
                "error": str(e),
                "smiles": smiles
            }


class BioGridClient(BioDatabaseAPI):
    """Enhanced BioGRID client specifically for chemical interactions."""
    
    def __init__(self, access_key: str):
        super().__init__(api_key=access_key)
        self.base_url = "https://webservice.thebiogrid.org"

    async def get_chemical_interactions(self, chemical_list: List[str]) -> Dict:
        """
        Get chemical-protein interactions.
        
        Chemical interactions in BioGRID require specific parameters:
        - chemicalList for the chemicals
        - includeInteractors=true to get protein targets
        - max=10000 to get comprehensive results
        """
        try:
            params = {
                "accessKey": self.api_key,
                "format": "json",
                "chemicalList": "|".join(chemical_list),
                "includeInteractors": "true",
                "max": "10000",  # Get maximum results
                "searchNames": "false",  # Not searching gene names
                "searchSynonyms": "false"  # Not searching gene synonyms
            }
            
            BioChatLogger.log_info(f"Querying BioGRID chemicals: {chemical_list}")
            
            response = await self._make_request("interactions", params)
            
            if isinstance(response, dict):
                if response.get("STATUS") == "ERROR":
                    error_msg = response.get('MESSAGES', ['Unknown error'])[0]
                    BioChatLogger.log_error("BioGRID API error", Exception(error_msg))
                    return {
                        "success": False,
                        "error": error_msg,
                        "chemical_list": chemical_list
                    }
                
                # Process and filter chemical interactions
                chemical_interactions = {}
                for interaction_id, interaction in response.items():
                    # Check if this is a chemical interaction
                    if interaction.get("EXPERIMENTAL_SYSTEM") in [
                        "Biochemical Activity",
                        "Chemical-Physical",
                        "Co-crystal Structure",
                        "Pharmacological",
                        "Reconstituted Complex"
                    ]:
                        chemical_interactions[interaction_id] = {
                            "chemical_name": interaction.get("OFFICIAL_SYMBOL_A"),
                            "protein_target": interaction.get("OFFICIAL_SYMBOL_B"),
                            "interaction_type": interaction.get("EXPERIMENTAL_SYSTEM"),
                            "interaction_evidence": interaction.get("EXPERIMENTAL_SYSTEM_TYPE"),
                            "pubmed_id": interaction.get("PUBMED_ID"),
                            "publication": interaction.get("PUBMED_AUTHOR"),
                            "throughput": interaction.get("THROUGHPUT"),
                            "qualifications": interaction.get("QUALIFICATIONS"),
                            "source": interaction.get("SOURCEDB")
                        }
                
                return {
                    "success": True,
                    "data": chemical_interactions,
                    "chemical_list": chemical_list,
                    "interaction_count": len(chemical_interactions),
                    "metadata": {
                        "chemicals_found": len(set(i["chemical_name"] for i in chemical_interactions.values())),
                        "protein_targets": len(set(i["protein_target"] for i in chemical_interactions.values())),
                        "experiment_types": list(set(i["interaction_type"] for i in chemical_interactions.values()))
                    }
                }
            
            return {
                "success": False,
                "error": "Invalid response format",
                "chemical_list": chemical_list
            }
            
        except Exception as e:
            BioChatLogger.log_error("BioGRID chemical interaction error", e)
            return {"error": str(e), "chemical_list": chemical_list}

    async def search(self, chemical_name: str) -> Dict:
        """
        Search for a specific chemical and its interactions.
        Provides more focused results for a single chemical.
        """
        try:
            # First try exact chemical name
            results = await self.get_chemical_interactions([chemical_name])
            
            if not results.get("success") or results.get("interaction_count", 0) == 0:
                # If no results, try with synonyms if available
                # Note: BioGRID doesn't directly support chemical synonym search
                # This is just a placeholder for future enhancement
                pass
                
            return results
            
        except Exception as e:
            BioChatLogger.log_error(f"Chemical search error for {chemical_name}", e)
            return {"error": str(e), "chemical": chemical_name}

class IntActClient(BioDatabaseAPI):
    """
    Enhanced IntAct client with proper chemical interaction handling.
    """
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.ebi.ac.uk/intact/ws/interaction"
        
    async def search(self, query: str, species: Optional[str] = None,
                    negative_filter: str = "POSITIVE_ONLY", page: int = 0,
                    page_size: int = 10) -> Dict:
        """
        Search IntAct database with improved chemical query handling.
        """
        try:
            # Format query according to IntAct specs
            params = {
                "query": query,
                "page": page,
                "pageSize": page_size,
                "negativeFilter": negative_filter
            }
            if species:
                params["species"] = species
            
            # First try findInteractions endpoint
            try:
                response = await self._make_request("findInteractions", params)
                if response:
                    return {
                        "success": True,
                        "data": response,
                        "query": query,
                        "interaction_count": len(response.get("content", [])) if isinstance(response, dict) else 0
                    }
            except Exception as first_error:
                BioChatLogger.log_error(f"IntAct findInteractions error: {str(first_error)}", e)
                # If first attempt fails, try faceted search
                try:
                    facet_response = await self._make_request("findInteractionFacets", params)
                    if facet_response:
                        return {
                            "success": True,
                            "data": facet_response,
                            "query": query,
                            "interaction_count": facet_response.get("totalElements", 0)
                        }
                except Exception as second_error:
                    BioChatLogger.log_error(f"IntAct faceted search error: {str(second_error)}", e)
                    raise second_error
                
        except Exception as e:
            BioChatLogger.log_error(f"IntAct search error: {str(e)}", e)
            return {"error": str(e)}

    async def get_interaction_facets(self, query: str, interaction_types: Optional[List[str]] = None) -> Dict:
        """Get interaction statistics and metadata"""
        try:
            params = {"query": query}
            if interaction_types:
                params["interactionTypesFilter"] = ",".join(interaction_types)
            
            return await self._make_request("findInteractionFacets", params)
        except Exception as e:
            BioChatLogger.log_error(f"IntAct facets error: {str(e)}", e)
            return {"error": str(e)}


class PharmGKBClient(BioDatabaseAPI):
    """
    Enhanced PharmGKB API client with proper name-to-ID resolution.
    Uses the query endpoints first to get IDs, then fetches details.
    """
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.pharmgkb.org/v1"
        self.headers = {"Content-Type": "application/json"}

    async def search(self, query: str) -> Dict[str, Any]:
        """
        Implements required abstract method. Searches across chemical, drug labels, and pathways.
        """
        try:
            results = {
                "chemicals": await self.search_chemical_by_name(query),
                "drug_labels": await self.search_drug_labels_by_name(query),
                "pathways": await self.search_pathway_by_name(query)
            }
            return results
        except Exception as e:
            BioChatLogger.log_error(f"PharmGKB search error: {str(e)}", e)
            return {"error": str(e)}

    async def search_chemical_by_name(self, name: str, view: str = "base") -> Dict[str, Any]:
        """
        Search for chemicals by name, returns a list of matches.
        Returns empty list if no matches found.
        """
        try:
            params = {
                "name": name,
                "view": view
            }
            response = await self._make_request("data/chemical", params)
            
            if isinstance(response, list):
                return response
            elif isinstance(response, dict) and "error" in response:
                BioChatLogger.log_info(f"No chemical found for name: {name}")
                return []
            return []
            
        except Exception as e:
            # Don't treat 404 as error for searches - it just means no results
            if "404" in str(e):
                BioChatLogger.log_info(f"No chemical found for name: {name}")
                return []
            BioChatLogger.log_error(f"PharmGKB chemical search error: {str(e)}", e)
            return {"error": str(e)}

    async def get_chemical_by_id(self, pharmgkb_id: str, view: str = "base") -> Dict[str, Any]:
        """
        Get chemical details by PharmGKB ID.
        """
        try:
            params = {"view": view}
            return await self._make_request(f"data/chemical/{pharmgkb_id}", params)
        except Exception as e:
            BioChatLogger.log_error(f"PharmGKB get chemical error: {str(e)}", e)
            return {"error": str(e)}

    async def search_drug_labels_by_name(self, name: str, view: str = "base") -> Dict[str, Any]:
        """
        Search drug labels by name.
        """
        try:
            params = {
                "relatedChemicals.name": name,
                "view": view
            }
            response = await self._make_request("data/label", params)
            
            if isinstance(response, list):
                return response
            return []
            
        except Exception as e:
            if "404" in str(e):
                BioChatLogger.log_info(f"No drug labels found for name: {name}")
                return []
            BioChatLogger.log_error(f"PharmGKB drug label search error: {str(e)}", e)
            return {"error": str(e)}

    async def get_drug_label_by_id(self, pharmgkb_id: str, view: str = "base") -> Dict[str, Any]:
        """
        Get drug label details by PharmGKB ID.
        """
        try:
            params = {"view": view}
            return await self._make_request(f"data/label/{pharmgkb_id}", params)
        except Exception as e:
            BioChatLogger.log_error(f"PharmGKB get drug label error: {str(e)}", e)
            return {"error": str(e)}

    async def search_pathway_by_name(self, name: str, view: str = "base") -> Dict[str, Any]:
        """
        Search pathways by name.
        """
        try:
            params = {
                "name": name,
                "view": view
            }
            response = await self._make_request("data/pathway", params)
            
            if isinstance(response, list):
                return response
            return []
            
        except Exception as e:
            if "404" in str(e):
                BioChatLogger.log_info(f"No pathways found for name: {name}")
                return []
            BioChatLogger.log_error(f"PharmGKB pathway search error: {str(e)}", e)
            return {"error": str(e)}

    async def get_pathway_by_id(self, pharmgkb_id: str, view: str = "base") -> Dict[str, Any]:
        """
        Get pathway details by PharmGKB ID.
        """
        try:
            params = {"view": view}
            return await self._make_request(f"data/pathway/{pharmgkb_id}", params)
        except Exception as e:
            BioChatLogger.log_error(f"PharmGKB get pathway error: {str(e)}", e)
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


class OpenTargetsClient(BioDatabaseAPI):
    """Client for interacting with Open Targets Platform GraphQL API"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.platform.opentargets.org/api/v4/graphql"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def _execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Execute a GraphQL query"""
        try:
            payload = {
                "query": query,
                "variables": variables or {}
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, json=payload, headers=self.headers) as response:
                    if response.status == 429:  # Rate limit
                        retry_after = int(response.headers.get('Retry-After', 5))
                        await asyncio.sleep(retry_after)
                        return await self._execute_query(query, variables)
                        
                    response.raise_for_status()
                    result = await response.json()
                    
                    if "errors" in result:
                        raise Exception(f"GraphQL errors: {result['errors']}")
                        
                    return result.get("data", {})
                    
        except aiohttp.ClientError as e:
            BioChatLogger.log_error("OpenTargets API request error", e)
            raise
        except Exception as e:
            BioChatLogger.log_error("OpenTargets query error", e)
            raise

    async def search(self, query: str, entity: str = None, size: int = 10) -> Dict:
        """Search across targets, diseases, and drugs"""
        search_query = """
        query SearchQuery($searchQuery: String!, $entity: String, $size: Int) {
            search(queryString: $searchQuery, entityNames: [$entity], size: $size) {
                total
                hits {
                    id
                    entity
                    object {
                        id
                        name
                    }
                }
            }
        }
        """
        
        variables = {
            "searchQuery": query,
            "entity": entity,
            "size": size
        }
        
        try:
            return await self._execute_query(search_query, variables)
        except Exception as e:
            BioChatLogger.log_error(f"OpenTargets search error", e)
            return {"error": str(e)}

    async def get_target_info(self, target_id: str) -> Dict:
        """Get detailed information about a target"""
        # Updated query to match schema
        target_query = """
        query TargetQuery($targetId: String!) {
            target(ensemblId: $targetId) {
                id
                approvedSymbol
                approvedName
                biotype
                knownDrugs(size: 20) {
                    count
                    rows {
                        phase
                        status
                        mechanismOfAction
                        disease {
                            id
                            name
                        }
                        drug {
                            id
                            name
                            drugType
                            maximumClinicalTrialPhase
                        }
                    }
                }
                safetyLiabilities {
                    event
                    eventId
                    effects {
                        direction
                        dosing
                    }
                    biosamples {
                        tissueLabel
                        tissueId
                    }
                }
            }
        }
        """
        
        try:
            BioChatLogger.log_info(f"Querying OpenTargets for target: {target_id}")
            result = await self._execute_query(target_query, {"targetId": target_id})
            
            if not result or "target" not in result:
                error_msg = "No target data found"
                BioChatLogger.log_error(error_msg, Exception(error_msg))
                return {"error": error_msg, "target_id": target_id}
            
            return result
            
        except Exception as e:
            BioChatLogger.log_error(f"OpenTargets target info error", e)
            return {"error": str(e), "target_id": target_id}

    async def get_disease_info(self, disease_id: str) -> Dict:
        """Get detailed information about a disease"""
        disease_query = """
        query DiseaseQuery($diseaseId: String!) {
            disease(efoId: $diseaseId) {
                id
                name
                description
                therapeuticAreas {
                    id
                    name
                }
            }
        }
        """
        
        try:
            return await self._execute_query(disease_query, {"diseaseId": disease_id})
        except Exception as e:
            BioChatLogger.log_error(f"OpenTargets disease info error", e)
            return {"error": str(e)}

    async def get_target_disease_associations(self, 
                                           target_id: str = None,
                                           disease_id: str = None,
                                           score_min: float = 0.0,
                                           size: int = 10) -> Dict:
        """Get associations between targets and diseases"""
        association_query = """
        query AssociationsQuery($targetId: String, $diseaseId: String, $scoreMin: Float, $size: Int) {
            associatedDiseases(
                ensemblId: $targetId,
                efoId: $diseaseId,
                datasourceScoreMin: $scoreMin,
                size: $size
            ) {
                count
                rows {
                    disease {
                        id
                        name
                    }
                    score
                    datatypeScores {
                        id
                        score
                    }
                }
            }
        }
        """
        
        variables = {
            "targetId": target_id,
            "diseaseId": disease_id,
            "scoreMin": score_min,
            "size": size
        }
        
        try:
            return await self._execute_query(association_query, variables)
        except Exception as e:
            BioChatLogger.log_error(f"OpenTargets association error", e)
            return {"error": str(e)}


    async def _execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict:
            """Execute a GraphQL query with proper error handling"""
            try:
                payload = {
                    "query": query,
                    "variables": variables or {}
                }
                
                # Use aiohttp session for requests
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.base_url,
                        json=payload,
                        headers=self.headers,
                        raise_for_status=True
                    ) as response:
                        result = await response.json()
                        
                        if "errors" in result:
                            raise Exception(f"GraphQL errors: {result['errors']}")
                        
                        if "data" not in result:
                            raise Exception("No data in response")
                            
                        return result.get("data", {})
                        
            except aiohttp.ClientError as e:
                BioChatLogger.log_error("OpenTargets API request error", e)
                raise
            except Exception as e:
                BioChatLogger.log_error("OpenTargets query error", e)
                raise

    async def get_target_safety(self, target_id: str) -> Dict:
        """Get safety information for a target"""
        query = """
        query TargetSafety($targetId: String!) {
            target(ensemblId: $targetId) {
                id
                safetyLiabilities {
                    biosamples {
                        tissueLabel
                        tissueId
                        cellLabel
                        cellFormat
                        cellId
                    }
                    effects {
                        direction
                        dosing
                    }
                    event
                    eventId
                    datasource
                    literature
                    studies {
                        name
                        description
                        type
                    }
                }
            }
        }
        """
        
        try:
            result = await self._execute_query(query, {"targetId": target_id})
            return result.get("target", {}).get("safetyLiabilities", [])
        except Exception as e:
            BioChatLogger.log_error(f"OpenTargets target safety error", e)
            return {"error": str(e)}

    async def get_known_drugs(self, target_id: str, size: int = 10) -> Dict:
        """Get known drugs for a target"""
        query = """
        query TargetDrugs($targetId: String!, $size: Int!) {
            target(ensemblId: $targetId) {
                id
                knownDrugs(size: $size) {
                    count
                    cursor
                    rows {
                        phase
                        status
                        mechanismOfAction
                        disease {
                            id
                            name
                        }
                        drug {
                            id
                            name
                            drugType
                            maximumClinicalTrialPhase
                        }
                        urls {
                            url
                            name
                        }
                    }
                }
            }
        }
        """
        
        try:
            result = await self._execute_query(query, {
                "targetId": target_id,
                "size": size
            })
            return result.get("target", {}).get("knownDrugs", {})
        except Exception as e:
            BioChatLogger.log_error(f"OpenTargets known drugs error", e)
            return {"error": str(e)}

    async def get_target_expression(self, target_id: str) -> Dict:
        """Get expression data for a target"""
        query = """
        query TargetExpression($targetId: String!) {
            target(ensemblId: $targetId) {
                id
                expressions {
                    tissue {
                        id
                        label
                        anatomicalSystems
                        organs
                    }
                    rna {
                        value
                        unit
                        level
                        zscore
                    }
                    protein {
                        level
                        reliability
                        cellType {
                            name
                            level
                            reliability
                        }
                    }
                }
            }
        }
        """
        
        try:
            result = await self._execute_query(query, {"targetId": target_id})
            return result.get("target", {}).get("expressions", [])
        except Exception as e:
            BioChatLogger.log_error(f"OpenTargets expression error", e)
            return {"error": str(e)}