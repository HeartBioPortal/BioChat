import pytest
from unittest.mock import Mock, patch
from src.tool_executor import ToolExecutor
from src.schemas import LiteratureSearchParams, VariantSearchParams

@pytest.fixture
def tool_executor():
    """Create a ToolExecutor instance with mock API clients"""
    with patch('src.tool_executor.NCBIEutils') as mock_ncbi, \
         patch('src.tool_executor.EnsemblAPI') as mock_ensembl, \
         patch('src.tool_executor.GWASCatalog') as mock_gwas, \
         patch('src.tool_executor.UniProtAPI') as mock_uniprot:
        
        executor = ToolExecutor(
            ncbi_api_key="mock_key",
            tool_name="test_tool",
            email="test@example.com"
        )
        return executor

@pytest.mark.asyncio
async def test_execute_literature_search(tool_executor):
    """Test literature search execution"""
    mock_tool_call = Mock()
    mock_tool_call.function.name = "search_literature"
    mock_tool_call.function.arguments = '''{
        "genes": ["BRCA1"],
        "phenotypes": ["Breast Cancer"],
        "max_results": 5
    }'''
    
    # Configure mock response
    tool_executor.ncbi.search_and_analyze.return_value = {
        "articles": [
            {
                "title": "Test Article",
                "abstract": "Test abstract",
                "authors": ["Author One"],
                "journal": "Test Journal",
                "pubdate": "2024"
            }
        ]
    }
    
    result = await tool_executor.execute_tool(mock_tool_call)
    
    assert "articles" in result
    assert len(result["articles"]) == 1
    assert result["articles"][0]["title"] == "Test Article"
    tool_executor.ncbi.search_and_analyze.assert_called_once()

@pytest.mark.asyncio
async def test_execute_variant_search(tool_executor):
    """Test variant search execution"""
    mock_tool_call = Mock()
    mock_tool_call.function.name = "search_variants"
    mock_tool_call.function.arguments = '''{
        "chromosome": "13",
        "start": 32315474,
        "end": 32400266
    }'''
    
    # Configure mock response
    tool_executor.ensembl.get_variants.return_value = {
        "variants": [
            {
                "id": "rs123456",
                "alleles": ["A", "G"],
                "position": 32315500
            }
        ]
    }
    
    result = await tool_executor.execute_tool(mock_tool_call)
    
    assert "variants" in result
    assert len(result["variants"]) == 1
    assert result["variants"][0]["id"] == "rs123456"
    tool_executor.ensembl.get_variants.assert_called_once()

@pytest.mark.asyncio
async def test_error_handling(tool_executor):
    """Test error handling in tool execution"""
    mock_tool_call = Mock()
    mock_tool_call.function.name = "search_literature"
    mock_tool_call.function.arguments = '''{
        "invalid": "arguments"
    }'''
    
    result = await tool_executor.execute_tool(mock_tool_call)
    
    assert "error" in result
    assert isinstance(result["error"], str)

@pytest.mark.asyncio
async def test_unknown_function(tool_executor):
    """Test handling of unknown function calls"""
    mock_tool_call = Mock()
    mock_tool_call.function.name = "unknown_function"
    mock_tool_call.function.arguments = '{}'
    
    result = await tool_executor.execute_tool(mock_tool_call)
    
    assert "error" in result
    assert "Unknown function" in result["error"]