"""
UniProtAPI API client.
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


