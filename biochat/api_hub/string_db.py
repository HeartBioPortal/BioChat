"""
StringDBClient API client.
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


