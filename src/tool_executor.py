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
 StringDBEnrichmentParams, VariantSearchParams, 
    GWASSearchParams, ProteinInfoParams, PathwayAnalysisParams, GeneticVariantParams,TargetAnalysisParams, DiseaseAnalysisParams,
      PharmGKBChemicalQueryParams, PharmGKBGetChemicalParams, PharmGKBDrugLabelQueryParams, PharmGKBGetDrugLabelParams, PharmGKBPathwayQueryParams,
        PharmGKBGetPathwayParams, PharmGKBClinicalAnnotationQueryParams, PharmGKBVariantAnnotationQueryParams
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
            # self.string_db = StringDBClient()
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
                "get_biogrid_interactions": self._execute_biogrid_interactions,
                "get_string_interactions": self._execute_string_interactions,
                "get_biogrid_chemical_interactions": self._execute_biogrid_chemical_interactions,
                "get_intact_interactions": self._execute_intact_interactions,
                "analyze_pathways": self._execute_pathway_analysis,
                "analyze_target": self._execute_target_analysis,
                "analyze_disease": self._execute_disease_analysis,
                "search_chemical": self.execute_pharmgkb_search_chemical,
                "search_drug_labels": self.execute_pharmgkb_search_drug_labels,
                "search_pathway": self.execute_pharmgkb_search_pathway,
                "search_clinical_annotation": self.execute_pharmgkb_search_clinical_annotation,
                "get_variant_annotation": self.execute_pharmgkb_get_variant_annotation,
                "get_pharmgkb_annotations": self._execute_pharmgkb_annotations,
                "search_chembl": self._execute_chembl_search,
                "get_chembl_compound_details": self._execute_chembl_compound_details,
                "get_chembl_bioactivities": self._execute_chembl_bioactivities,
                "get_chembl_target_info": self._execute_chembl_target_info,
                "search_chembl_similarity": self._execute_chembl_similarity_search,
                "search_chembl_substructure": self._execute_chembl_substructure_search
            }
            
            handler = handlers.get(function_name)
            if not handler:
                raise ValueError(f"Unknown function: {function_name}")
            
            return await handler(arguments)

        except Exception as e:
            logger.error(f"Tool execution error: {str(e)}")
            return {"error": str(e)}



    async def execute_pharmgkb_search_chemical(self, arguments: Dict) -> Dict:
        """
        Execute a search for chemicals by name, handling the name-to-ID resolution.
        """
        try:
            params = PharmGKBChemicalQueryParams(**arguments)
            results = await self.pharmgkb.search_chemical_by_name(params.name)
            
            if isinstance(results, list) and results:
                # Get full details for each found chemical
                detailed_results = []
                for chemical in results:
                    if chemical.get('id'):
                        details = await self.pharmgkb.get_chemical_by_id(chemical['id'])
                        if not isinstance(details, dict) or "error" not in details:
                            detailed_results.append(details)
                
                if detailed_results:
                    return {
                        "matches": detailed_results,
                        "count": len(detailed_results)
                    }
            
            return {
                "matches": [],
                "count": 0,
                "message": f"No chemicals found matching name: {params.name}"
            }
                
        except Exception as e:
            logger.error(f"PharmGKB chemical search error: {str(e)}")
            return {"error": str(e)}

    async def execute_pharmgkb_search_drug_labels(self, arguments: Dict) -> Dict:
        """
        Execute a search for drug labels by name.
        """
        try:
            params = PharmGKBDrugLabelQueryParams(**arguments)
            results = await self.pharmgkb.search_drug_labels_by_name(params.name)
            
            if isinstance(results, list) and results:
                return {
                    "matches": results,
                    "count": len(results)
                }
                
            return {
                "matches": [],
                "count": 0,
                "message": f"No drug labels found matching name: {params.name}"
            }
                
        except Exception as e:
            logger.error(f"PharmGKB drug label search error: {str(e)}")
            return {"error": str(e)}

    async def execute_pharmgkb_search_pathway(self, arguments: Dict) -> Dict:
        """
        Execute a search for pathways by name.
        """
        try:
            params = PharmGKBPathwayQueryParams(**arguments)
            results = await self.pharmgkb.search_pathway_by_name(params.name)
            
            if isinstance(results, list) and results:
                return {
                    "matches": results,
                    "count": len(results)
                }
                
            return {
                "matches": [],
                "count": 0,
                "message": f"No pathways found matching name: {params.name}"
            }
                
        except Exception as e:
            logger.error(f"PharmGKB pathway search error: {str(e)}")
            return {"error": str(e)}

    async def _execute_pharmgkb_annotations(self, arguments: Dict) -> Dict:
        """Execute PharmGKB annotation search with error handling."""
        try:
            if not self.pharmgkb:
                raise ValueError("PharmGKB client not initialized")

            # Extract query parameters from arguments
            gene_id = arguments.get('gene_id')
            if not gene_id:
                raise ValueError("gene_id is required for PharmGKB annotation search")

            # First, search for clinical annotations
            clinical_annotations = await self.pharmgkb.search_clinical_annotation({
                "view": "base"
            })

            # Filter annotations for the specific gene
            filtered_annotations = []
            for annotation in clinical_annotations.get('data', []):
                if gene_id.upper() in [g.upper() for g in annotation.get('genes', [])]:
                    filtered_annotations.append(annotation)

            # Organize results
            results = {
                "clinical_annotations": filtered_annotations,
                "metadata": {
                    "gene_id": gene_id,
                    "timestamp": datetime.now().isoformat(),
                    "source": "PharmGKB",
                    "total_annotations": len(filtered_annotations)
                }
            }

            # Save full API response
            file_path = self.save_api_response("pharmgkb_annotations", results)
            logger.info(f"Full PharmGKB annotation response saved to {file_path}")

            return results

        except Exception as e:
            logger.error(f"PharmGKB annotation error: {str(e)}")
            return {"error": str(e)}
    
    async def execute_pharmgkb_search_clinical_annotation(self, arguments: Dict) -> Dict:
        """
        Execute a query for clinical annotations.
        Note: Filtering must be done client-side as the API does not support filtering by chemical/gene.
        """
        try:
            params = PharmGKBClinicalAnnotationQueryParams(**arguments)
            return await self.pharmgkb.search_clinical_annotation(params.dict())
        except Exception as e:
            logger.error(f"PharmGKB search clinical annotation error: {str(e)}")
            return {"error": str(e)}

    async def execute_pharmgkb_get_variant_annotation(self, arguments: Dict) -> Dict:
        """
        Execute retrieval of a variant annotation by its PharmGKB ID.
        """
        try:
            params = PharmGKBVariantAnnotationQueryParams(**arguments)
            return await self.pharmgkb.get_variant_annotation(params.pharmgkb_id, view=params.view)
        except Exception as e:
            logger.error(f"PharmGKB get variant annotation error: {str(e)}")
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
        """Execute BioGRID chemical interaction search with improved processing."""
        try:
            params = BioGridChemicalParams(**arguments)
            if not params.chemical_list:
                error = "No chemicals provided for search"
                BioChatLogger.log_error("BioGRID validation error", Exception(error))
                return {
                    "success": False,
                    "error": error
                }
                
            results = await self.biogrid.get_chemical_interactions(params.chemical_list)
            
            if results.get("success"):
                # Process and format the chemical interaction data
                interactions = results.get("data", {})
                metadata = results.get("metadata", {})
                
                # Create a more useful summary
                summary = {
                    "chemicals_searched": params.chemical_list,
                    "chemicals_found": metadata.get("chemicals_found", 0),
                    "total_interactions": results.get("interaction_count", 0),
                    "protein_targets": metadata.get("protein_targets", 0),
                    "experiment_types": metadata.get("experiment_types", []),
                    "top_interactions": []
                }
                
                # Add top interactions (limit to 5 for readability)
                for interaction_id, interaction in list(interactions.items())[:5]:
                    summary["top_interactions"].append({
                        "chemical": interaction.get("chemical_name"),
                        "target": interaction.get("protein_target"),
                        "type": interaction.get("interaction_type"),
                        "evidence": interaction.get("interaction_evidence"),
                        "publication": f"{interaction.get('publication')} (PMID:{interaction.get('pubmed_id')})"
                    })
                
                # Save full response but return summary
                file_path = self.save_api_response("biogrid_chemicals", results)
                
                return {
                    "success": True,
                    "summary": summary,
                    "full_data_path": file_path,
                    "message": f"Found {summary['total_interactions']} chemical-protein interactions. Full data saved to {file_path}"
                }
                
            return results
            
        except Exception as e:
            BioChatLogger.log_error("BioGRID chemical interaction execution error", e)
            return {
                "error": str(e),
                "chemical_list": params.chemical_list if params else arguments.get("chemical_list", [])
            }

    async def _execute_intact_interactions(self, arguments: Dict) -> Dict:
        """Execute IntAct interaction search with improved chemical handling."""
        try:
            params = IntActSearchParams(**arguments)
            results = await self.intact.search(
                query=params.query,
                negative_filter=params.negative_filter,
                page=params.page,
                page_size=params.page_size
            )
            
            # If direct search fails, try faceted search
            if "error" in results:
                facet_results = await self.intact.get_interaction_facets(params.query)
                if not "error" in facet_results:
                    results = facet_results
            
            # Save response if successful
            if results.get("success"):
                file_path = self.save_api_response("intact_interactions", results)
                results["download_url"] = file_path
                
            return results
            
        except Exception as e:
            logger.error(f"IntAct interaction error: {str(e)}")
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
        try:
            params = PathwayAnalysisParams(**arguments)
            results = {}
            
            # Check if genes parameter is provided
            if params.genes and isinstance(params.genes, list):
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
            # Check if gene_id parameter is provided
            elif params.gene_id:
                gene = params.gene_id
                BioChatLogger.log_info(f"Analyzing pathway for single gene: {gene}")
                try:
                    pathways = await self.reactome.get_pathways_for_gene(gene)
                    
                    if isinstance(pathways, dict) and "error" in pathways:
                        results[gene] = {
                            "status": "error",
                            "message": pathways['error']
                        }
                    elif pathways:
                        results[gene] = {
                            "status": "success",
                            "pathways": pathways,
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
            # Check if pathway_id parameter is provided
            elif params.pathway_id:
                pathway_id = params.pathway_id
                BioChatLogger.log_info(f"Getting details for pathway: {pathway_id}")
                try:
                    pathway_details = await self.reactome.get_pathway_details(pathway_id)
                    if pathway_details:
                        results["pathway_details"] = {
                            "status": "success",
                            "pathway_id": pathway_id,
                            "details": pathway_details,
                            "source": "Reactome Database",
                            "last_updated": datetime.now().isoformat()
                        }
                    else:
                        results["pathway_details"] = {
                            "status": "no_data",
                            "pathway_id": pathway_id,
                            "message": "No details found for pathway"
                        }
                except Exception as e:
                    logger.error(f"Error getting details for pathway {pathway_id}: {str(e)}")
                    results["pathway_details"] = {
                        "status": "error",
                        "pathway_id": pathway_id,
                        "message": str(e)
                    }
            else:
                # No valid parameters provided
                return {
                    "status": "error",
                    "message": "No valid parameters provided. Please specify genes, gene_id, or pathway_id."
                }
                
            return results
            
        except Exception as e:
            BioChatLogger.log_error("Pathway analysis error", e)
            return {
                "status": "error",
                "message": f"Pathway analysis failed: {str(e)}",
                "parameters": arguments
            }

    async def _execute_chembl_search(self, arguments: dict) -> dict:
        """
        Execute a ChEMBL compound search.
        """
        try:
            from src.schemas import ChemblSearchParams
            params = ChemblSearchParams(**arguments)
            from src.APIHub import ChemblAPI
            chembl_client = ChemblAPI()
            
            BioChatLogger.log_info(f"Executing ChEMBL search for query: {params.query}")
            results = await chembl_client.search(params.query)
            
            # Save API response
            file_path = self.save_api_response("chembl_search", results)
            BioChatLogger.log_info(f"ChEMBL search results saved to {file_path}")
            
            return results
        except Exception as e:
            BioChatLogger.log_error("ChEMBL search execution error", e)
            return {"error": str(e), "query": arguments.get("query", "")}

    async def _execute_chembl_compound_details(self, arguments: dict) -> dict:
        """
        Retrieve detailed compound information from ChEMBL.
        """
        try:
            from src.schemas import ChemblCompoundDetailsParams
            params = ChemblCompoundDetailsParams(**arguments)
            from src.APIHub import ChemblAPI
            chembl_client = ChemblAPI()
            
            BioChatLogger.log_info(f"Executing ChEMBL compound details for ID: {params.molecule_chembl_id}")
            results = await chembl_client.get_compound_details(params.molecule_chembl_id)
            
            # Save API response
            file_path = self.save_api_response("chembl_compound", results)
            BioChatLogger.log_info(f"ChEMBL compound details saved to {file_path}")
            
            return results
        except Exception as e:
            BioChatLogger.log_error("ChEMBL compound details execution error", e)
            return {"error": str(e), "molecule_chembl_id": arguments.get("molecule_chembl_id", "")}

    async def _execute_chembl_bioactivities(self, arguments: dict) -> dict:
        """
        Retrieve bioactivity data from ChEMBL.
        """
        try:
            from src.schemas import ChemblBioactivitiesParams
            params = ChemblBioactivitiesParams(**arguments)
            from src.APIHub import ChemblAPI
            chembl_client = ChemblAPI()
            
            BioChatLogger.log_info(f"Executing ChEMBL bioactivities for ID: {params.molecule_chembl_id} (limit: {params.limit})")
            results = await chembl_client.get_bioactivities(params.molecule_chembl_id, limit=params.limit)
            
            # Save API response
            file_path = self.save_api_response("chembl_bioactivities", results)
            BioChatLogger.log_info(f"ChEMBL bioactivities data saved to {file_path}")
            
            return results
        except Exception as e:
            BioChatLogger.log_error("ChEMBL bioactivities execution error", e)
            return {"error": str(e), "molecule_chembl_id": arguments.get("molecule_chembl_id", "")}

    async def _execute_chembl_target_info(self, arguments: dict) -> dict:
        """
        Retrieve target information from ChEMBL.
        """
        try:
            from src.schemas import ChemblTargetInfoParams
            params = ChemblTargetInfoParams(**arguments)
            from src.APIHub import ChemblAPI
            chembl_client = ChemblAPI()
            
            BioChatLogger.log_info(f"Executing ChEMBL target info for ID: {params.target_chembl_id}")
            results = await chembl_client.get_target_info(params.target_chembl_id)
            
            # Save API response
            file_path = self.save_api_response("chembl_target", results)
            BioChatLogger.log_info(f"ChEMBL target information saved to {file_path}")
            
            return results
        except Exception as e:
            BioChatLogger.log_error("ChEMBL target info execution error", e)
            return {"error": str(e), "target_chembl_id": arguments.get("target_chembl_id", "")}
    
    async def _execute_chembl_similarity_search(self, arguments: dict) -> dict:
        """
        Execute a ChEMBL structural similarity search.
        """
        try:
            from src.schemas import ChemblSimilaritySearchParams
            params = ChemblSimilaritySearchParams(**arguments)
            from src.APIHub import ChemblAPI
            chembl_client = ChemblAPI()
            
            BioChatLogger.log_info(f"Executing ChEMBL similarity search for SMILES: {params.smiles[:20]}... (similarity: {params.similarity})")
            results = await chembl_client.search_by_similarity(
                smiles=params.smiles,
                similarity=params.similarity,
                limit=params.limit
            )
            
            # Save API response
            file_path = self.save_api_response("chembl_similarity", results)
            BioChatLogger.log_info(f"ChEMBL similarity search results saved to {file_path}")
            
            return results
        except Exception as e:
            BioChatLogger.log_error("ChEMBL similarity search execution error", e)
            return {"error": str(e), "smiles": arguments.get("smiles", "")[:20] + "..."}
    
    async def _execute_chembl_substructure_search(self, arguments: dict) -> dict:
        """
        Execute a ChEMBL substructure search.
        """
        try:
            from src.schemas import ChemblSubstructureSearchParams
            params = ChemblSubstructureSearchParams(**arguments)
            from src.APIHub import ChemblAPI
            chembl_client = ChemblAPI()
            
            BioChatLogger.log_info(f"Executing ChEMBL substructure search for SMILES: {params.smiles[:20]}...")
            results = await chembl_client.search_by_substructure(
                smiles=params.smiles,
                limit=params.limit
            )
            
            # Save API response
            file_path = self.save_api_response("chembl_substructure", results)
            BioChatLogger.log_info(f"ChEMBL substructure search results saved to {file_path}")
            
            return results
        except Exception as e:
            BioChatLogger.log_error("ChEMBL substructure search execution error", e)
            return {"error": str(e), "smiles": arguments.get("smiles", "")[:20] + "..."}

    async def _execute_target_analysis(self, arguments: Dict) -> Dict:
        """Execute comprehensive target analysis using Open Targets with better error handling"""
        try:
            params = TargetAnalysisParams(**arguments)
            
            # Get target info with all necessary data in a single query
            target_response = await self.open_targets.get_target_info(params.target_id)
            
            # Early return if there's an error
            if "error" in target_response:
                BioChatLogger.log_error(f"Failed to get target info: {target_response['error']}")
                return target_response
                
            target_data = target_response.get('target', {})
            if not target_data:
                return {"error": "No target data found", "target_id": params.target_id}
            
            # Extract and structure the data
            drugs_data = target_data.get('knownDrugs', {})
            safety_data = target_data.get('safetyEffects', [])
            
            structured_response = {
                "target_id": params.target_id,
                "target_info": {
                    "name": target_data.get('approvedName'),
                    "symbol": target_data.get('approvedSymbol'),
                    "biotype": target_data.get('biotype')
                },
                "drug_data": {
                    "count": drugs_data.get('count', 0),
                    "drugs": [
                        {
                            "name": drug.get('drug', {}).get('name'),
                            "phase": drug.get('phase'),
                            "status": drug.get('status'),
                            "mechanism": drug.get('mechanismOfAction'),
                            "disease": drug.get('disease', {}).get('name'),
                            "type": drug.get('drug', {}).get('drugType')
                        }
                        for drug in drugs_data.get('rows', [])
                    ]
                },
                "safety_data": [
                    {
                        "event": effect.get('event'),
                        "effects": effect.get('effects', [])
                    }
                    for effect in safety_data
                ]
            }
            
            # Save complete response
            file_path = self.save_api_response("opentargets_target", structured_response)
            BioChatLogger.log_info(f"Saved OpenTargets response to {file_path}")
            
            return {
                "success": True,
                "data": structured_response,
                "file_path": file_path
            }
            
        except Exception as e:
            BioChatLogger.log_error("Target analysis error", e)
            return {
                "error": str(e),
                "target_id": params.target_id if params else arguments.get("target_id")
            }
    
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