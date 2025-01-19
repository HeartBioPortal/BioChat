from typing import Dict, Any
from datetime import datetime
import json
import logging
from src.APIHub import (
    NCBIEutils, EnsemblAPI, GWASCatalog, UniProtAPI,
    StringDBClient, ReactomeClient, PharmGKBClient,
    IntActClient, BioCyc, BioGridClient, OpenTargetsClient
)
from src.schemas import (
    LiteratureSearchParams, VariantSearchParams, GWASSearchParams, ProteinInfoParams,
    ProteinInteractionParams, PathwayAnalysisParams, MolecularMechanismParams, GeneticVariantParams,TargetAnalysisParams, DiseaseAnalysisParams
)

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class ToolExecutor:
    def __init__(self, ncbi_api_key: str, tool_name: str, email: str, biogrid_access_key: str = None):
        """Initialize database clients with appropriate credentials"""
        # Initialize core clients with error handling
        try:
            # Core APIs (required)
            self.ncbi = NCBIEutils(api_key=ncbi_api_key, tool=tool_name, email=email)
            self.ensembl = EnsemblAPI()
            self.gwas = GWASCatalog()
            self.uniprot = UniProtAPI()
            
            # Optional APIs (initialized based on available credentials)
            self.string_db = StringDBClient() if biogrid_access_key else None
            self.reactome = ReactomeClient()
            self.intact = IntActClient()
            self.pharmgkb = PharmGKBClient()
            self.biocyc = BioCyc()
            self.biogrid = BioGridClient(access_key=biogrid_access_key) if biogrid_access_key else None
            self.open_targets = OpenTargetsClient()

            logger.info("Tool executor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize tool executor: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to initialize services: {str(e)}")

    async def execute_tool(self, tool_call) -> Dict:
        """Execute the appropriate database function based on the tool call"""
        try:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            
            logger.info(f"Executing tool: {function_name}")
            
            # Map function names to their handlers
            handlers = {
                "search_literature": self._execute_literature_search,
                "search_variants": self._execute_variant_search,
                "search_gwas": self._execute_gwas_search,
                "get_protein_info": self._execute_protein_info,
                "analyze_protein_interactions": self._execute_protein_interactions,
                "analyze_pathways": self._execute_pathway_analysis,
                "analyze_molecular_mechanisms": self._execute_molecular_mechanisms,
                "analyze_genetic_variants": self._execute_genetic_variant_analysis,
                "analyze_target": self._execute_target_analysis,
                "analyze_disease": self._execute_disease_analysis
            }
            
            handler = handlers.get(function_name)
            if not handler:
                raise ValueError(f"Unknown function: {function_name}")
            
            result = await handler(arguments)
            return result

        except json.JSONDecodeError:
            logger.error("Failed to parse tool arguments", exc_info=True)
            return {"error": "Invalid arguments format"}
        except Exception as e:
            logger.error(f"Tool execution error: {str(e)}", exc_info=True)
            return {"error": str(e)}

    async def _execute_literature_search(self, arguments: Dict) -> Dict:
        """Execute literature search using NCBI"""
        try:
            params = LiteratureSearchParams(**arguments)
            return await self.ncbi.search_and_analyze(
                genes=params.genes,
                phenotypes=params.phenotypes,
                additional_terms=params.additional_terms,
                max_results=params.max_results
            )
        except Exception as e:
            logger.error(f"Literature search error: {str(e)}", exc_info=True)
            return {"error": f"Literature search failed: {str(e)}"}

    async def _execute_variant_search(self, arguments: Dict) -> Dict:
        """Execute variant search using Ensembl"""
        try:
            params = VariantSearchParams(**arguments)
            return await self.ensembl.get_variants(
                chromosome=params.chromosome,
                start=params.start,
                end=params.end,
                species=params.species
            )
        except Exception as e:
            logger.error(f"Variant search error: {str(e)}", exc_info=True)
            return {"error": f"Variant search failed: {str(e)}"}

    async def _execute_gwas_search(self, arguments: Dict) -> Dict:
        """Execute GWAS search"""
        try:
            params = GWASSearchParams(**arguments)
            results = await self.gwas.search(params.trait)
            if params.gene:
                results = {k: v for k, v in results.items() 
                          if params.gene.upper() in str(v.get('mapped_genes', '')).upper()}
            return results
        except Exception as e:
            logger.error(f"GWAS search error: {str(e)}", exc_info=True)
            return {"error": f"GWAS search failed: {str(e)}"}

    async def _execute_protein_info(self, arguments: Dict) -> Dict:
        """Execute protein information search using UniProt"""
        try:
            params = ProteinInfoParams(**arguments)
            results = await self.uniprot.search(params.protein_id)
            
            if 'error' in results:
                return results

            if not results.get('results'):
                return {"error": f"No results found for protein {params.protein_id}"}

            protein_data = results['results'][0]  # Get first result
            response = {
                "protein_id": params.protein_id,
                "found_id": protein_data.get('id'),
                "protein_name": protein_data.get('protein_name'),
                "gene_names": protein_data.get('gene_names', []),
                "organism": protein_data.get('organism')
            }

            # Get additional features if requested
            if params.include_features and protein_data.get('id'):
                try:
                    features = await self.uniprot.get_protein_features(protein_data['id'])
                    response["features"] = features
                except Exception as e:
                    logger.warning(f"Failed to get protein features: {str(e)}")
                    response["features_error"] = str(e)

            return response

        except Exception as e:
            logger.error(f"Protein info error: {str(e)}")
            return {"error": str(e)}

    async def _execute_protein_interactions(self, arguments: Dict) -> Dict:
        """Execute protein interaction analysis"""
        try:
            params = ProteinInteractionParams(**arguments)
            if not self.string_db or not self.biogrid:
                return {"error": "Protein interaction services not available"}
            
            results = {
                "protein_id": params.protein_id,
                "interactions": {}
            }
            
            try:
                results["interactions"]["string_db"] = await self.string_db.get_interactions(
                    protein_id=params.protein_id,
                    confidence_score=params.confidence_score
                )
            except Exception as e:
                logger.warning(f"STRING-DB query failed: {str(e)}")
                results["interactions"]["string_db"] = {"error": str(e)}

            try:
                results["interactions"]["biogrid"] = await self.biogrid.get_interactions(
                    protein_id=params.protein_id,
                    max_results=params.max_interactions
                )
            except Exception as e:
                logger.warning(f"BioGRID query failed: {str(e)}")
                results["interactions"]["biogrid"] = {"error": str(e)}

            return results
            
        except Exception as e:
            logger.error(f"Protein interaction analysis error: {str(e)}", exc_info=True)
            return {"error": f"Interaction analysis failed: {str(e)}"}

    async def _execute_pathway_analysis(self, arguments: Dict) -> Dict:
        """Execute pathway analysis using Reactome"""
        try:
            params = PathwayAnalysisParams(**arguments)
            results = {}
            
            if params.genes:
                for gene in params.genes:
                    try:
                        # Get pathways for gene
                        pathways = await self.reactome.get_pathways_for_gene(gene)
                        
                        if isinstance(pathways, dict) and "error" in pathways:
                            logger.warning(f"Could not get pathways for gene {gene}: {pathways['error']}")
                            results[gene] = {
                                "status": "error",
                                "message": pathways['error']
                            }
                            continue
                            
                        if pathways:
                            results[gene] = {
                                "status": "success",
                                "pathways": pathways
                            }
                            
                            if params.include_participants and "pathways" in pathways:
                                pathway_details = []
                                for pathway in pathways["pathways"][:5]:
                                    try:
                                        details = await self.reactome.get_pathway_details(pathway["stId"])
                                        if params.include_hierarchy:
                                            hierarchy = await self.reactome.get_pathway_hierarchy(pathway["stId"])
                                            details["hierarchy"] = hierarchy
                                        pathway_details.append(details)
                                    except Exception as e:
                                        logger.warning(f"Error getting details for pathway {pathway['stId']}: {str(e)}")
                                        continue
                                results[gene]["pathway_details"] = pathway_details
                        else:
                            results[gene] = {
                                "status": "no_data",
                                "message": "No pathways found"
                            }
                            
                    except Exception as e:
                        logger.error(f"Error processing gene {gene}: {str(e)}")
                        results[gene] = {
                            "status": "error",
                            "message": str(e)
                        }
            
            return results

        except Exception as e:
            logger.error(f"Pathway analysis error: {str(e)}")
            return {"error": f"Pathway analysis failed: {str(e)}"}
        

    async def _execute_molecular_mechanisms(self, arguments: Dict) -> Dict:
        """Execute molecular mechanism analysis"""
        try:
            params = MolecularMechanismParams(**arguments)
            
            # Get protein info
            protein_info = await self._execute_protein_info({"protein_id": params.protein_id})
            
            # Get pathway data if requested
            pathway_data = {}
            if params.include_pathways:
                pathway_data = await self._execute_pathway_analysis({
                    "genes": [params.protein_id],
                    "include_hierarchy": True,
                    "include_participants": True
                })

            results = {
                "protein_id": params.protein_id,
                "timestamp": datetime.now().isoformat(),
                "mechanism_types": params.mechanism_types,
                "data": {
                    "protein_info": protein_info,
                    "pathway_data": pathway_data
                }
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Molecular mechanism analysis error: {str(e)}")
            return {"error": f"Mechanism analysis failed: {str(e)}"}


    async def _execute_genetic_variant_analysis(self, arguments: Dict) -> Dict:
        """Execute genetic variant analysis"""
        try:
            params = GeneticVariantParams(**arguments)
            
            # Get basic variant data from Ensembl
            gene_info = await self.ensembl.search(params.gene)
            if not gene_info:
                return {"error": f"Gene {params.gene} not found in Ensembl"}

            variants = await self.ensembl.get_variants(
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
                if self.pharmgkb:
                    pharmgkb_data = await self.pharmgkb.get_drug_gene_relationships(params.gene)
                    results["clinical_data"]["pharmgkb"] = pharmgkb_data
            except Exception as e:
                logger.warning(f"PharmGKB query failed: {str(e)}")
                results["clinical_data"]["pharmgkb"] = {"error": str(e)}

            return results
            
        except Exception as e:
            logger.error(f"Genetic variant analysis error: {str(e)}", exc_info=True)
            return {"error": f"Variant analysis failed: {str(e)}"}


    async def _execute_target_analysis(self, arguments: Dict) -> Dict:
            """Execute comprehensive target analysis using Open Targets"""
            params = TargetAnalysisParams(**arguments)
            try:
                # Get basic target information
                target_info = await self.open_targets.get_target_info(params.target_id)
                
                results = {
                    "target_info": target_info,
                    "associations": await self.open_targets.get_target_disease_associations(
                        target_id=params.target_id,
                        score_min=params.min_association_score
                    )
                }
                
                # Add optional information
                if params.include_safety:
                    results["safety"] = await self.open_targets.get_target_safety(params.target_id)
                    
                if params.include_drugs:
                    results["drugs"] = await self.open_targets.get_known_drugs(params.target_id)
                    
                if params.include_expression:
                    results["expression"] = await self.open_targets.get_target_expression(params.target_id)
                
                return results
                
            except Exception as e:
                logger.error(f"Target analysis error: {e}")
                return {"error": f"Target analysis failed: {str(e)}"}

    async def _execute_disease_analysis(self, arguments: Dict) -> Dict:
        """Execute comprehensive disease analysis using Open Targets"""
        params = DiseaseAnalysisParams(**arguments)
        try:
            # Get basic disease information
            disease_info = await self.open_targets.get_disease_info(params.disease_id)
            
            results = {
                "disease_info": disease_info
            }
            
            if params.include_targets:
                results["target_associations"] = await self.open_targets.get_target_disease_associations(
                    disease_id=params.disease_id,
                    score_min=params.min_association_score
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Disease analysis error: {e}")
            return {"error": f"Disease analysis failed: {str(e)}"}
