"""
GWASCatalog API client.
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
