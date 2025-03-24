"""
OpenTargetsClient API client.
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


class OpenTargetsClient(BioDatabaseAPI):
    """Client for interacting with Open Targets Platform GraphQL API"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.platform.opentargets.org/api/v4/graphql"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def _execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Execute a GraphQL query"""
        try:
            payload = {
                "query": query,
                "variables": variables or {}
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, json=payload, headers=self.headers) as response:
                    if response.status == 429:  # Rate limit
                        retry_after = int(response.headers.get('Retry-After', 5))
                        await asyncio.sleep(retry_after)
                        return await self._execute_query(query, variables)
                        
                    response.raise_for_status()
                    result = await response.json()
                    
                    if "errors" in result:
                        raise Exception(f"GraphQL errors: {result['errors']}")
                        
                    return result.get("data", {})
                    
        except aiohttp.ClientError as e:
            BioChatLogger.log_error("OpenTargets API request error", e)
            raise
        except Exception as e:
            BioChatLogger.log_error("OpenTargets query error", e)
            raise

    async def search(self, query: str, entity: str = None, size: int = 10) -> Dict:
        """Search across targets, diseases, and drugs"""
        search_query = """
        query SearchQuery($searchQuery: String!, $entity: String, $size: Int) {
            search(queryString: $searchQuery, entityNames: [$entity], size: $size) {
                total
                hits {
                    id
                    entity
                    object {
                        id
                        name
                    }
                }
            }
        }
        """
        
        variables = {
            "searchQuery": query,
            "entity": entity,
            "size": size
        }
        
        try:
            return await self._execute_query(search_query, variables)
        except Exception as e:
            BioChatLogger.log_error(f"OpenTargets search error", e)
            return {"error": str(e)}

    async def get_target_info(self, target_id: str) -> Dict:
        """Get detailed information about a target"""
        # Updated query to match schema
        target_query = """
        query TargetQuery($targetId: String!) {
            target(ensemblId: $targetId) {
                id
                approvedSymbol
                approvedName
                biotype
                knownDrugs(size: 20) {
                    count
                    rows {
                        phase
                        status
                        mechanismOfAction
                        disease {
                            id
                            name
                        }
                        drug {
                            id
                            name
                            drugType
                            maximumClinicalTrialPhase
                        }
                    }
                }
                safetyLiabilities {
                    event
                    eventId
                    effects {
                        direction
                        dosing
                    }
                    biosamples {
                        tissueLabel
                        tissueId
                    }
                }
            }
        }
        """
        
        try:
            BioChatLogger.log_info(f"Querying OpenTargets for target: {target_id}")
            result = await self._execute_query(target_query, {"targetId": target_id})
            
            if not result or "target" not in result:
                error_msg = "No target data found"
                BioChatLogger.log_error(error_msg, Exception(error_msg))
                return {"error": error_msg, "target_id": target_id}
            
            return result
            
        except Exception as e:
            BioChatLogger.log_error(f"OpenTargets target info error", e)
            return {"error": str(e), "target_id": target_id}

    async def get_disease_info(self, disease_id: str) -> Dict:
        """Get detailed information about a disease"""
        disease_query = """
        query DiseaseQuery($diseaseId: String!) {
            disease(efoId: $diseaseId) {
                id
                name
                description
                therapeuticAreas {
                    id
                    name
                }
            }
        }
        """
        
        try:
            return await self._execute_query(disease_query, {"diseaseId": disease_id})
        except Exception as e:
            BioChatLogger.log_error(f"OpenTargets disease info error", e)
            return {"error": str(e)}

    async def get_target_disease_associations(self, 
                                           target_id: str = None,
                                           disease_id: str = None,
                                           score_min: float = 0.0,
                                           size: int = 10) -> Dict:
        """Get associations between targets and diseases"""
        association_query = """
        query AssociationsQuery($targetId: String, $diseaseId: String, $scoreMin: Float, $size: Int) {
            associatedDiseases(
                ensemblId: $targetId,
                efoId: $diseaseId,
                datasourceScoreMin: $scoreMin,
                size: $size
            ) {
                count
                rows {
                    disease {
                        id
                        name
                    }
                    score
                    datatypeScores {
                        id
                        score
                    }
                }
            }
        }
        """
        
        variables = {
            "targetId": target_id,
            "diseaseId": disease_id,
            "scoreMin": score_min,
            "size": size
        }
        
        try:
            return await self._execute_query(association_query, variables)
        except Exception as e:
            BioChatLogger.log_error(f"OpenTargets association error", e)
            return {"error": str(e)}


    async def _execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict:
            """Execute a GraphQL query with proper error handling"""
            try:
                payload = {
                    "query": query,
                    "variables": variables or {}
                }
                
                # Use aiohttp session for requests
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.base_url,
                        json=payload,
                        headers=self.headers,
                        raise_for_status=True
                    ) as response:
                        result = await response.json()
                        
                        if "errors" in result:
                            raise Exception(f"GraphQL errors: {result['errors']}")
                        
                        if "data" not in result:
                            raise Exception("No data in response")
                            
                        return result.get("data", {})
                        
            except aiohttp.ClientError as e:
                BioChatLogger.log_error("OpenTargets API request error", e)
                raise
            except Exception as e:
                BioChatLogger.log_error("OpenTargets query error", e)
                raise

    async def get_target_safety(self, target_id: str) -> Dict:
        """Get safety information for a target"""
        query = """
        query TargetSafety($targetId: String!) {
            target(ensemblId: $targetId) {
                id
                safetyLiabilities {
                    biosamples {
                        tissueLabel
                        tissueId
                        cellLabel
                        cellFormat
                        cellId
                    }
                    effects {
                        direction
                        dosing
                    }
                    event
                    eventId
                    datasource
                    literature
                    studies {
                        name
                        description
                        type
                    }
                }
            }
        }
        """
        
        try:
            result = await self._execute_query(query, {"targetId": target_id})
            return result.get("target", {}).get("safetyLiabilities", [])
        except Exception as e:
            BioChatLogger.log_error(f"OpenTargets target safety error", e)
            return {"error": str(e)}

    async def get_known_drugs(self, target_id: str, size: int = 10) -> Dict:
        """Get known drugs for a target"""
        query = """
        query TargetDrugs($targetId: String!, $size: Int!) {
            target(ensemblId: $targetId) {
                id
                knownDrugs(size: $size) {
                    count
                    cursor
                    rows {
                        phase
                        status
                        mechanismOfAction
                        disease {
                            id
                            name
                        }
                        drug {
                            id
                            name
                            drugType
                            maximumClinicalTrialPhase
                        }
                        urls {
                            url
                            name
                        }
                    }
                }
            }
        }
        """
        
        try:
            result = await self._execute_query(query, {
                "targetId": target_id,
                "size": size
            })
            return result.get("target", {}).get("knownDrugs", {})
        except Exception as e:
            BioChatLogger.log_error(f"OpenTargets known drugs error", e)
            return {"error": str(e)}

    async def get_target_expression(self, target_id: str) -> Dict:
        """Get expression data for a target"""
        query = """
        query TargetExpression($targetId: String!) {
            target(ensemblId: $targetId) {
                id
                expressions {
                    tissue {
                        id
                        label
                        anatomicalSystems
                        organs
                    }
                    rna {
                        value
                        unit
                        level
                        zscore
                    }
                    protein {
                        level
                        reliability
                        cellType {
                            name
                            level
                            reliability
                        }
                    }
                }
            }
        }
        """
        
        try:
            result = await self._execute_query(query, {"targetId": target_id})
            return result.get("target", {}).get("expressions", [])
        except Exception as e:
            BioChatLogger.log_error(f"OpenTargets expression error", e)
            return {"error": str(e)}