# Query Analyzer Module

## Overview

The Query Analyzer is a specialized module for intelligent analysis of biological research queries. It uses a combination of NLP techniques and knowledge graphs to determine:

1. **Query Intent** - The purpose of the query (explanation, prediction, comparison, etc.)
2. **Entity Recognition** - Identification of biological entities mentioned (genes, proteins, diseases, etc.)
3. **Relationship Type** - The type of relationship being asked about (causal, regulatory, etc.)
4. **Database Selection** - Optimal sequence of biological databases to query based on entity relationships

## Architecture

The Query Analyzer follows a knowledge graph approach where biological entities and their relationships determine which databases to query:

```
Query → Intent/Entity Analysis → Entity-Relationship Mapping → Database Sequence
```

## Key Components

### 1. Entity Types

The analyzer recognizes various biological entity types:
- Genes
- Proteins
- Pathways
- Diseases
- Drugs
- Variants
- Cell types
- Tissues
- Phenotypes
- Organisms
- Chemicals

### 2. Query Intents

The analyzer identifies the primary purpose of the query:
- Explanation (how/why something works)
- Prediction (outcomes or behaviors)
- Comparison (between entities or processes)
- Identification (characterizing entities)
- Mechanism (biological processes)
- Treatment (interventions)
- Diagnosis (disease identification)

### 3. Relationship Types

The analyzer determines the relationship type being investigated:
- Causal (direct cause-effect)
- Associative (statistical association)
- Regulatory (activation/inhibition)
- Structural (physical relationship)
- Functional (function-related)

### 4. Knowledge Graph Mappings

The system uses predefined mappings between entity pairs and appropriate databases:
- (Gene, Disease) → [Literature, GWAS, Target Analysis]
- (Protein, Protein) → [STRING, IntAct, BioGRID]
- (Pathway, Disease) → [Reactome, Literature]
- etc.

Database priorities are further adjusted based on query intent and relationship type.

## Usage

### Basic Query Analysis

```python
from src.utils.query_analyzer import QueryAnalyzer
from openai import AsyncOpenAI

# Initialize
client = AsyncOpenAI(api_key="your-key")
analyzer = QueryAnalyzer(client)

# Analyze a query
analysis = await analyzer.analyze_query("What role does BRCA1 play in breast cancer?")

# Get database sequence
db_sequence = analyzer.get_optimal_database_sequence(analysis)

# Generate domain-specific prompt
prompt = analyzer.create_domain_specific_prompt(analysis)
```

### Integration with Orchestrator

The `BioChatOrchestrator` includes methods for using the Query Analyzer:

```python
# Test analysis only
result = await orchestrator.test_query_analyzer("What is the function of TP53?")

# Process a query with knowledge graph routing
response = await orchestrator.process_knowledge_graph_query(
    "How does metformin affect insulin signaling pathways?"
)
```

### API Endpoints

The system exposes these endpoints:

- `POST /analyze` - Analyze a query without executing it
- `POST /query/knowledge` - Process a query using knowledge graph routing

## Benefits

1. **Intelligent Routing** - Selects most appropriate databases for specific query types
2. **Specialized Prompting** - Generates domain-specific prompts tailored to the query context
3. **Entity Relationship Focus** - Prioritizes relationships between biological entities
4. **Fallback Mechanisms** - Includes robust fallbacks when analysis is uncertain

## Future Improvements

1. Expand entity and relationship types
2. Add database-specific entity identifiers
3. Include confidence scoring for database selection
4. Incorporate user feedback for continuous improvement
5. Add support for complex multi-entity queries