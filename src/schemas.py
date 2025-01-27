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


class PathwayAnalysisParams(BaseModel):
    """Parameters for pathway analysis"""
    gene_id: Optional[str] = Field(None, description="Gene/protein identifier")
    pathway_id: Optional[str] = Field(None, description="Reactome pathway ID")
    disease_id: Optional[str] = Field(None, description="Disease identifier")
    genes: Optional[List[str]] = Field(None, description="List of genes to analyze")
    species: str = Field(default="Homo sapiens", description="Species name")
    include_hierarchy: bool = Field(default=False, description="Include pathway hierarchy")
    include_participants: bool = Field(default=True, description="Include pathway participants")

    @model_validator(mode='before')
    @classmethod
    def validate_inputs(cls, values):
        """Ensure at least one identifier is provided"""
        if not any([
            values.get('gene_id'),
            values.get('pathway_id'),
            values.get('disease_id'),
            values.get('genes')
        ]):
            raise ValueError("At least one of gene_id, pathway_id, disease_id, or genes must be provided")
        return values

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

class PharmGKBClinicalParams(BaseModel):
    """Parameters for PharmGKB clinical annotation queries"""
    drug_id: Optional[str] = Field(None, description="PharmGKB drug identifier")
    gene_id: Optional[str] = Field(None, description="PharmGKB gene identifier")

class PharmGKBVariantParams(BaseModel):
    """Parameters for PharmGKB variant annotation queries"""
    variant_id: str = Field(description="Variant identifier")
    drug_id: Optional[str] = Field(None, description="Drug identifier")

class PharmGKBDiseaseParams(BaseModel):
    """Parameters for PharmGKB disease association queries"""
    disease_id: str = Field(description="Disease identifier")
    association_type: Optional[str] = Field(None, description="Type of association")

class BioGridInteractionParams(BaseModel):
    """Parameters for BioGRID interaction queries"""
    gene_list: List[str] = Field(description="List of gene identifiers")
    include_interactors: bool = Field(default=False, description="Include first-order interactions")
    tax_id: Optional[str] = Field(None, description="Organism identifier")

class BioGridChemicalParams(BaseModel):
    """Parameters for BioGRID chemical interaction queries"""
    gene_list: List[str] = Field(description="Gene list")
    chemical_list: Optional[List[str]] = Field(None, description="Chemical identifiers")
    evidence_list: Optional[List[str]] = Field(None, description="Evidence types")

class IntActSearchParams(BaseModel):
    """Parameters for IntAct interaction queries"""
    query: str = Field(description="Search query string")
    species: Optional[str] = Field(None, description="Species filter")
    negative_filter: str = Field(
        default="POSITIVE_ONLY",
        description="Include/exclude negative interactions"
    )
    page: int = Field(default=0, description="Page number")
    page_size: int = Field(default=10, description="Results per page")

class StringDBEnrichmentParams(BaseModel):
    """Parameters for STRING-DB enrichment analysis"""
    identifiers: List[str] = Field(description="Protein identifiers")
    species: int = Field(default=9606, description="NCBI taxonomy ID")
    background_identifiers: Optional[List[str]] = Field(None, description="Custom background set")



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
            "description": "Search for genetic variants in a genomic region using Ensembl.",
            "parameters": VariantSearchParams.model_json_schema(),
            "required": ["chromosome", "start", "end"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_gwas",
            "description": "Search GWAS Catalog for genetic associations with traits and diseases.",
            "parameters": GWASSearchParams.model_json_schema(),
            "required": ["trait"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_protein_info",
            "description": "Get detailed protein information from UniProt.",
            "parameters": ProteinInfoParams.model_json_schema(),
            "required": ["protein_id"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_string_interactions",
            "description": "Get protein-protein interactions from STRING-DB.",
            "parameters": StringDBEnrichmentParams.model_json_schema(),
            "required": ["identifiers"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_biogrid_interactions",
            "description": "Get protein interaction data from BioGRID.",
            "parameters": BioGridInteractionParams.model_json_schema(),
            "required": ["gene_list"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_intact_interactions",
            "description": "Search molecular interactions in IntAct database.",
            "parameters": IntActSearchParams.model_json_schema(),
            "required": ["query"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_pathways",
            "description": "Analyze biological pathways using Reactome.",
            "parameters": PathwayAnalysisParams.model_json_schema(),
            "required": ["genes"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pharmgkb_annotations",
            "description": "Get pharmacogenomic annotations from PharmGKB.",
            "parameters": PharmGKBClinicalParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pharmgkb_variants",
            "description": "Get variant annotations from PharmGKB.",
            "parameters": PharmGKBVariantParams.model_json_schema(),
            "required": ["variant_id"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_target",
            "description": "Analyze a target using Open Targets Platform.",
            "parameters": TargetAnalysisParams.model_json_schema(),
            "required": ["target_id"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_disease",
            "description": "Analyze a disease using Open Targets Platform.",
            "parameters": DiseaseAnalysisParams.model_json_schema(),
            "required": ["disease_id"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_biogrid_chemical_interactions",
            "description": "Get protein-chemical interaction data from BioGRID.",
            "parameters": BioGridChemicalParams.model_json_schema(),
            "required": ["gene_list"]
        }
    }
]