"""
IntActClient API client.
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


