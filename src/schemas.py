from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class LiteratureSearchParams(BaseModel):
    genes: List[str] = Field(default_factory=list, description="List of gene names or symbols to search for")
    phenotypes: List[str] = Field(description="List of phenotypes or diseases to search for")
    additional_terms: List[str] = Field(default_factory=list, description="Additional search terms to refine the query")
    date_range: Optional[Dict[str, str]] = Field(default=None, description="Date range in YYYY/MM/DD format")
    max_results: int = Field(default=10, description="Maximum number of results to return")

    class Config:
        json_schema_extra = {
            "example": {
                "genes": ["BRCA1", "BRCA2"],
                "phenotypes": ["breast cancer"],
                "additional_terms": ["treatment", "therapy"],
                "max_results": 5
            }
        }

class VariantSearchParams(BaseModel):
    chromosome: str = Field(description="Chromosome name (e.g., '1', 'X', 'Y')")
    start: int = Field(description="Start position of the genomic region")
    end: int = Field(description="End position of the genomic region")
    species: str = Field(default="homo_sapiens", description="Species name in Ensembl format")

class GWASSearchParams(BaseModel):
    trait: str = Field(description="Trait or disease to search for")
    gene: Optional[str] = Field(default=None, description="Gene name to filter results")
    pvalue_threshold: float = Field(default=5e-8, description="P-value significance threshold")

class ProteinInfoParams(BaseModel):
    protein_id: str = Field(description="UniProt identifier or gene name")
    include_features: bool = Field(default=True, description="Include protein features in the response")

class ProteinInteractionParams(BaseModel):
    """Parameters for protein interaction queries"""
    protein_id: str = Field(description="Protein identifier")
    include_indirect: bool = Field(default=True, description="Include indirect interactions")
    confidence_score: float = Field(default=0.7, description="Minimum confidence score")
    max_interactions: int = Field(default=100, description="Maximum number of interactions to return")

class PathwayAnalysisParams(BaseModel):
    """Parameters for pathway analysis"""
    genes: List[str] = Field(description="List of gene identifiers")
    pathway_types: List[str] = Field(default_factory=list, description="Types of pathways to include")
    species: str = Field(default="homo_sapiens", description="Species to analyze")
    include_child_pathways: bool = Field(default=True, description="Include child pathways")

class GeneticVariantParams(BaseModel):
    """Parameters for genetic variant analysis"""
    gene: str = Field(description="Gene identifier")
    variant_types: List[str] = Field(default_factory=list, description="Types of variants to include")
    clinical_significance: Optional[List[str]] = Field(default=None, description="Clinical significance levels")
    population: Optional[str] = Field(default=None, description="Population identifier")

class MolecularMechanismParams(BaseModel):
    """Parameters for molecular mechanism analysis"""
    protein_id: str = Field(description="Protein identifier")
    mechanism_types: List[str] = Field(description="Types of mechanisms to analyze")
    include_interactions: bool = Field(default=True, description="Include protein interactions")
    include_pathways: bool = Field(default=True, description="Include pathway information")


# OpenAI tool definitions
BIOCHAT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_literature",
            "description": "Search scientific literature using NCBI PubMed for biological and medical research. Use this when the user asks about research papers, studies, or scientific findings.",
            "parameters": LiteratureSearchParams.model_json_schema(),
            "required": ["genes", "phenotypes"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_variants",
            "description": "Search for genetic variants in a genomic region using Ensembl. Use this when the user asks about genetic variations or mutations in specific genomic regions.",
            "parameters": VariantSearchParams.model_json_schema(),
            "required": ["chromosome", "start", "end"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_gwas",
            "description": "Search GWAS Catalog for genetic associations with traits and diseases. Use this when the user asks about genetic associations with diseases or traits.",
            "parameters": GWASSearchParams.model_json_schema(),
            "required": ["trait"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_protein_info",
            "description": "Get detailed protein information from UniProt. Use this when the user asks about protein structure, function, or annotations.",
            "parameters": ProteinInfoParams.model_json_schema(),
            "required": ["protein_id"]
        }
    },
        {
        "type": "function",
        "function": {
            "name": "analyze_protein_interactions",
            "description": "Analyze protein-protein interactions and their functional implications",
            "parameters": ProteinInteractionParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_pathways",
            "description": "Analyze biological pathways and their regulation",
            "parameters": PathwayAnalysisParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_genetic_variants",
            "description": "Analyze genetic variants and their clinical implications",
            "parameters": GeneticVariantParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_molecular_mechanisms",
            "description": "Analyze molecular mechanisms and signaling pathways",
            "parameters": MolecularMechanismParams.model_json_schema()
        }
    }
]