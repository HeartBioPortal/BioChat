"""
Module for intelligent query analysis, entity recognition, and database routing.
Combines query classification with knowledge graph principles to optimize database selection.
"""

import json
import logging
from typing import Dict, List, Tuple, Any, Optional, Set
from enum import Enum
from openai import AsyncOpenAI
from src.utils.biochat_api_logging import BioChatLogger

class QueryIntent(str, Enum):
    """Types of biological query intents"""
    EXPLANATION = "explanation"       # Explain how/why something works
    PREDICTION = "prediction"         # Predict outcomes or behaviors
    COMPARISON = "comparison"         # Compare entities or processes
    IDENTIFICATION = "identification" # Identify or characterize entities
    MECHANISM = "mechanism"           # Describe biological mechanisms
    TREATMENT = "treatment"           # Queries about treatments or interventions
    DIAGNOSIS = "diagnosis"           # Queries about disease diagnosis
    UNKNOWN = "unknown"               # Unclear intent

class EntityType(str, Enum):
    """Types of biological entities"""
    GENE = "gene"
    PROTEIN = "protein"
    PATHWAY = "pathway"
    DISEASE = "disease"
    DRUG = "drug"
    VARIANT = "variant"
    CELL_TYPE = "cell_type"
    TISSUE = "tissue"
    PHENOTYPE = "phenotype"
    ORGANISM = "organism"
    CHEMICAL = "chemical"
    UNKNOWN = "unknown"

class RelationshipType(str, Enum):
    """Types of relationships between biological entities"""
    CAUSAL = "causal"               # Direct cause-effect relationship
    ASSOCIATIVE = "associative"     # Statistical association
    REGULATORY = "regulatory"       # Regulation (activation/inhibition)
    STRUCTURAL = "structural"       # Physical or structural relationship
    FUNCTIONAL = "functional"       # Functional relationship
    UNKNOWN = "unknown"             # Unclear relationship

