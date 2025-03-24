"""
PharmGKBClient API client.
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


