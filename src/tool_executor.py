from typing import Dict, Any
from datetime import datetime
import json
from src.APIHub import (
    NCBIEutils, EnsemblAPI, GWASCatalog, UniProtAPI,
    StringDBClient, ReactomeClient, PharmGKBClient, DisGeNETClient,
    IntActClient, BioCyc, BioGridClient
)
from src.schemas import (
    LiteratureSearchParams, VariantSearchParams, GWASSearchParams, ProteinInfoParams,
    ProteinInteractionParams, PathwayAnalysisParams, MolecularMechanismParams,GeneticVariantParams
)

class ToolExecutor:
    def __init__(self, ncbi_api_key: str, tool_name: str, email: str, api_keys: Dict[str, str] = None):
        """Initialize database clients with appropriate credentials"""
        # Initialize core clients
        self.ncbi = NCBIEutils(api_key=ncbi_api_key, tool=tool_name, email=email)
        self.ensembl = EnsemblAPI()
        self.gwas = GWASCatalog()
        self.uniprot = UniProtAPI()
        
        # Initialize no-auth clients
        self.string_db = StringDBClient()
        self.reactome = ReactomeClient()
        self.intact = IntActClient()
        
        # Initialize auth-required ?! clients 
        api_keys = api_keys or {}
        self.pharmgkb = PharmGKBClient(api_keys.get("pharmgkb")) if api_keys.get("pharmgkb") else PharmGKBClient(None)
        self.disgenet = DisGeNETClient(api_keys.get("disgenet")) if api_keys.get("disgenet") else DisGeNETClient(None)
        self.biocyc = BioCyc(api_keys.get("biocyc")) if api_keys.get("biocyc") else BioCyc(None)
        self.biogrid = BioGridClient(api_keys.get("biogrid")) if api_keys.get("biogrid") else BioGridClient(None)
        
        # Track available services
        self.available_services = {
            # Core services
            "ncbi": True,
            "ensembl": True,
            "gwas": True,
            "uniprot": True,
            # No-auth services
            "string_db": True,
            "reactome": True,
            "intact": True,
            # Auth-required services
            "pharmgkb": True,
            "disgenet": True,
            "biocyc": True,
            "biogrid": True
        }

    async def analyze_protein_interactions(self, params: Dict) -> Dict:
        """Comprehensive protein interaction analysis"""
        protein_id = params["protein_id"]
        results = {}
        
        # Gather protein interactions from multiple sources
        results["string_db"] = await self.string_db.get_protein_interactions(protein_id)
        results["intact"] = await self.intact.get_molecular_interactions(protein_id)
        results["biogrid"] = await self.biogrid.get_protein_interactions(protein_id)
        
        return {
            "protein_id": protein_id,
            "interaction_data": results,
            "metadata": {
                "sources": ["STRING-DB", "IntAct", "BioGRID"],
                "confidence_score": params.get("confidence_score", 0.7)
            }
        }

    async def analyze_pathways(self, params: Dict) -> Dict:
        """Comprehensive pathway analysis"""
        genes = params["genes"]
        results = {}
        
        for gene in genes:
            gene_results = {}
            gene_results["reactome"] = await self.reactome.get_pathways(gene)
            gene_results["biocyc"] = await self.biocyc.get_metabolic_pathways(gene)
            results[gene] = gene_results
            
        return {
            "genes": genes,
            "pathway_data": results,
            "metadata": {
                "sources": ["Reactome", "BioCyc"],
                "species": params.get("species", "homo_sapiens")
            }
        }

    async def analyze_molecular_mechanisms(self, params: MolecularMechanismParams) -> Dict:
        """Comprehensive molecular mechanism analysis"""
        results = {}
        
        # Gather mechanism data from multiple sources
        if params.include_interactions:
            results["interactions"] = await self.analyze_protein_interactions({
                "protein_id": params.protein_id
            })
            
        if params.include_pathways:
            results["pathways"] = await self.analyze_pathways({
                "genes": [params.protein_id]
            })
            
        # Add gene-disease associations
        try:
            results["disease_associations"] = await self.disgenet.get_gene_disease_associations(
                params.protein_id
            )
        except Exception as e:
            results["disease_associations"] = {"error": str(e)}
        
        return {
            "protein_id": params.protein_id,
            "mechanism_data": results,
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "mechanism_types": params.mechanism_types
            }
        }

    async def execute_tool(self, tool_call) -> Dict:
        """Execute the appropriate database function based on the tool call"""
        try:
            # Access attributes properly for ChatCompletionMessageToolCall object
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            # Core database functions
            if function_name == "search_literature":
                params = LiteratureSearchParams(**arguments)
                return await self.ncbi.search_and_analyze(
                    genes=params.genes,
                    phenotypes=params.phenotypes,
                    additional_terms=params.additional_terms,
                    max_results=params.max_results
                )

            elif function_name == "search_variants":
                params = VariantSearchParams(**arguments)
                return await self.ensembl.get_variants(
                    chromosome=params.chromosome,
                    start=params.start,
                    end=params.end,
                    species=params.species
                )

            elif function_name == "analyze_molecular_mechanisms":
                params = MolecularMechanismParams(**arguments)
                return await self.analyze_molecular_mechanisms(params)
                
            elif function_name == "analyze_genetic_variants":
                params = GeneticVariantParams(**arguments)
                return await self._execute_variant_search(params)
                
            elif function_name == "analyze_protein_interactions":
                params = ProteinInteractionParams(**arguments)
                return await self.analyze_protein_interactions(params)

            elif function_name == "analyze_pathways":
                params = PathwayAnalysisParams(**arguments)
                return await self.analyze_pathways(params)

            else:
                raise ValueError(f"Unknown function: {function_name}")

        except AttributeError as e:
            return {"error": f"Invalid tool call format: {str(e)}"}
        except Exception as e:
            return {"error": str(e)}

    def _check_interaction_confidence(self, interactions: Dict, threshold: float) -> bool:
        """Helper method to check interaction confidence scores"""
        try:
            return interactions.get("score", 0) >= threshold
        except (KeyError, TypeError):
            return False

    async def _execute_literature_search(self, arguments: Dict) -> Dict:
        """Execute literature search using NCBI"""
        params = LiteratureSearchParams(**arguments)
        return self.ncbi.search_and_analyze(
            genes=params.genes,
            phenotypes=params.phenotypes,
            additional_terms=params.additional_terms,
            max_results=params.max_results
        )

    async def _execute_variant_search(self, params: GeneticVariantParams) -> Dict:
        """Execute comprehensive genetic variant analysis"""
        try:
            # First, get gene coordinates from Ensembl
            gene_info = await self.ensembl.search(params.gene)
            if not gene_info:
                return {"error": f"Gene {params.gene} not found in Ensembl"}

            # Get variants using gene coordinates
            variants = self.ensembl.get_variants(
                chromosome=gene_info.get("seq_region_name", "1"),
                start=gene_info.get("start"),
                end=gene_info.get("end"),
                species="homo_sapiens"
            )
            
            results = {
                "gene": params.gene,
                "variants": variants,
                "clinical_data": {}
            }

            # Add pharmacogenomic data if available
            try:
                pharmgkb_data = await self.pharmgkb.get_drug_gene_relationships(params.gene)
                results["clinical_data"]["pharmgkb"] = pharmgkb_data
            except Exception as e:
                results["clinical_data"]["pharmgkb"] = {"error": str(e)}

            # Add disease associations if available
            try:
                disgenet_data = await self.disgenet.get_gene_disease_associations(params.gene)
                results["clinical_data"]["disgenet"] = disgenet_data
            except Exception as e:
                results["clinical_data"]["disgenet"] = {"error": str(e)}

            return results
        except Exception as e:
            return {"error": str(e)}

    async def _execute_gwas_search(self, arguments: Dict) -> Dict:
        """Execute GWAS search"""
        params = GWASSearchParams(**arguments)
        results = self.gwas.search(params.trait)
        if params.gene:
            results = {k: v for k, v in results.items() 
                      if params.gene.upper() in str(v.get('mapped_genes', '')).upper()}
        return results

    async def _execute_protein_info(self, arguments: Dict) -> Dict:
        """Execute protein information search using UniProt"""
        params = ProteinInfoParams(**arguments)
        results = self.uniprot.search(params.protein_id)
        if params.include_features and 'results' in results and results['results']:
            uniprot_id = results['results'][0]['id']
            features = self.uniprot.get_protein_features(uniprot_id)
            results['features'] = features
        return results