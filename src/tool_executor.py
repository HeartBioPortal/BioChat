from typing import Dict, Any
from datetime import datetime
import json
import logging
import os
from src.utils.biochat_api_logging import BioChatLogger
from src.APIHub import (
    NCBIEutils, EnsemblAPI, GWASCatalog, UniProtAPI,
    StringDBClient, ReactomeClient, PharmGKBClient,
    IntActClient, BioCyc, BioGridClient, OpenTargetsClient
)
from src.schemas import (
    BioGridChemicalParams, BioGridInteractionParams, IntActSearchParams, LiteratureSearchParams, 
    PharmGKBClinicalParams, PharmGKBVariantParams, StringDBEnrichmentParams, VariantSearchParams, 
    GWASSearchParams, ProteinInfoParams, PathwayAnalysisParams, GeneticVariantParams,TargetAnalysisParams, DiseaseAnalysisParams
)

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("biochat_api.log", mode="a"),  # ✅ Ensure the log file stays open
                logging.StreamHandler()
            ]
        )


API_RESULTS_DIR = "api_results"
os.makedirs(API_RESULTS_DIR, exist_ok=True)



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

            BioChatLogger.log_info("Tool executor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize tool executor: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to initialize services: {str(e)}")




    def save_api_response(self, api_name: str, response: dict) -> str:
        """Save the full API response to a file and return the file path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{api_name}_response_{timestamp}.json"
        filepath = os.path.join(API_RESULTS_DIR, filename)
        
        with open(filepath, "w") as file:
            json.dump(response, file, indent=4)
        
        logger.info(f"Full API response for {api_name} saved at {filepath}")
        return filepath

    async def execute_tool(self, tool_call) -> Dict:
        """Execute the appropriate database function based on the tool call"""
        try:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            
            BioChatLogger.log_info(f"Executing tool: {function_name}")
            
            handlers = {
                "search_literature": self._execute_literature_search,
                "search_variants": self._execute_variant_search,
                "search_gwas": self._execute_gwas_search,
                "get_protein_info": self._execute_protein_info,
                "get_string_interactions": self._execute_string_interactions,
                "get_biogrid_interactions": self._execute_biogrid_interactions,
                "get_biogrid_chemical_interactions": self._execute_biogrid_chemical_interactions,
                "get_intact_interactions": self._execute_intact_interactions,
                "analyze_pathways": self._execute_pathway_analysis,
                "get_pharmgkb_annotations": self._execute_pharmgkb_annotations,
                "get_pharmgkb_variants": self._execute_pharmgkb_variants,
                "analyze_target": self._execute_target_analysis,
                "analyze_disease": self._execute_disease_analysis
            }
            
            handler = handlers.get(function_name)
            if not handler:
                raise ValueError(f"Unknown function: {function_name}")
            
            return await handler(arguments)

        except Exception as e:
            logger.error(f"Tool execution error: {str(e)}")
            return {"error": str(e)}

    async def _execute_string_interactions(self, arguments: Dict) -> Dict:
        """Execute STRING-DB interaction analysis with optimized filtering."""
        try:
            params = StringDBEnrichmentParams(**arguments)
            raw_results = await self.string_db.get_interaction_partners(
                identifiers=params.identifiers,
                species=params.species
            )

            # ✅ Keep only high-confidence interactions (score > 0.8) and limit to top 10
            relevant_interactions = sorted(
                [entry for entry in raw_results if entry.get("score", 0) > 0.8], 
                key=lambda x: x["score"], 
                reverse=True
            )[:10]  # Keep only top 10 high-confidence interactions

            # ✅ Save full API response in a temp file for download
            file_path = self.save_api_response("stringdb", raw_results)

            logger.info(f"Full STRING-DB API response saved to {file_path}")

            return {
                "top_interactions": relevant_interactions,
                "download_url": file_path  # Provide a download link for full data
            }

        except Exception as e:
            logger.error(f"STRING-DB interaction error: {str(e)}")
            return {"error": str(e)}


    async def _execute_biogrid_interactions(self, arguments: Dict) -> Dict:
        """Execute BioGRID interaction analysis with optimized filtering."""
        try:
            params = BioGridInteractionParams(**arguments)
            raw_results = await self.biogrid.get_core_interactions(
                gene_list=params.gene_list,
                include_interactors=params.include_interactors,
                tax_id=params.tax_id
            )

            # ✅ Keep only interactions related to queried genes with highest confidence scores
            relevant_interactions = sorted(
                [entry for entry in raw_results if entry.get("score", 0) > 0.7], 
                key=lambda x: x["score"], 
                reverse=True
            )[:10]  # Limit to top 10 interactions

            # ✅ Save full API response in a temp file for download
            file_path = self.save_api_response("biogrid", raw_results)

            logger.info(f"Full BioGRID API response saved to {file_path}")

            return {
                "top_interactions": relevant_interactions,
                "download_url": file_path  # Provide a link for users to download full data
            }

        except Exception as e:
            logger.error(f"BioGRID interaction error: {str(e)}")
            return {"error": str(e)}


    async def _execute_biogrid_chemical_interactions(self, arguments: Dict) -> Dict:
        """Execute BioGRID chemical interaction analysis"""
        try:
            params = BioGridChemicalParams(**arguments)
            return await self.biogrid.get_chemical_interactions(
                gene_list=params.gene_list,
                chemical_list=params.chemical_list,
                evidence_list=params.evidence_list
            )
        except Exception as e:
            logger.error(f"BioGRID chemical interaction error: {str(e)}")
            return {"error": str(e)}

    async def _execute_intact_interactions(self, arguments: Dict) -> Dict:
        """Execute IntAct interaction search"""
        try:
            params = IntActSearchParams(**arguments)
            return await self.intact.search(
                query=params.query,
                species=params.species,
                negative_filter=params.negative_filter,
                page=params.page,
                page_size=params.page_size
            )
        except Exception as e:
            logger.error(f"IntAct search error: {str(e)}")
            return {"error": str(e)}

    async def _execute_pharmgkb_annotations(self, arguments: Dict) -> Dict:
        """Execute PharmGKB clinical annotation search"""
        try:
            params = PharmGKBClinicalParams(**arguments)
            return await self.pharmgkb.get_clinical_annotations(
                drug_id=params.drug_id,
                gene_id=params.gene_id
            )
        except Exception as e:
            logger.error(f"PharmGKB annotation error: {str(e)}")
            return {"error": str(e)}

    async def _execute_pharmgkb_variants(self, arguments: Dict) -> Dict:
        """Execute PharmGKB variant annotation search"""
        try:
            params = PharmGKBVariantParams(**arguments)
            return await self.pharmgkb.get_variant_annotations(
                variant_id=params.variant_id,
                drug_id=params.drug_id
            )
        except Exception as e:
            logger.error(f"PharmGKB variant error: {str(e)}")
            return {"error": str(e)}
        
    async def _execute_literature_search(self, arguments: Dict) -> Dict:
        """Execute literature search using NCBI"""
        try:
            params = LiteratureSearchParams(**arguments)
            results = await self.ncbi.search_and_analyze(
                genes=params.genes,
                phenotypes=params.phenotypes,
                additional_terms=params.additional_terms,
                max_results=params.max_results
            )
            
            # Add metadata for citation
            results["metadata"] = {
                "source": "NCBI PubMed",
                "query_date": datetime.now().isoformat(),
                "database_version": "2024",
                "citation_format": "PMID: [id]"
            }

            # ✅ Save full API response in a temp file for download
            file_path = self.save_api_response("pubmed", results)

            return results
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
            
            file_path = self.save_api_response("gwas", results)
            return results
        except Exception as e:

            logger.error(f"GWAS search error: {str(e)} result was {results}", exc_info=True)
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

            file_path = self.save_api_response("uniprot", response)
            return response

        except Exception as e:
            logger.error(f"Protein info error: {str(e)}")
            return {"error": str(e)}

    async def _execute_pathway_analysis(self, arguments: Dict) -> Dict:
        """Execute pathway analysis using Reactome"""

        params = PathwayAnalysisParams(**arguments)
        results = {}
        
        if params.genes:
            BioChatLogger.log_info(f"Analyzing pathways for genes: {params.genes}")
            for gene in params.genes:
                try:
                    # Get pathways for gene
                    BioChatLogger.log_info(f"Getting pathways for gene: {gene}")
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
                            "pathways": pathways,
                            "evidence_strength": "high/medium/low",
                            "source": "Reactome Database",
                            "last_updated": datetime.now().isoformat()
                        }
                        
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
        try:
            params = DiseaseAnalysisParams(**arguments)
            disease_info = await self.open_targets.get_disease_info(params.disease_id)
            
            # Cross-reference with literature
            literature = await self._execute_literature_search({
                "phenotypes": [disease_info.get("name")],
                "max_results": 5
            })
            
            # Cross-reference with pathways
            related_genes = disease_info.get("associated_genes", [])
            pathways = await self._execute_pathway_analysis({
                "genes": related_genes[:5]  # Top 5 associated genes
            })
            
            results = {
                "disease_info": disease_info,
                "supporting_literature": literature,
                "pathway_analysis": pathways,
                "metadata": {
                    "sources": ["Open Targets", "PubMed", "Reactome"],
                    "analysis_date": datetime.now().isoformat(),
                    "confidence_score": "Calculate based on evidence convergence"
                }
            }
            
            return results

        except Exception as e:
                logger.error(f"Target analysis error: {e}")
                return {"error": f"Target analysis failed: {str(e)}"}

    async def aggregate_gene_disease_evidence(self, gene: str, disease: str) -> Dict:
        """Comprehensive evidence gathering across all databases"""
        results = {
            "literature": await self._execute_literature_search({
                "genes": [gene],
                "phenotypes": [disease]
            }),
            "molecular": await self._execute_protein_info({"protein_id": gene}),
            "pathways": await self._execute_pathway_analysis({"genes": [gene]}),
            "variants": await self._execute_variant_search({"gene": gene}),
            "clinical": await self._execute_pharmgkb_annotations({
                "gene_id": gene
            })
        }
        
        # Add confidence scoring
        results["evidence_summary"] = {
            "confidence_score": self._calculate_confidence(results),
            "evidence_types": list(results.keys()),
            "source_databases": ["PubMed", "UniProt", "Reactome", "PharmGKB"],
            "analysis_date": datetime.now().isoformat()
        }
        
        return results