class DatabasePriority(str, Enum):
    """Priority levels for databases"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    FALLBACK = "fallback"

# Entity-relationship to database mapping
# Maps pairs of entity types to database priorities
ENTITY_DB_MAPPING = {
    # Gene relationships
    (EntityType.GENE, EntityType.PATHWAY): [
        ("analyze_pathways", DatabasePriority.CRITICAL),
        ("search_literature", DatabasePriority.HIGH)
    ],
    (EntityType.GENE, EntityType.DISEASE): [
        ("search_literature", DatabasePriority.CRITICAL),
        ("search_gwas", DatabasePriority.HIGH),
        ("analyze_target", DatabasePriority.MEDIUM)
    ],
    (EntityType.GENE, EntityType.PROTEIN): [
        ("get_protein_info", DatabasePriority.CRITICAL),
        ("search_literature", DatabasePriority.HIGH)
    ],
    (EntityType.GENE, EntityType.GENE): [
        ("get_string_interactions", DatabasePriority.CRITICAL),
        ("get_biogrid_interactions", DatabasePriority.HIGH),
        ("get_intact_interactions", DatabasePriority.MEDIUM)
    ],
    (EntityType.GENE, EntityType.VARIANT): [
        ("search_variants", DatabasePriority.CRITICAL),
        ("search_gwas", DatabasePriority.HIGH)
    ],
    (EntityType.GENE, EntityType.DRUG): [
        ("analyze_target", DatabasePriority.CRITICAL),
        ("search_chembl", DatabasePriority.HIGH),
        ("search_chemical", DatabasePriority.LOW)
    ],

    # Protein relationships
    (EntityType.PROTEIN, EntityType.PROTEIN): [
        ("get_string_interactions", DatabasePriority.CRITICAL),
        ("get_intact_interactions", DatabasePriority.HIGH),
        ("get_biogrid_interactions", DatabasePriority.MEDIUM)
    ],
    (EntityType.PROTEIN, EntityType.PATHWAY): [
        ("analyze_pathways", DatabasePriority.CRITICAL),
        ("search_literature", DatabasePriority.HIGH)
    ],
    (EntityType.PROTEIN, EntityType.DISEASE): [
        ("analyze_target", DatabasePriority.CRITICAL),
        ("search_literature", DatabasePriority.HIGH)
    ],
    (EntityType.PROTEIN, EntityType.DRUG): [
        ("analyze_target", DatabasePriority.CRITICAL),
        ("get_chembl_bioactivities", DatabasePriority.HIGH),
        ("search_literature", DatabasePriority.MEDIUM)
    ],

    # Pathway relationships
    (EntityType.PATHWAY, EntityType.DISEASE): [
        ("analyze_pathways", DatabasePriority.CRITICAL),
        ("search_literature", DatabasePriority.HIGH)
    ],
    (EntityType.PATHWAY, EntityType.DRUG): [
        ("search_literature", DatabasePriority.HIGH),
        ("analyze_pathways", DatabasePriority.MEDIUM)
    ],

    # Disease relationships
    (EntityType.DISEASE, EntityType.DRUG): [
        ("analyze_disease", DatabasePriority.CRITICAL),
        ("search_literature", DatabasePriority.HIGH),
        ("search_clinical_annotation", DatabasePriority.MEDIUM)
    ],
    (EntityType.DISEASE, EntityType.VARIANT): [
        ("search_gwas", DatabasePriority.CRITICAL),
        ("search_variants", DatabasePriority.HIGH),
        ("search_literature", DatabasePriority.MEDIUM)
    ],

    # Drug relationships
    (EntityType.DRUG, EntityType.DRUG): [
        ("search_literature", DatabasePriority.CRITICAL),
        ("search_chembl", DatabasePriority.HIGH)
    ],
    (EntityType.DRUG, EntityType.CHEMICAL): [
        ("search_chembl", DatabasePriority.CRITICAL),
        ("get_chembl_compound_details", DatabasePriority.HIGH),
        ("search_chemical", DatabasePriority.MEDIUM)
    ],

    # Variant relationships
    (EntityType.VARIANT, EntityType.PHENOTYPE): [
        ("search_gwas", DatabasePriority.CRITICAL),
        ("search_literature", DatabasePriority.HIGH)
    ],

    # Single entity queries
    (EntityType.GENE, None): [
        ("get_protein_info", DatabasePriority.CRITICAL),
        ("search_literature", DatabasePriority.HIGH),
        ("analyze_pathways", DatabasePriority.MEDIUM)
    ],
    (EntityType.PROTEIN, None): [
        ("get_protein_info", DatabasePriority.CRITICAL),
        ("search_literature", DatabasePriority.HIGH)
    ],
    (EntityType.DISEASE, None): [
        ("search_literature", DatabasePriority.CRITICAL),
        ("analyze_disease", DatabasePriority.HIGH)
    ],
    (EntityType.DRUG, None): [
        ("search_chembl", DatabasePriority.CRITICAL),
        ("get_chembl_compound_details", DatabasePriority.HIGH),
        ("search_chemical", DatabasePriority.MEDIUM)
    ],
    (EntityType.PATHWAY, None): [
        ("analyze_pathways", DatabasePriority.CRITICAL),
        ("search_literature", DatabasePriority.HIGH)
    ],
}

# Intent-specific database priorities
INTENT_DB_PRIORITIES = {
    QueryIntent.EXPLANATION: {
        "search_literature": 5,      # Literature is critical for explanations
        "analyze_pathways": 3        # Pathways help explain mechanisms
    },
    QueryIntent.MECHANISM: {
        "analyze_pathways": 5,       # Pathways are essential for mechanisms
        "get_string_interactions": 3  # Interactions help explain mechanisms
    },
    QueryIntent.PREDICTION: {
        "search_gwas": 4,            # GWAS data helps with predictions
        "analyze_target": 3          # Target data helps with predictions
    },
    QueryIntent.COMPARISON: {
        "get_protein_info": 3,       # Protein data helps with comparisons
        "search_chembl": 3           # Chemical data helps with comparisons
    },
    QueryIntent.TREATMENT: {
        "search_clinical_annotation": 5,  # Clinical data is critical for treatments
        "analyze_disease": 4,            # Disease data helps with treatment context
        "search_chemical": 3             # Chemical data helps with treatment options
    }
}

# Relationship-specific database priorities
RELATIONSHIP_DB_PRIORITIES = {
    RelationshipType.CAUSAL: {
        "search_literature": 5,      # Literature for causal relationships
        "search_gwas": 4             # GWAS for genetic causal relationships
    },
    RelationshipType.REGULATORY: {
        "get_string_interactions": 5, # STRING for regulatory relationships
        "get_biogrid_interactions": 4 # BioGRID for regulatory relationships
    },
    RelationshipType.STRUCTURAL: {
        "get_protein_info": 5,       # Protein info for structural relationships
        "search_chembl": 4           # Chemical info for structural relationships
    }
}

class QueryAnalyzer:
    """
    Analyzes biological queries to determine intent, entities, and optimal database sequence.
    """
    
    def __init__(self, openai_client: AsyncOpenAI, model: str = "gpt-4o"):
        """
        Initialize the query analyzer.
        
        Args:
            openai_client: AsyncOpenAI client
            model: OpenAI model to use for analysis
        """
        self.client = openai_client
        self.model = model
        self.logger = logging.getLogger(__name__)
    
    async def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze a biological query to determine intent, entities, and relationships.
        
        Args:
            query: The user's query string
            
        Returns:
            Dict containing query classification
        """
        BioChatLogger.log_info(f"Analyzing query: {query[:100]}...")
        
        system_prompt = """
        You are a specialized biological query analyzer that extracts structured information from research questions.
        
        Analyze the given biological research query and extract:
        1. primary_intent: The main purpose of the query (explanation, prediction, comparison, identification, mechanism, treatment, diagnosis)
        2. entities: All biological entities mentioned in the query, categorized by type
        3. relationship_type: The type of relationship being asked about
        
        Return a JSON object with the following structure:
        {
            "primary_intent": "explanation|prediction|comparison|identification|mechanism|treatment|diagnosis",
            "entities": {
                "gene": ["BRCA1", "TP53"],
                "protein": ["insulin"],
                "pathway": ["apoptosis"],
                "disease": ["diabetes"],
                "drug": ["metformin"],
                "variant": ["rs123456"],
                "cell_type": ["T cell"],
                "tissue": ["liver"],
                "phenotype": ["obesity"],
                "organism": ["mouse"],
                "chemical": ["glucose"]
            },
            "relationship_type": "causal|associative|regulatory|structural|functional|unknown",
            "confidence": 0.8  // Your confidence in this analysis (0-1)
        }
        
        Only include entity types that are actually present in the query. If no entities of a particular type are mentioned, omit that type entirely.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            BioChatLogger.log_info(f"Query analysis result: {json.dumps(result)}")
            return result
            
        except Exception as e:
            BioChatLogger.log_error(f"Error analyzing query: {str(e)}", e)
            # Return a default analysis to avoid breaking the pipeline
            return {
                "primary_intent": "unknown",
                "entities": {},
                "relationship_type": "unknown",
                "confidence": 0.0,
                "error": str(e)
            }
    
    def get_optimal_database_sequence(self, analysis: Dict[str, Any]) -> List[str]:
        """
        Determine the optimal database sequence based on entity relationships.
        
        Args:
            analysis: The query analysis from analyze_query
            
        Returns:
            List of database endpoint names in priority order
        """
        try:
            # Extract data from analysis
            intent = analysis.get("primary_intent", "unknown")
            entities = analysis.get("entities", {})
            relationship = analysis.get("relationship_type", "unknown")
            
            # Create entity type pairs for lookup
            entity_pairs = []
            entity_types = []
            
            # Convert string entity types to EntityType enum values
            for type_str, names in entities.items():
                try:
                    entity_type = EntityType(type_str)
                    entity_types.append(entity_type)
                    if names and len(names) > 0:
                        BioChatLogger.log_info(f"Found entity type {entity_type} with {len(names)} entities")
                except ValueError:
                    BioChatLogger.log_info(f"Unknown entity type: {type_str}")
            
            # Create all possible entity type pairs
            for i, type1 in enumerate(entity_types):
                for type2 in entity_types[i+1:]:  # Only create distinct pairs
                    entity_pairs.append((type1, type2))
                    entity_pairs.append((type2, type1))  # Add reverse pair too
                
                # Also add single entity type for direct lookups
                entity_pairs.append((type1, None))
            
            # If no entity pairs are found, use a fallback approach
            if not entity_pairs:
                BioChatLogger.log_info("No entity pairs found, using literature search as fallback")
                return ["search_literature"]
            
            # Calculate database priorities
            db_priorities = {}
            
            # 1. Add priorities from entity pairs
            for entity_pair in entity_pairs:
                if entity_pair in ENTITY_DB_MAPPING:
                    for db, priority in ENTITY_DB_MAPPING[entity_pair]:
                        if db not in db_priorities:
                            db_priorities[db] = 0
                        # Add priority score
                        priority_value = {
                            DatabasePriority.CRITICAL: 10,
                            DatabasePriority.HIGH: 5, 
                            DatabasePriority.MEDIUM: 3,
                            DatabasePriority.LOW: 1,
                            DatabasePriority.FALLBACK: 0.5
                        }.get(priority, 0)
                        db_priorities[db] += priority_value
            
            # 2. Adjust priorities based on intent
            if intent in INTENT_DB_PRIORITIES:
                for db, bonus in INTENT_DB_PRIORITIES[intent].items():
                    if db in db_priorities:
                        db_priorities[db] += bonus
                    else:
                        db_priorities[db] = bonus
            
            # 3. Adjust priorities based on relationship type
            relationship_enum = RelationshipType.UNKNOWN
            try:
                relationship_enum = RelationshipType(relationship)
            except ValueError:
                pass
                
            if relationship_enum in RELATIONSHIP_DB_PRIORITIES:
                for db, bonus in RELATIONSHIP_DB_PRIORITIES[relationship_enum].items():
                    if db in db_priorities:
                        db_priorities[db] += bonus
                    else:
                        db_priorities[db] = bonus
            
            # 4. Ensure literature search is always included as a fallback
            if "search_literature" not in db_priorities:
                db_priorities["search_literature"] = 1
            
            # Sort databases by priority score
            sorted_dbs = sorted(db_priorities.items(), key=lambda x: x[1], reverse=True)
            result = [db for db, score in sorted_dbs]
            
            BioChatLogger.log_info(f"Optimal database sequence: {result}")
            BioChatLogger.log_info(f"Database scores: {sorted_dbs}")
            
            return result
            
        except Exception as e:
            BioChatLogger.log_error(f"Error determining database sequence: {str(e)}", e)
            # Return a reasonable default
            return ["search_literature", "get_protein_info", "analyze_pathways"]
    
    def create_domain_specific_prompt(self, analysis: Dict[str, Any]) -> str:
        """
        Generate a domain-specific system prompt based on query analysis.
        
        Args:
            analysis: The query analysis from analyze_query
            
        Returns:
            A tailored system prompt for the specific query domain
        """
        try:
            # Extract data from analysis
            intent = analysis.get("primary_intent", "unknown")
            entities = analysis.get("entities", {})
            relationship = analysis.get("relationship_type", "unknown")
            
            # Base prompt
            base_prompt = """You are BioChat, a specialized AI assistant for biological and medical research with expertise in multiple biological databases."""
            
            # Intent-specific instructions
            intent_instructions = {
                "explanation": """
                Focus on clearly explaining biological mechanisms and pathways. 
                Highlight causal relationships and provide molecular details when available.
                Present information in a logical sequence, building from simpler concepts to more complex ones.
                """,
                
                "prediction": """
                Focus on evidence-based predictions, clearly distinguishing between well-established relationships and speculative ones.
                Quantify prediction confidence when possible using statistics from the data.
                Highlight any contradictory evidence and explain the limitations of current knowledge.
                """,
                
                "comparison": """
                Structure your response as a systematic comparison, highlighting both similarities and differences.
                Use parallel structure when comparing entities and organize by key features.
                When appropriate, create a mental model that explains why differences exist.
                """,
                
                "identification": """
                Focus on providing definitive characteristics and properties of the entities.
                Organize information hierarchically from most distinctive features to more general ones.
                Include relevant classification systems and nomenclature.
                """,
                
                "mechanism": """
                Provide detailed step-by-step explanations of molecular and cellular mechanisms.
                Use cause-and-effect language and explain the temporal sequence of events.
                Connect molecular events to higher-level biological functions and outcomes.
                """,
                
                "treatment": """
                Focus on evidence-based treatment approaches, prioritizing information from clinical studies.
                Clearly distinguish between established treatments and experimental approaches.
                Include relevant information about efficacy, safety, and mechanisms of action.
                """,
                
                "diagnosis": """
                Provide clear diagnostic criteria and relevant biomarkers.
                Explain how different conditions are differentiated.
                Include information about diagnostic tests and their interpretation.
                """
            }
            
            # Entity-specific instructions
            entity_instructions = ""
            for entity_type, names in entities.items():
                if entity_type == "gene" or entity_type == "protein":
                    entity_instructions += """
                    For genes and proteins, emphasize:
                    - Primary function and biological role
                    - Key pathways and interaction partners
                    - Disease associations and clinical relevance
                    - Structural and regulatory features
                    """
                elif entity_type == "disease":
                    entity_instructions += """
                    For diseases, emphasize:
                    - Underlying molecular mechanisms
                    - Genetic and environmental factors
                    - Current therapeutic approaches
                    - Diagnostic criteria and biomarkers
                    """
                elif entity_type == "drug" or entity_type == "chemical":
                    entity_instructions += """
                    For drugs and chemicals, emphasize:
                    - Mechanism of action and molecular targets
                    - Pharmacokinetics and pharmacodynamics
                    - Clinical applications and efficacy
                    - Safety profile and side effects
                    """
                elif entity_type == "pathway":
                    entity_instructions += """
                    For biological pathways, emphasize:
                    - Component genes and proteins
                    - Regulatory mechanisms and key control points
                    - Cellular and physiological outcomes
                    - Cross-talk with other pathways
                    """
                elif entity_type == "variant":
                    entity_instructions += """
                    For genetic variants, emphasize:
                    - Location and nature of the variant
                    - Functional consequences of the variant
                    - Associated phenotypes and diseases
                    - Population frequencies and risk assessments 
                    - Molecular mechanisms of pathogenicity
                    """
                elif entity_type == "phenotype":
                    entity_instructions += """
                    For phenotypes, emphasize:
                    - Clinical and physiological manifestations
                    - Underlying molecular mechanisms
                    - Genetic and environmental influences
                    - Diagnostic criteria and biomarkers
                    - Relationship to disease progression
                    """
                elif entity_type == "cell_type" or entity_type == "tissue":
                    entity_instructions += """
                    For cells and tissues, emphasize:
                    - Structure and functional characteristics
                    - Cell-cell interactions and signaling
                    - Role in physiological processes
                    - Pathological changes in disease states
                    - Tissue-specific gene expression patterns
                    """
                else:
                    # Generic instructions for any other entity type
                    entity_instructions += f"""
                    For {entity_type}, emphasize:
                    - Definition and key characteristics
                    - Biological context and importance
                    - Related entities and interactions
                    - Research significance and applications
                    """
            
            # Relationship-specific instructions
            relationship_instructions = {
                "causal": "Clearly distinguish between correlation and causation, highlighting direct evidence for causal relationships.",
                "associative": "Present statistical associations with appropriate context about study design and potential confounders.",
                "regulatory": "Detail the direction and magnitude of regulatory effects and the mechanisms involved.",
                "structural": "Include specific structural details, interactions, and spatial relationships when available.",
                "functional": "Explain how functional relationships manifest and their biological significance."
            }
            
            # Combine all instructions
            prompt = f"{base_prompt}\n\n"
            
            if intent in intent_instructions:
                prompt += f"## Query Intent: {intent.capitalize()}\n{intent_instructions[intent]}\n\n"
            
            if entity_instructions:
                prompt += f"## Entity Focus\n{entity_instructions}\n\n"
            
            if relationship in relationship_instructions:
                prompt += f"## Relationship Focus: {relationship.capitalize()}\n{relationship_instructions[relationship]}\n\n"
            
            # Data synthesis instructions
            prompt += """
            ## Data Synthesis Instructions
            
            1. Integrate information across multiple databases to provide a comprehensive view.
            2. Highlight agreements and contradictions in the data.
            3. Cite the specific data sources for key claims.
            4. Present information at appropriate levels of detail:
               - Begin with a concise executive summary
               - Follow with detailed analysis organized by key concepts
               - Include technical details for specialists
            5. Make information accessible by defining specialized terms.
            6. Indicate confidence levels and limitations in the available data.
            """
            
            return prompt
            
        except Exception as e:
            BioChatLogger.log_error(f"Error creating domain-specific prompt: {str(e)}", e)
            # Return the default system prompt
            return """You are BioChat, a specialized AI assistant for biological and medical research, with access to multiple biological databases."""