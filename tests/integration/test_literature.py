import pytest
from tests.utils.logger import test_logger

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
    query = "What are the major discoveries about DSP in the past 2 years?"
    response = await integration_orchestrator.process_query(query)
    
    test_logger.log_conversation(
        test_name="Date Range Query",
        query=query,
        response=response,
        conversation_history=integration_orchestrator.get_conversation_history()
    )
    
    assert isinstance(response, str)
    assert len(response) > 0
    assert "recent" in response.lower() or "new" in response.lower()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_invalid_query(integration_orchestrator, clear_conversation_history):
    """Test handling of invalid or malformed queries"""
    query = "Find papers about @#$%^"
    response = await integration_orchestrator.process_query(query)
    
    test_logger.log_conversation(
        test_name="Invalid Query Handling",
        query=query,
        response=response,
        conversation_history=integration_orchestrator.get_conversation_history()
    )
    
    assert isinstance(response, str)
    assert len(response) > 0
    assert "clarify" in response.lower() or "specify" in response.lower()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_result_synthesis(integration_orchestrator, clear_conversation_history):
    """Test the system's ability to synthesize information from multiple sources"""
    query = "What are the current treatment approaches for DSP-positive myocardial infarction patients?"
    response = await integration_orchestrator.process_query(query)
    
    test_logger.log_conversation(
        test_name="Treatment Approaches Synthesis",
        query=query,
        response=response,
        conversation_history=integration_orchestrator.get_conversation_history()
    )
    
    assert isinstance(response, str)
    assert len(response) > 300