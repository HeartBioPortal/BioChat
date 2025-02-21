"""
Module for summarizing API responses from various biological databases.
Uses strategy pattern to handle different summarization approaches for each API.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from dataclasses import dataclass

class APISummarizer(ABC):
    """Abstract base class for API response summarizers."""
    
    @abstractmethod
    def summarize(self, response: Dict) -> Dict:
        """Summarize the API response into a condensed format."""
        pass

    def _format_timestamp(self) -> str:
        """Helper method to format current timestamp."""
        return datetime.now().isoformat()

@dataclass
class OpenTargetsDrugInfo:
    """Data class for storing drug information from OpenTargets."""
    name: str
    status: str
    mechanism: str
    disease_name: str
    phase: int
    drug_type: str

class OpenTargetsSummarizer(APISummarizer):
    """Summarizer for OpenTargets API responses."""
    
    def summarize(self, response: Dict) -> Dict:
        """
        Summarize OpenTargets API response, focusing on drug information.
        
        Args:
            response: Raw API response containing target analysis data
            
        Returns:
            Dict containing summarized information
        """
        if not response or "data" not in response:
            return {"error": "No valid data in response"}
            
        data = response["data"]
        drugs_data = data.get("drugs", {})
        
        # Extract drug information
        drug_count = drugs_data.get("count", 0)
        drug_rows = []
        
        for row in drugs_data.get("rows", []):
            try:
                drug_info = OpenTargetsDrugInfo(
                    name=row["drug"]["name"],
                    status=row["status"],
                    mechanism=row["mechanismOfAction"],
                    disease_name=row["disease"]["name"],
                    phase=row["phase"],
                    drug_type=row["drug"]["drugType"]
                )
                drug_rows.append(vars(drug_info))
            except KeyError as e:
                continue  # Skip malformed entries
                
        return {
            "total_drugs": drug_count,
            "drugs": drug_rows,
            "summary_timestamp": self._format_timestamp()
        }

class BioGridSummarizer(APISummarizer):
    """Summarizer for BioGRID API responses."""
    
    def summarize(self, response: Dict) -> Dict:
        """Summarize BioGRID chemical interaction data."""
        if not response.get("success"):
            return {"error": response.get("error", "Unknown error")}
            
        interactions = response.get("data", {})
        metadata = response.get("metadata", {})
        
        summary = {
            "chemicals_searched": response.get("chemical_list", []),
            "chemicals_found": metadata.get("chemicals_found", 0),
            "total_interactions": response.get("interaction_count", 0),
            "protein_targets": metadata.get("protein_targets", 0),
            "experiment_types": metadata.get("experiment_types", []),
            "top_interactions": []
        }
        
        # Add top 5 interactions
        for interaction_id, interaction in list(interactions.items())[:5]:
            summary["top_interactions"].append({
                "chemical": interaction.get("chemical_name"),
                "target": interaction.get("protein_target"),
                "type": interaction.get("interaction_type"),
                "evidence": interaction.get("interaction_evidence"),
                "publication": f"{interaction.get('publication')} (PMID:{interaction.get('pubmed_id')})"
            })
            
        summary["summary_timestamp"] = self._format_timestamp()
        return summary

class IntActSummarizer(APISummarizer):
    """Summarizer for IntAct API responses."""
    
    def summarize(self, response: Dict) -> Dict:
        """Summarize IntAct interaction data."""
        if not response.get("success"):
            return {"error": response.get("error", "Unknown error")}
            
        data = response.get("data", {})
        query = response.get("query", "")
        count = response.get("interaction_count", 0)
        
        summary = {
            "query": query,
            "total_interactions": count,
            "top_interactions": []
        }
        
        # Include top 5 interactions
        content = data.get("content", [])
        for interaction in content[:5]:
            summary["top_interactions"].append({
                "interactor_a": interaction.get("interactorA"),
                "interactor_b": interaction.get("interactorB"),
                "interaction_type": interaction.get("type"),
                "score": interaction.get("score")
            })
            
        summary["summary_timestamp"] = self._format_timestamp()
        return summary

class APISummarizerFactory:
    """Factory class for creating appropriate summarizer instances."""
    
    _summarizers = {
        "opentargets": OpenTargetsSummarizer,
        "biogrid": BioGridSummarizer,
        "intact": IntActSummarizer
    }
    
    @classmethod
    def get_summarizer(cls, api_name: str) -> APISummarizer:
        """Get the appropriate summarizer for the given API."""
        summarizer_class = cls._summarizers.get(api_name.lower())
        if not summarizer_class:
            raise ValueError(f"No summarizer found for API: {api_name}")
        return summarizer_class()

class ResponseSummarizer:
    """Main class for handling API response summarization."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ResponseSummarizer, cls).__new__(cls)
            cls._instance.factory = APISummarizerFactory()
        return cls._instance
    
    def __init__(self):
        self.factory = APISummarizerFactory()
        
    def summarize_response(self, api_name: str, response: Dict) -> Dict:
        """
        Summarize an API response using the appropriate summarizer.
        
        Args:
            api_name: Name of the API (e.g., "opentargets", "biogrid")
            response: Raw API response to summarize
            
        Returns:
            Dict containing the summarized information
        """
        try:
            summarizer = self.factory.get_summarizer(api_name)
            return summarizer.summarize(response)
        except Exception as e:
            return {
                "error": f"Summarization failed: {str(e)}",
                "api": api_name,
                "timestamp": self._format_timestamp()
            }
            
    def _format_timestamp(self) -> str:
        return datetime.now().isoformat()