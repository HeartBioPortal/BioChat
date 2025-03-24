"""
BioCyc API client.
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

