from typing import List, Dict, Optional
from pydantic import BaseModel, Field, model_validator

class LiteratureSearchParams(BaseModel):
    """Parameters for literature search queries"""
    genes: List[str] = Field(
        default_factory=list,
        description="List of gene names or symbols to search for"
    )
    phenotypes: List[str] = Field(
        description="List of phenotypes or diseases to search for"
    )
    additional_terms: List[str] = Field(
        default_factory=list,
        description="Additional search terms to refine the query"
    )
    date_range: Optional[Dict[str, str]] = Field(
        default=None,
        description="Date range in YYYY/MM/DD format"
    )
    max_results: int = Field(
        default=10,
        description="Maximum number of results to return",
        ge=1,
        le=100
    )

    @model_validator(mode='before')
    @classmethod
    def validate_search_terms(cls, values):
        """Ensure at least one search term is provided"""
        genes = values.get('genes', [])
        phenotypes = values.get('phenotypes', [])
        additional_terms = values.get('additional_terms', [])
        if not any([genes, phenotypes, additional_terms]):
            raise ValueError("At least one search term must be provided")
        return values

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
    """Parameters for variant search queries"""
    chromosome: str = Field(
        description="Chromosome name (e.g., '1', 'X', 'Y')"
    )
    start: int = Field(
        description="Start position of the genomic region",
        gt=0
    )
    end: int = Field(
        description="End position of the genomic region",
        gt=0
    )
    species: str = Field(
        default="homo_sapiens",
        description="Species name in Ensembl format"
    )

    @model_validator(mode='before')
    @classmethod
    def validate_positions(cls, values):
        """Ensure start position is before end position"""
        start = values.get('start', 0)
        end = values.get('end', 0)
        if start >= end:
            raise ValueError("Start position must be less than end position")
        return values

class GWASSearchParams(BaseModel):
    """Parameters for GWAS catalog search"""
    trait: str = Field(
        description="Trait or disease to search for"
    )
    gene: Optional[str] = Field(
        default=None,
        description="Gene name to filter results"
    )
    pvalue_threshold: float = Field(
        default=5e-8,
        description="P-value significance threshold",
        gt=0,
        lt=1
    )

class ProteinInfoParams(BaseModel):
    """Parameters for protein information queries"""
    protein_id: str = Field(
        description="UniProt identifier or gene name"
    )
    include_features: bool = Field(
        default=True,
        description="Include protein features in the response"
    )

class ProteinInteractionParams(BaseModel):
    """Parameters for protein interaction queries"""
    protein_id: str = Field(
        description="Protein identifier"
    )
    include_indirect: bool = Field(
        default=True,
        description="Include indirect interactions"
    )
    confidence_score: float = Field(
        default=0.7,
        description="Minimum confidence score",
        ge=0.0,
        le=1.0
    )
    max_interactions: int = Field(
        default=100,
        description="Maximum number of interactions to return",
        ge=1,
        le=1000
    )

class PathwayAnalysisParams(BaseModel):
    """Parameters for pathway analysis"""
    gene_id: Optional[str] = Field(None, description="Gene/protein identifier (UniProt ID)")
    pathway_id: Optional[str] = Field(None, description="Reactome pathway ID")
    disease_id: Optional[str] = Field(None, description="Disease identifier")
    include_hierarchy: bool = Field(default=False, description="Include pathway hierarchy")
    include_participants: bool = Field(default=True, description="Include pathway participants")

    @model_validator(mode='before')
    @classmethod
    def validate_inputs(cls, values):
        """Ensure at least one identifier is provided"""
        if not any([values.get('gene_id'), values.get('pathway_id'), values.get('disease_id')]):
            raise ValueError("At least one of gene_id, pathway_id, or disease_id must be provided")
        return values

    class Config:
        json_schema_extra = {
            "example": {
                "gene_id": "P38398",
                "include_hierarchy": True,
                "include_participants": True
            }
        }

class GeneticVariantParams(BaseModel):
    """Parameters for genetic variant analysis"""
    gene: str = Field(
        description="Gene identifier"
    )
    variant_types: List[str] = Field(
        default_factory=list,
        description="Types of variants to include"
    )
    clinical_significance: Optional[List[str]] = Field(
        default=None,
        description="Clinical significance levels"
    )
    population: Optional[str] = Field(
        default=None,
        description="Population identifier"
    )

class MolecularMechanismParams(BaseModel):
    """Parameters for molecular mechanism analysis"""
    protein_id: str = Field(
        description="Protein identifier"
    )
    mechanism_types: List[str] = Field(
        description="Types of mechanisms to analyze",
        default_factory=lambda: ["protein_function", "pathway_interaction"]
    )
    include_pathways: bool = Field(
        default=True,
        description="Include pathway information"
    )
    include_interactions: bool = Field(
        default=True,
        description="Include protein interactions"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "protein_id": "BRCA1",
                "mechanism_types": ["protein_function", "pathway_interaction"],
                "include_pathways": True,
                "include_interactions": True
            }
        }

class TargetAnalysisParams(BaseModel):
    """Parameters for target analysis using Open Targets"""
    target_id: str = Field(description="Ensembl ID of the target")
    include_safety: bool = Field(default=True, description="Include safety information")
    include_drugs: bool = Field(default=True, description="Include known drugs")
    include_expression: bool = Field(default=True, description="Include expression data")
    min_association_score: float = Field(
        default=0.1, 
        description="Minimum association score for disease associations",
        ge=0.0,
        le=1.0
    )

class DiseaseAnalysisParams(BaseModel):
    """Parameters for disease analysis using Open Targets"""
    disease_id: str = Field(description="EFO ID of the disease")
    include_targets: bool = Field(default=True, description="Include associated targets")
    min_association_score: float = Field(
        default=0.1,
        description="Minimum association score for target associations",
        ge=0.0,
        le=1.0
    )

# OpenAI tool definitions
BIOCHAT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_literature",
            "description": "Search scientific literature using NCBI PubMed for biological and medical research. Use this when the user asks about research papers, studies, or scientific findings.",
            "parameters": LiteratureSearchParams.model_json_schema(),
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
            "description": "Analyze protein-protein interactions using STRING-DB and BioGRID. Use this for understanding protein interaction networks.",
            "parameters": ProteinInteractionParams.model_json_schema(),
            "required": ["protein_id"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_pathways",
            "description": "Analyze biological pathways using Reactome and BioCyc. Use this for understanding pathway involvement and regulation.",
            "parameters": PathwayAnalysisParams.model_json_schema(),
            "required": ["genes"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_genetic_variants",
            "description": "Analyze genetic variants and their clinical implications using various databases.",
            "parameters": GeneticVariantParams.model_json_schema(),
            "required": ["gene"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_molecular_mechanisms",
            "description": "Analyze molecular mechanisms including protein function, interactions, and pathway involvement.",
            "parameters": MolecularMechanismParams.model_json_schema(),
            "required": ["protein_id"]
        }
    },
        {
        "type": "function",
        "function": {
            "name": "analyze_target",
            "description": "Analyze a target (gene/protein) using Open Targets Platform, including safety, drugs, and disease associations.",
            "parameters": TargetAnalysisParams.model_json_schema(),
            "required": ["target_id"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_disease",
            "description": "Analyze a disease using Open Targets Platform, including associated targets and therapeutic approaches.",
            "parameters": DiseaseAnalysisParams.model_json_schema(),
            "required": ["disease_id"]
        }
    }

]