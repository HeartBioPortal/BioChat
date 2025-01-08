from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class LiteratureSearchParams(BaseModel):
    genes: List[str] = Field(description="List of gene names or symbols to search for")
    phenotypes: List[str] = Field(description="List of phenotypes or diseases to search for")
    additional_terms: Optional[List[str]] = Field(None, description="Additional search terms to refine the query")
    date_range: Optional[Dict[str, str]] = Field(None, description="Date range in YYYY/MM/DD format")
    max_results: Optional[int] = Field(10, description="Maximum number of results to return")

class VariantSearchParams(BaseModel):
    chromosome: str = Field(description="Chromosome name (e.g., '1', 'X', 'Y')")
    start: int = Field(description="Start position of the genomic region")
    end: int = Field(description="End position of the genomic region")
    species: Optional[str] = Field("homo_sapiens", description="Species name in Ensembl format")

class GWASSearchParams(BaseModel):
    trait: str = Field(description="Trait or disease to search for")
    gene: Optional[str] = Field(None, description="Gene name to filter results")
    pvalue_threshold: Optional[float] = Field(5e-8, description="P-value significance threshold")

class ProteinInfoParams(BaseModel):
    protein_id: str = Field(description="UniProt identifier or gene name")
    include_features: Optional[bool] = Field(True, description="Include protein features in the response")

# OpenAI tool definitions
BIOCHAT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_literature",
            "description": "Search scientific literature using NCBI PubMed for biological and medical research. Use this when the user asks about research papers, studies, or scientific findings.",
            "parameters": LiteratureSearchParams.model_json_schema(),
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_variants",
            "description": "Search for genetic variants in a genomic region using Ensembl. Use this when the user asks about genetic variations or mutations in specific genomic regions.",
            "parameters": VariantSearchParams.model_json_schema(),
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_gwas",
            "description": "Search GWAS Catalog for genetic associations with traits and diseases. Use this when the user asks about genetic associations with diseases or traits.",
            "parameters": GWASSearchParams.model_json_schema(),
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_protein_info",
            "description": "Get detailed protein information from UniProt. Use this when the user asks about protein structure, function, or annotations.",
            "parameters": ProteinInfoParams.model_json_schema(),
            "strict": True
        }
    }
]