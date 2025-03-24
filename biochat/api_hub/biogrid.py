"""
BioGridClient API client.
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

