"""
EnsemblAPI API client.
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

