"""
Module for summarizing API responses from various biological databases and handling
string-based interactions with OpenAI LLMs.
Uses strategy pattern to handle different summarization approaches for each API.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from dataclasses import dataclass
import logging
from openai import AsyncOpenAI

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

class ChemblSummarizer(APISummarizer):
    """Summarizer for ChEMBL API responses."""
    
    def summarize(self, response: Dict) -> Dict:
        """Summarize ChEMBL data focusing on key compound properties."""
        if "error" in response:
            return {"error": response.get("error", "Unknown error")}
            
        if "molecules" not in response and "molecule_hierarchy" not in response:
            # Likely a search result
            compounds = response.get("molecules", [])
            if not compounds:
                compounds = [response] if "molecule_chembl_id" in response else []
                
            summary = {
                "total_compounds": len(compounds),
                "compounds": []
            }
            
            # Add compound data
            for compound in compounds[:5]:  # Limit to top 5
                summary["compounds"].append({
                    "chembl_id": compound.get("molecule_chembl_id"),
                    "pref_name": compound.get("pref_name"),
                    "molecule_type": compound.get("molecule_type"),
                    "max_phase": compound.get("max_phase"),
                    "activity_count": compound.get("activity_count")
                })
                
            return summary
            
        # Single compound detail
        compound = response
        summary = {
            "chembl_id": compound.get("molecule_chembl_id"),
            "name": compound.get("pref_name"),
            "structure": {
                "smiles": compound.get("molecule_structures", {}).get("canonical_smiles"),
                "inchi": compound.get("molecule_structures", {}).get("standard_inchi")
            },
            "properties": {
                "molecular_weight": compound.get("molecule_properties", {}).get("full_mwt"),
                "alogp": compound.get("molecule_properties", {}).get("alogp"),
                "psa": compound.get("molecule_properties", {}).get("psa"),
                "hba": compound.get("molecule_properties", {}).get("hba"),
                "hbd": compound.get("molecule_properties", {}).get("hbd")
            }
        }
        
        return summary

class APISummarizerFactory:
    """Factory class for creating appropriate summarizer instances."""
    
    _summarizers = {
        "opentargets": OpenTargetsSummarizer,
        "biogrid": BioGridSummarizer,
        "intact": IntActSummarizer,
        "chembl": ChemblSummarizer
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

class StringInteractionExecutor:
    """
    Handles string-based interactions with OpenAI's LLM for custom functionality.
    This complements the OpenAI function calling interface.
    """
    
    def __init__(self, openai_client: AsyncOpenAI, model: str = "gpt-4o"):
        """
        Initialize the string interaction executor with OpenAI credentials.
        
        Args:
            openai_client: AsyncOpenAI client instance
            model: The OpenAI model to use for string interactions
        """
        self.client = openai_client
        self.model = model
        self.logger = logging.getLogger(__name__)
    
    async def execute_query(self, query: str, system_prompt: str, 
                           context: Optional[str] = None) -> str:
        """
        Execute a string-based query against the OpenAI model.
        
        Args:
            query: The user query to process
            system_prompt: The system prompt to guide the model behavior
            context: Optional additional context for the model
            
        Returns:
            The model's response as a string
        """
        try:
            messages = [{"role": "system", "content": system_prompt}]
            
            if context:
                messages.append({"role": "system", "content": f"Context:\n{context}"})
                
            messages.append({"role": "user", "content": query})
            
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"String interaction execution error: {str(e)}")
            return f"Error processing query: {str(e)}"
    
    async def guided_analysis(self, data: Dict, analysis_prompt: str) -> str:
        """
        Perform a guided analysis of structured data using the LLM.
        
        Args:
            data: Structured data to analyze
            analysis_prompt: The specific instructions for analysis
            
        Returns:
            The model's analysis as a string
        """
        try:
            # Format data as a JSON string
            data_str = json.dumps(data, indent=2)
            
            system_prompt = """
            You are a specialized scientific analysis system. Your task is to analyze 
            the provided structured data and respond with a detailed analysis.
            Focus on identifying patterns, drawing conclusions, and extracting insights.
            Maintain scientific precision and clarity throughout your analysis.
            """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analysis instructions: {analysis_prompt}\n\nData to analyze:\n{data_str}"}
            ]
            
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Guided analysis error: {str(e)}")
            return f"Error performing analysis: {str(e)}"