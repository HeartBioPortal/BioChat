"""
ReactomeClient API client.
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
        """
        Get pathways involving a given gene using multiple strategies.
        First tries direct gene name mapping, then UniProt ID mapping, then search.
        
        Args:
            gene_name: Gene symbol (e.g., "CD47", "TP53")
            
        Returns:
            Dict containing pathways and count
        """
        try:
            BioChatLogger.log_info(f"Getting pathways for gene {gene_name}")
            
            # Strategy 1: Direct gene name approach - this is most reliable!
            try:
                BioChatLogger.log_info(f"Getting pathways by direct gene name: {gene_name}")
                # Try the direct gene-to-pathway endpoint
                endpoint = f"data/mapping/UniProt/{gene_name}/pathways"
                params = {"species": "9606"}  # Human species ID
                pathways_response = await self._make_request(endpoint, params=params)
                
                # If we got results directly, format and return them
                if pathways_response and isinstance(pathways_response, list) and len(pathways_response) > 0:
                    BioChatLogger.log_info(f"Found {len(pathways_response)} pathways via direct gene name mapping")
                    
                    # Format the response consistently
                    formatted_pathways = []
                    for pathway in pathways_response:
                        formatted_pathways.append({
                            "pathway_id": pathway.get("stId", ""),
                            "pathway_name": pathway.get("displayName", ""),
                            "species": pathway.get("speciesName", "Homo sapiens"),
                            "source": "Reactome Direct Gene Mapping",
                            "is_disease": pathway.get("isInDisease", False),
                            "has_diagram": pathway.get("hasDiagram", False)
                        })
                    
                    return {"pathways": formatted_pathways, "count": len(formatted_pathways), "method": "direct_gene_mapping"}
            except Exception as e:
                BioChatLogger.log_error(f"Error in direct gene mapping for {gene_name}", e)
                # Try alternative approach with direct HTTP request
                try:
                    BioChatLogger.log_info(f"Trying direct HTTP request for gene {gene_name}")
                    url = f"https://reactome.org/ContentService/data/mapping/UniProt/{gene_name}/pathways?species=9606"
                    session = requests.Session()
                    response = session.get(url)
                    response.raise_for_status()
                    pathways_data = response.json()
                    
                    if pathways_data and isinstance(pathways_data, list) and len(pathways_data) > 0:
                        BioChatLogger.log_info(f"Found {len(pathways_data)} pathways via direct HTTP request")
                        
                        # Format the response consistently
                        formatted_pathways = []
                        for pathway in pathways_data:
                            formatted_pathways.append({
                                "pathway_id": pathway.get("stId", ""),
                                "pathway_name": pathway.get("displayName", ""),
                                "species": pathway.get("speciesName", "Homo sapiens"),
                                "source": "Reactome Direct HTTP Request",
                                "is_disease": pathway.get("isInDisease", False),
                                "has_diagram": pathway.get("hasDiagram", False)
                            })
                        
                        return {"pathways": formatted_pathways, "count": len(formatted_pathways), "method": "direct_http_request"}
                except Exception as http_error:
                    BioChatLogger.log_error(f"Error in direct HTTP request for {gene_name}", http_error)
            
            # Strategy 2: Via UniProt mapping
            try:
                BioChatLogger.log_info(f"Getting UniProt ID for gene {gene_name}")
                uniprot_id = self.get_primary_uniprot_id(gene_name.strip())
                if uniprot_id:
                    BioChatLogger.log_info(f"Found UniProt ID: {uniprot_id} for {gene_name}")
                    
                    # Try the direct mapping endpoint with UniProt ID
                    endpoint = f"data/mapping/UniProt/{uniprot_id}/pathways"
                    params = {"species": "9606"}  # Human species ID
                    pathways_response = await self._make_request(endpoint, params=params)
                    
                    if pathways_response and isinstance(pathways_response, list) and len(pathways_response) > 0:
                        BioChatLogger.log_info(f"Found {len(pathways_response)} pathways via UniProt ID mapping")
                        
                        # Format the response consistently
                        formatted_pathways = []
                        for pathway in pathways_response:
                            formatted_pathways.append({
                                "pathway_id": pathway.get("stId", ""),
                                "pathway_name": pathway.get("displayName", ""),
                                "species": pathway.get("speciesName", "Homo sapiens"),
                                "source": "Reactome UniProt ID Mapping",
                                "is_disease": pathway.get("isInDisease", False),
                                "has_diagram": pathway.get("hasDiagram", False)
                            })
                        
                        return {"pathways": formatted_pathways, "count": len(formatted_pathways), "method": "uniprot_id_mapping"}
            except Exception as e:
                BioChatLogger.log_error(f"Error in UniProt ID mapping for {gene_name}", e)
            
            # Strategy 3: Direct Reactome search by gene name
            try:
                BioChatLogger.log_info(f"Directly searching Reactome for gene {gene_name}")
                pathways = await self.search_pathways_by_gene(gene_name)
                if pathways and len(pathways) > 0:
                    BioChatLogger.log_info(f"Found {len(pathways)} pathways via direct search")
                    return {"pathways": pathways, "count": len(pathways), "method": "direct_search"}
            except Exception as e:
                BioChatLogger.log_error(f"Error in direct Reactome search for {gene_name}", e)
            
            # Strategy 4: Use standard pathways for common genes
            if gene_name.upper() in self.get_common_pathways():
                BioChatLogger.log_info(f"Using standard pathways for {gene_name}")
                pathways = self.get_common_pathways()[gene_name.upper()]
                return {"pathways": pathways, "count": len(pathways), "method": "standard_mapping"}
            
            # If all strategies fail
            BioChatLogger.log_info(f"No pathways found for gene {gene_name} using any strategy")
            return {"error": f"No pathways found for gene {gene_name}", "count": 0}
            
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
            # Get basic pathway information instead of containedEvents which often fails
            endpoint = f"data/pathway/{pathway_id}"
            details = await self._make_request(endpoint)
            
            if not details or "stId" not in details:
                BioChatLogger.log_error(f"No pathway details found for {pathway_id}")
                return {}
                
            # Format the response more consistently
            formatted_details = {
                "pathway_id": details.get("stId"),
                "pathway_name": details.get("displayName"),
                "species": details.get("speciesName", "Homo sapiens"),
                "compartment": details.get("compartment", {}).get("name", "Unknown"),
                "is_disease": details.get("isInDisease", False),
                "has_diagram": details.get("hasDiagram", False),
                "source": "Reactome Pathway API"
            }
            
            return formatted_details
            
        except Exception as e:
            BioChatLogger.log_error(f"Error getting pathway details for {pathway_id}", e)
            return {}

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

     
    async def get_interactors_for_gene(self, uniprot_id: str) -> List[Dict]:
        """
        Fetch interactors for a given UniProt ID from Reactome.
        This is more reliable than direct pathway mapping for some proteins.
        
        Args:
            uniprot_id: UniProt accession number
            
        Returns:
            List of pathway dictionaries
        """
        BioChatLogger.log_info(f"Fetching interactors for UniProt ID: {uniprot_id}")
        try:
            # Using the correct interactors endpoint from the Reactome API
            endpoint = f"interactors/static/molecule/{uniprot_id}/pathways"
            response = await self._make_request(endpoint)
            
            # If no interactors found, return empty list
            if not response or "pathways" not in response:
                BioChatLogger.log_info(f"No interactors found for {uniprot_id}")
                return []
                
            # Format the response in a consistent way
            pathways = []
            for pathway in response.get("pathways", []):
                pathways.append({
                    "pathway_id": pathway.get("stId", ""),
                    "pathway_name": pathway.get("name", ""),
                    "species": pathway.get("species", ""),
                    "source": "Reactome Interactors API"
                })
                
            return pathways
            
        except Exception as e:
            BioChatLogger.log_error(f"Error fetching interactors for {uniprot_id}", e)
            return []
    
    async def search_pathways_by_gene(self, gene_name: str) -> List[Dict]:
        """
        Search for pathways directly by gene name using Reactome search API.
        
        Args:
            gene_name: Gene symbol to search for
            
        Returns:
            List of pathway dictionaries
        """
        BioChatLogger.log_info(f"Searching pathways by gene name: {gene_name}")
        try:
            # Using the Reactome search endpoint
            params = {
                "query": gene_name,
                "types": "Pathway",
                "species": "Homo sapiens",
                "clustered": "true"
            }
            endpoint = "search/query"
            
            try:
                response = await self._make_request(endpoint, params=params)
                BioChatLogger.log_info(f"Reactome search response: {str(response)[:200]}...")
            except Exception as search_error:
                BioChatLogger.log_error(f"Error with Reactome search API: {str(search_error)}")
                
                # Try alternate search endpoint as fallback
                BioChatLogger.log_info(f"Trying alternate search endpoint for {gene_name}")
                # Use a more direct search approach with the main Reactome website
                url = f"https://reactome.org/ContentService/search/query?query={gene_name}&species=Homo%20sapiens&types=Pathway&cluster=true"
                try:
                    session = requests.Session()
                    alt_response = session.get(url)
                    alt_response.raise_for_status()
                    response = alt_response.json()
                    BioChatLogger.log_info(f"Alternate search succeeded, found {len(response.get('results', []))} results")
                except Exception as alt_error:
                    BioChatLogger.log_error(f"Alternate search also failed: {str(alt_error)}")
                    return []
            
            # If no results, return empty list
            if not response or "results" not in response:
                BioChatLogger.log_info(f"No pathways found for gene: {gene_name}")
                return []
                
            # Format the results in a consistent way
            pathways = []
            for result in response.get("results", []):
                # Include both Pathway and Reaction types
                if result.get("exactType") in ["Pathway", "Reaction"]:
                    pathways.append({
                        "pathway_id": result.get("stId", ""),
                        "pathway_name": result.get("name", ""),
                        "species": "Homo sapiens",
                        "source": "Reactome Search API",
                        "type": result.get("exactType", "Unknown")
                    })
                    
            BioChatLogger.log_info(f"Found {len(pathways)} pathways via search for {gene_name}")
            return pathways
            
        except Exception as e:
            BioChatLogger.log_error(f"Error searching pathways for gene {gene_name}", e)
            return []
    
    def get_common_pathways(self) -> Dict[str, List[Dict]]:
        """
        Return a dictionary of common pathways for well-known genes.
        This serves as a fallback when API methods fail.
        
        Returns:
            Dict mapping gene symbols to lists of pathway dictionaries
        """
        return {
            "CD47": [
                {
                    "pathway_id": "R-HSA-168256",
                    "pathway_name": "Immune System",
                    "species": "Homo sapiens",
                    "source": "Curated Standard Pathways"
                },
                {
                    "pathway_id": "R-HSA-109582",
                    "pathway_name": "Hemostasis",
                    "species": "Homo sapiens",
                    "source": "Curated Standard Pathways"
                },
                {
                    "pathway_id": "R-HSA-162582",
                    "pathway_name": "Signal Transduction",
                    "species": "Homo sapiens",
                    "source": "Curated Standard Pathways"
                },
                {
                    "pathway_id": "R-HSA-1500931",
                    "pathway_name": "Cell-Cell communication",
                    "species": "Homo sapiens",
                    "source": "Curated Standard Pathways"
                }
            ],
            "TP53": [
                {
                    "pathway_id": "R-HSA-5633007",
                    "pathway_name": "TP53 Regulates Transcription of Cell Death Genes",
                    "species": "Homo sapiens",
                    "source": "Curated Standard Pathways"
                },
                {
                    "pathway_id": "R-HSA-2559583",
                    "pathway_name": "Cellular Senescence",
                    "species": "Homo sapiens",
                    "source": "Curated Standard Pathways"
                },
                {
                    "pathway_id": "R-HSA-5358508",
                    "pathway_name": "TP53 Regulates Metabolic Genes",
                    "species": "Homo sapiens",
                    "source": "Curated Standard Pathways"
                }
            ],
            "BRCA1": [
                {
                    "pathway_id": "R-HSA-5693567",
                    "pathway_name": "HDR through Homologous Recombination",
                    "species": "Homo sapiens",
                    "source": "Curated Standard Pathways"
                },
                {
                    "pathway_id": "R-HSA-5685942",
                    "pathway_name": "HDR through MMEJ",
                    "species": "Homo sapiens",
                    "source": "Curated Standard Pathways"
                }
            ]
            # Add more genes as needed
        }
    
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


