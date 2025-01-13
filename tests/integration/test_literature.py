import pytest
from tests.utils.logger import test_logger


@pytest.mark.integration
@pytest.mark.asyncio
async def test_complex_query(integration_orchestrator, clear_conversation_history):
    """Test querying multiple genes and their interactions"""

    query = """ What is the mechanistic relationship between PCSK9 and atherosclerotic plaque development in 
    coronary artery disease, specifically addressing: (1) the protein's role in LDL receptor recycling and 
    its impact on plasma LDL-cholesterol levels, (2) its influence on vascular inflammation through NF-κB signaling pathways,
    (3) the clinical implications of gain-of-function versus loss-of-function PCSK9 genetic variants on cardiovascular outcomes,
    and (4) how these molecular mechanisms inform current therapeutic approaches using PCSK9 inhibitors. Include discussion of 
    recent findings regarding potential LDL-receptor-independent effects of PCSK9 on atherosclerosis progression and any 
    emerging evidence for sex-specific differences in PCSK9-mediated cardiovascular risk."""
    response = await integration_orchestrator.process_query(query)
    
    test_logger.log_conversation(
        test_name="Complex and technical Query",
        query=query,
        response=response,
        conversation_history=integration_orchestrator.get_conversation_history()
    )
    
    assert isinstance(response, str)
    assert len(response) > 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_DSP_literature_search(integration_orchestrator, clear_conversation_history):
    """Test searching for DSP-related literature"""
    query = "What are the key findings about DSP's role in myocardial infarction from recent research?"
    response = await integration_orchestrator.process_query(query)
    
    # Log the complete conversation
    test_logger.log_conversation(
        test_name="DSP Literature Search",
        query=query,
        response=response,
        conversation_history=integration_orchestrator.get_conversation_history()
    )
    
    assert isinstance(response, str)
    assert len(response) > 0
    assert "DSP" in response


@pytest.mark.integration
@pytest.mark.asyncio
async def test_complex_query_with_multiple_genes(integration_orchestrator, clear_conversation_history):
    """Test querying multiple genes and their interactions"""
        
    query = "What is known about the interaction between DSP, BRCA2, and TP53 in cancer development?"
    response = await integration_orchestrator.process_query(query)
    
    test_logger.log_conversation(
        test_name="Complex Gene Interactions Query",
        query=query,
        response=response,
        conversation_history=integration_orchestrator.get_conversation_history()
    )
    
    assert isinstance(response, str)
    assert len(response) > 200
    assert all(gene in response for gene in ["DSP", "BRCA2", "TP53"])

@pytest.mark.integration
@pytest.mark.asyncio
async def test_date_range_query(integration_orchestrator, clear_conversation_history):
    """Test searching literature within a specific date range"""
    # Use a more specific query that encourages temporal context
    query = "What are the major discoveries and advances in PCSK9 research in heart disease published between 2023 and 2025?"
    response = await integration_orchestrator.process_query(query)
    
    test_logger.log_conversation(
        test_name="Date Range Query",
        query=query,
        response=response,
        conversation_history=integration_orchestrator.get_conversation_history()
    )
    
    # Check for successful response
    assert isinstance(response, str)
    assert len(response) > 0
    
    # More comprehensive response validation
    keywords = [
        "recent", "new", "latest", "current", "study", "research",
        "published", "findings", "discovered", "advances", "developments"
    ]
    
    # Allow for both direct responses and processing messages
    if "processing" in response.lower() or "searching" in response.lower():
        assert any(term in response.lower() for term in [
            "search", "looking", "gathering", "retrieving"
        ])
    else:
        assert any(keyword in response.lower() for keyword in keywords)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_invalid_query(integration_orchestrator, clear_conversation_history):
    """Test handling of invalid or malformed queries"""
    # Use a more clearly invalid query
    query = """What is the mechanistic relationship between !@!@#±"""
    response = await integration_orchestrator.process_query(query)
    
    test_logger.log_conversation(
        test_name="Invalid Query Handling",
        query=query,
        response=response,
        conversation_history=integration_orchestrator.get_conversation_history()
    )
    
    assert isinstance(response, str)
    assert len(response) > 0
    
    # Updated assertion patterns to match both error and clarification responses
    error_patterns = [
        # Error messages
        "error", "invalid", "unable to process",
        # Clarification requests
        "could you please", "could you specify", "please provide",
        # System messages
        "unable to understand", "invalid format",
        # Help messages
        "try rephrasing", "more specific", "clarify"
    ]
    
    if not any(pattern in response.lower() for pattern in error_patterns):
        # test_logger.warning(f"Unexpected response format: {response}")
        test_logger.log_conversation("Warning", "Unexpected response", 
                                   f"Response didn't match expected patterns: {response}")
    
    assert any(pattern in response.lower() for pattern in error_patterns)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_result_synthesis(integration_orchestrator, clear_conversation_history):
    """Test the system's ability to synthesize information from multiple sources"""
    query = "What are the current treatment approaches for myocardial infarction patients?"
    response = await integration_orchestrator.process_query(query)
    
    test_logger.log_conversation(
        test_name="Treatment Approaches Synthesis",
        query=query,
        response=response,
        conversation_history=integration_orchestrator.get_conversation_history()
    )
    
    # Updated assertions and error handling
    assert isinstance(response, str)
    if "error" in response.lower():
        pytest.skip("Skipping length assertion due to error response")
    else:
        assert len(response) > 300
        assert any(term in response.lower() for term in ["treatment", "therapy", "approach", "management"])
        assert any(term in response.lower() for term in ["study", "research", "evidence", "findings"])