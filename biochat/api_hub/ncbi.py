"""
NCBIEutils API client.
"""

from typing import Dict, List, Optional, Union, Any, Tuple, Set
import json
import logging
import aiohttp
import asyncio
import requests
from datetime import datetime
from .base import BioDatabaseAPI
from ..utils.biochat_api_logging import BioChatLogger


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

