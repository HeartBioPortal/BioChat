"""
ChemblAPI API client.
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


class ChemblAPI(BioDatabaseAPI):
    """
    Client for accessing the ChEMBL API.
    Provides methods to search compounds, fetch detailed compound info, bioactivities, and target data.
    Documentation: https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services
    """
    def __init__(self):
        # ChEMBL public endpoints do not require an API key
        super().__init__()
        self.base_url = "https://www.ebi.ac.uk/chembl/api/data"
    
    async def search(self, query: str) -> dict:
        """
        Search for compounds in ChEMBL using a simple name lookup.
        The query is assumed to be a gene, protein, or compound name.
        
        Args:
            query (str): The search query - can be compound name, SMILES, InChI, etc.
            
        Returns:
            dict: Results from ChEMBL search with matching molecules
        """
        try:
            # Attempt molecule search first (most common use case)
            params = {
                "format": "json",
                "limit": 10,
                "q": query
            }
            
            BioChatLogger.log_info(f"Searching ChEMBL for molecules matching: {query}")
            result = await self._make_request("molecule/search", params=params)
            
            # If successful and has matches, return it
            if result and "molecules" in result and len(result["molecules"]) > 0:
                return {
                    "success": True,
                    "query_type": "molecule",
                    "molecules": result["molecules"],
                    "count": len(result["molecules"])
                }
            
            # If no results, try mechanism search
            params = {
                "format": "json",
                "limit": 10,
                "q": query
            }
            
            BioChatLogger.log_info(f"Searching ChEMBL for mechanisms matching: {query}")
            mechanism_result = await self._make_request("mechanism/search", params=params)
            
            # If mechanism results found
            if mechanism_result and "mechanisms" in mechanism_result and len(mechanism_result["mechanisms"]) > 0:
                return {
                    "success": True,
                    "query_type": "mechanism",
                    "mechanisms": mechanism_result["mechanisms"],
                    "count": len(mechanism_result["mechanisms"])
                }
                
            # If still no results, try target search
            params = {
                "format": "json",
                "limit": 10,
                "q": query
            }
            
            BioChatLogger.log_info(f"Searching ChEMBL for targets matching: {query}")
            target_result = await self._make_request("target/search", params=params)
            
            # If target results found
            if target_result and "targets" in target_result and len(target_result["targets"]) > 0:
                return {
                    "success": True,
                    "query_type": "target",
                    "targets": target_result["targets"],
                    "count": len(target_result["targets"])
                }
            
            # No results in any category
            return {
                "success": True,
                "query_type": "unknown",
                "message": f"No results found for query: {query}",
                "count": 0
            }
            
        except Exception as e:
            BioChatLogger.log_error(f"ChEMBL search error for query '{query}'", e)
            return {
                "success": False,
                "error": str(e),
                "query": query
            }

    async def get_compound_details(self, molecule_chembl_id: str) -> dict:
        """
        Retrieve detailed compound information for a given ChEMBL molecule ID.
        
        Args:
            molecule_chembl_id (str): The ChEMBL ID for the molecule
            
        Returns:
            dict: Comprehensive compound details including structure, properties, etc.
        """
        try:
            BioChatLogger.log_info(f"Getting compound details for ChEMBL ID: {molecule_chembl_id}")
            params = {"format": "json"}
            endpoint = f"molecule/{molecule_chembl_id}"
            
            # Get basic molecule data
            molecule_data = await self._make_request(endpoint, params=params)
            
            if not molecule_data or "molecule_chembl_id" not in molecule_data:
                return {
                    "success": False,
                    "error": f"No data found for molecule ID: {molecule_chembl_id}"
                }
                
            # Enhance with additional related data
            # 1. Get drug indications if it's a drug
            if molecule_data.get("max_phase", 0) > 0:
                params = {
                    "molecule_chembl_id": molecule_chembl_id,
                    "format": "json"
                }
                drug_indications = await self._make_request("drug_indication", params=params)
                molecule_data["drug_indications"] = drug_indications.get("drug_indications", [])
            
            # 2. Get mechanism of action
            params = {
                "molecule_chembl_id": molecule_chembl_id,
                "format": "json"
            }
            mechanisms = await self._make_request("mechanism", params=params)
            molecule_data["mechanisms_of_action"] = mechanisms.get("mechanisms", [])
            
            return {
                "success": True,
                "molecule_data": molecule_data
            }
            
        except Exception as e:
            BioChatLogger.log_error(f"ChEMBL compound details error for ID '{molecule_chembl_id}'", e)
            return {
                "success": False,
                "error": str(e),
                "molecule_chembl_id": molecule_chembl_id
            }

    async def get_bioactivities(self, molecule_chembl_id: str, limit: int = 20) -> dict:
        """
        Retrieve bioactivity data for a given ChEMBL molecule ID.
        
        Args:
            molecule_chembl_id (str): The ChEMBL ID for the molecule
            limit (int): Maximum number of activity records to return
            
        Returns:
            dict: Bioactivity data including targets, assays, and activity values
        """
        try:
            BioChatLogger.log_info(f"Getting bioactivities for ChEMBL ID: {molecule_chembl_id} (limit: {limit})")
            params = {
                "molecule_chembl_id": molecule_chembl_id,
                "format": "json",
                "limit": limit,
                "sort": "-standard_value"  # Sort by activity value (most potent first)
            }
            
            bioactivities = await self._make_request("activity", params=params)
            
            if not bioactivities or "activities" not in bioactivities:
                return {
                    "success": False,
                    "error": f"No bioactivity data found for molecule ID: {molecule_chembl_id}"
                }
                
            # Process and structure the bioactivity data
            structured_activities = []
            for activity in bioactivities.get("activities", []):
                structured_activities.append({
                    "target_name": activity.get("target_name", ""),
                    "target_organism": activity.get("target_organism", ""),
                    "standard_type": activity.get("standard_type", ""),
                    "standard_value": activity.get("standard_value", ""),
                    "standard_units": activity.get("standard_units", ""),
                    "assay_description": activity.get("assay_description", ""),
                    "document_year": activity.get("document_year", "")
                })
                
            return {
                "success": True,
                "molecule_chembl_id": molecule_chembl_id,
                "activities": structured_activities,
                "activity_count": len(structured_activities)
            }
            
        except Exception as e:
            BioChatLogger.log_error(f"ChEMBL bioactivities error for ID '{molecule_chembl_id}'", e)
            return {
                "success": False,
                "error": str(e),
                "molecule_chembl_id": molecule_chembl_id
            }

    async def get_target_info(self, target_chembl_id: str) -> dict:
        """
        Retrieve target information from ChEMBL using a ChEMBL target ID.
        
        Args:
            target_chembl_id (str): The ChEMBL ID for the target
            
        Returns:
            dict: Comprehensive target information including properties and related data
        """
        try:
            BioChatLogger.log_info(f"Getting target information for ChEMBL ID: {target_chembl_id}")
            params = {"format": "json"}
            endpoint = f"target/{target_chembl_id}"
            
            # Get basic target data
            target_data = await self._make_request(endpoint, params=params)
            
            if not target_data or "target_chembl_id" not in target_data:
                return {
                    "success": False,
                    "error": f"No data found for target ID: {target_chembl_id}"
                }
                
            # Get active compounds for this target (with a limit to avoid huge result sets)
            params = {
                "target_chembl_id": target_chembl_id,
                "format": "json",
                "limit": 10,
                "sort": "-standard_value"  # Most potent first
            }
            
            activities = await self._make_request("activity", params=params)
            target_data["top_compounds"] = [
                {
                    "molecule_chembl_id": act.get("molecule_chembl_id", ""),
                    "molecule_name": act.get("molecule_pref_name", ""),
                    "activity_type": act.get("standard_type", ""),
                    "activity_value": act.get("standard_value", ""),
                    "activity_units": act.get("standard_units", "")
                }
                for act in activities.get("activities", [])
            ]
            
            return {
                "success": True,
                "target_data": target_data
            }
            
        except Exception as e:
            BioChatLogger.log_error(f"ChEMBL target info error for ID '{target_chembl_id}'", e)
            return {
                "success": False,
                "error": str(e),
                "target_chembl_id": target_chembl_id
            }
    
    async def search_by_similarity(self, smiles: str, similarity: float = 0.8, limit: int = 10) -> dict:
        """
        Search for compounds with structural similarity to the provided SMILES string.
        
        Args:
            smiles (str): SMILES notation of the query molecule
            similarity (float): Similarity threshold (0-1), default 0.8
            limit (int): Maximum number of results to return
            
        Returns:
            dict: Similar compounds with their similarity scores
        """
        try:
            BioChatLogger.log_info(f"Searching ChEMBL for compounds similar to SMILES: {smiles}")
            params = {
                "limit": limit,
                "format": "json",
                "similarity": similarity
            }
            
            endpoint = f"similarity/{smiles}"
            result = await self._make_request(endpoint, params=params)
            
            if not result or "molecules" not in result:
                return {
                    "success": False,
                    "error": f"No similar compounds found for SMILES: {smiles}"
                }
                
            return {
                "success": True,
                "query_smiles": smiles,
                "similarity_threshold": similarity,
                "similar_compounds": result.get("molecules", []),
                "count": len(result.get("molecules", []))
            }
            
        except Exception as e:
            BioChatLogger.log_error(f"ChEMBL similarity search error for SMILES '{smiles}'", e)
            return {
                "success": False,
                "error": str(e),
                "smiles": smiles
            }
    
    async def search_by_substructure(self, smiles: str, limit: int = 10) -> dict:
        """
        Search for compounds containing the provided SMILES as a substructure.
        
        Args:
            smiles (str): SMILES notation of the query substructure
            limit (int): Maximum number of results to return
            
        Returns:
            dict: Compounds containing the substructure
        """
        try:
            BioChatLogger.log_info(f"Searching ChEMBL for compounds with substructure SMILES: {smiles}")
            params = {
                "limit": limit,
                "format": "json"
            }
            
            endpoint = f"substructure/{smiles}"
            result = await self._make_request(endpoint, params=params)
            
            if not result or "molecules" not in result:
                return {
                    "success": False,
                    "error": f"No compounds found containing substructure SMILES: {smiles}"
                }
                
            return {
                "success": True,
                "query_smiles": smiles,
                "matching_compounds": result.get("molecules", []),
                "count": len(result.get("molecules", []))
            }
            
        except Exception as e:
            BioChatLogger.log_error(f"ChEMBL substructure search error for SMILES '{smiles}'", e)
            return {
                "success": False,
                "error": str(e),
                "smiles": smiles
            }


