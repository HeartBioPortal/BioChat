from typing import List, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

class LiteratureSearchParams(BaseModel):
    """Parameters for literature search queries"""
    genes: List[str] = Field(
        default_factory=list,
        description="List of gene names or symbols to search for"
    )
    phenotypes: List[str] = Field(
        default_factory=list,
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
        # Convert None to empty lists for optional fields
        values['genes'] = values.get('genes') or []
        values['phenotypes'] = values.get('phenotypes') or []
        values['additional_terms'] = values.get('additional_terms') or []
        
        if not any([values['genes'], values['phenotypes'], values['additional_terms']]):
            raise ValueError("At least one search term must be provided")
        return values

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
    # include_hierarchy: bool = Field(default=False, description="Include pathway hierarchy")
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


class PharmGKBChemicalQueryParams(BaseModel):
    """Parameters for searching Chemical objects by name."""
    name: str = Field(..., description="The chemical (drug) name to query")
    view: Optional[str] = Field("base", description="The view level (min, base, max)")

class PharmGKBGetChemicalParams(BaseModel):
    """Parameters for retrieving a Chemical object by PharmGKB ID."""
    pharmgkb_id: str = Field(..., description="The PharmGKB chemical identifier")
    view: Optional[str] = Field("base", description="The view level (min, base, max)")

class PharmGKBDrugLabelQueryParams(BaseModel):
    """Parameters for searching Drug Label objects by name."""
    name: str = Field(..., description="The drug name to query")
    view: Optional[str] = Field("base", description="The view level (min, base, max)")

class PharmGKBGetDrugLabelParams(BaseModel):
    """Parameters for retrieving a Drug Label by PharmGKB ID."""
    pharmgkb_id: str = Field(..., description="The PharmGKB drug label identifier")
    view: Optional[str] = Field("base", description="The view level (min, base, max)")

class PharmGKBPathwayQueryParams(BaseModel):
    """Parameters for querying Pathway objects."""
    name: Optional[str] = Field(None, description="The name of the pathway")
    accessionId: Optional[str] = Field(None, description="The PharmGKB pathway identifier")
    view: Optional[str] = Field("base", description="The view level (min, base, max)")

class PharmGKBGetPathwayParams(BaseModel):
    """Parameters for retrieving a Pathway object by PharmGKB ID."""
    pharmgkb_id: str = Field(..., description="The PharmGKB pathway identifier")
    view: Optional[str] = Field("base", description="The view level (min, base, max)")

class PharmGKBClinicalAnnotationQueryParams(BaseModel):
    """Parameters for querying Clinical Annotation objects."""
    # No filtering parameters are officially supported by the API,
    # but you may include a view parameter.
    view: Optional[str] = Field("base", description="The view level (min, base, max)")

class PharmGKBVariantAnnotationQueryParams(BaseModel):
    """Parameters for retrieving a Variant Annotation by PharmGKB ID."""
    pharmgkb_id: str = Field(..., description="The PharmGKB variant annotation identifier")
    view: Optional[str] = Field("base", description="The view level (min, base, max)")


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


class ChemblSearchParams(BaseModel):
    """
    Parameters for searching compounds using the ChEMBL API.
    The query represents a gene, protein, or compound name.
    """
    query: str = Field(..., description="Search query for ChEMBL compounds")


class ChemblCompoundDetailsParams(BaseModel):
    """
    Parameters for retrieving compound details from ChEMBL.
    """
    molecule_chembl_id: str = Field(..., description="ChEMBL molecule identifier")

class ChemblBioactivitiesParams(BaseModel):
    """
    Parameters for retrieving bioactivity data from ChEMBL.
    """
    molecule_chembl_id: str = Field(..., description="ChEMBL molecule identifier")
    limit: int = Field(20, description="Maximum number of bioactivity records to return", ge=1, le=100)

class ChemblTargetInfoParams(BaseModel):
    """
    Parameters for retrieving target information from ChEMBL.
    """
    target_chembl_id: str = Field(..., description="ChEMBL target identifier")

class ChemblSimilaritySearchParams(BaseModel):
    """
    Parameters for searching compounds by structural similarity in ChEMBL.
    """
    smiles: str = Field(..., description="SMILES notation of the query molecule")
    similarity: float = Field(0.8, description="Similarity threshold (0-1)", ge=0.1, le=1.0)
    limit: int = Field(10, description="Maximum number of results to return", ge=1, le=100)

class ChemblSubstructureSearchParams(BaseModel):
    """
    Parameters for searching compounds containing a specific substructure in ChEMBL.
    """
    smiles: str = Field(..., description="SMILES notation of the query substructure")
    limit: int = Field(10, description="Maximum number of results to return", ge=1, le=100)


# Update the problematic tool definition in BIOCHAT_TOOLS
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
            "name": "search_chembl",
            "description": "Search for chemical compounds using the ChEMBL API based on a gene, protein, or compound name.",
            "parameters": ChemblSearchParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_chembl_compound_details",
            "description": "Retrieve detailed compound information from ChEMBL using a ChEMBL molecule ID.",
            "parameters": ChemblCompoundDetailsParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_chembl_bioactivities",
            "description": "Retrieve bioactivity data from ChEMBL for a given molecule.",
            "parameters": ChemblBioactivitiesParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_chembl_target_info",
            "description": "Retrieve target information from ChEMBL using a ChEMBL target ID.",
            "parameters": ChemblTargetInfoParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_chembl_similarity",
            "description": "Search for compounds with structural similarity to a provided SMILES string. This is useful for finding chemically similar compounds to a molecule of interest.",
            "parameters": ChemblSimilaritySearchParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_chembl_substructure",
            "description": "Search for compounds containing a specific substructure defined by a SMILES string. This is useful for finding compounds with a particular chemical fragment or functional group.",
            "parameters": ChemblSubstructureSearchParams.model_json_schema()
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
    },
    {
        "type": "function",
        "function": {
            "name": "search_chemical",
            "description": "Search for Chemical objects by name to retrieve candidate PharmGKB compound IDs.",
            "parameters": PharmGKBChemicalQueryParams.model_json_schema(),
            "required": ["name"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_chemical",
            "description": "Retrieve a Chemical object by its PharmGKB ID.",
            "parameters": PharmGKBGetChemicalParams.model_json_schema(),
            "required": ["pharmgkb_id"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_drug_label",
            "description": "Retrieve a Drug Label by its PharmGKB ID.",
            "parameters": PharmGKBGetDrugLabelParams.model_json_schema(),
            "required": ["pharmgkb_id"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_drug_labels",
            "description": "Search for Drug Label objects by name.",
            "parameters": PharmGKBDrugLabelQueryParams.model_json_schema(),
            "required": ["name"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_pathway",
            "description": "Query for Pathway objects by name or accessionId.",
            "parameters": PharmGKBPathwayQueryParams.model_json_schema(),
            "required": []
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pathway",
            "description": "Retrieve a Pathway object by its PharmGKB ID.",
            "parameters": PharmGKBGetPathwayParams.model_json_schema(),
            "required": ["pharmgkb_id"]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_clinical_annotation",
            "description": "Query Clinical Annotation objects (filtering is performed client-side).",
            "parameters": PharmGKBClinicalAnnotationQueryParams.model_json_schema(),
            "required": []
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_variant_annotation",
            "description": "Retrieve a Variant Annotation by its PharmGKB ID.",
            "parameters": PharmGKBVariantAnnotationQueryParams.model_json_schema(),
            "required": ["pharmgkb_id"]
        }
    }
]