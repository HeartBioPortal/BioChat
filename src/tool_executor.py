from typing import Dict, Any
import json
from src.APIHub import NCBIEutils, EnsemblAPI, GWASCatalog, UniProtAPI
from src.schemas import LiteratureSearchParams, VariantSearchParams, GWASSearchParams, ProteinInfoParams

class ToolExecutor:
    def __init__(self, ncbi_api_key: str, tool_name: str, email: str):
        """Initialize database clients"""
        self.ncbi = NCBIEutils(api_key=ncbi_api_key, tool=tool_name, email=email)
        self.ensembl = EnsemblAPI()
        self.gwas = GWASCatalog()
        self.uniprot = UniProtAPI()

    async def execute_tool(self, tool_call: Dict) -> Dict[str, Any]:
        """Execute the appropriate database function based on the tool call"""
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)

        try:
            if function_name == "search_literature":
                return await self._execute_literature_search(arguments)
            elif function_name == "search_variants":
                return await self._execute_variant_search(arguments)
            elif function_name == "search_gwas":
                return await self._execute_gwas_search(arguments)
            elif function_name == "get_protein_info":
                return await self._execute_protein_info(arguments)
            else:
                return {"error": f"Unknown function: {function_name}"}
        except Exception as e:
            return {"error": str(e)}

    async def _execute_literature_search(self, arguments: Dict) -> Dict:
        """Execute literature search using NCBI"""
        params = LiteratureSearchParams(**arguments)
        return self.ncbi.search_and_analyze(
            genes=params.genes,
            phenotypes=params.phenotypes,
            additional_terms=params.additional_terms,
            max_results=params.max_results
        )

    async def _execute_variant_search(self, arguments: Dict) -> Dict:
        """Execute variant search using Ensembl"""
        params = VariantSearchParams(**arguments)
        return self.ensembl.get_variants(
            chromosome=params.chromosome,
            start=params.start,
            end=params.end,
            species=params.species
        )

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