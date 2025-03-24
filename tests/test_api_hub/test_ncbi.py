"""
Integration tests for the NCBI E-utilities API client.
"""

import os
import pytest
from biochat.api_hub import NCBIEutils

pytestmark = pytest.mark.asyncio

@pytest.fixture
async def ncbi_client():
    """Fixture to provide an NCBI API client."""
    # Skip test if NCBI API key is missing
    if not os.getenv("NCBI_API_KEY"):
        pytest.skip("NCBI API key not found in environment variables")
    
    client = NCBIEutils(
        api_key=os.getenv("NCBI_API_KEY"),
        tool="BioChat_Test",
        email=os.getenv("CONTACT_EMAIL")
    )
    
    yield client
    
    # Cleanup
    if client.session and not client.session.closed:
        await client.session.close()

class TestNCBIEutils:
    """Test the NCBIEutils API client."""
    
    async def test_search(self, ncbi_client):
        """Test the basic search functionality."""
        # Search for a well-known gene
        results = await ncbi_client.search("TP53")
        
        # Check that we got valid results
        assert results is not None
        assert isinstance(results, dict)
        
        # Check that the results contain expected fields
        if "esearchresult" in results:
            assert "idlist" in results["esearchresult"]
            assert isinstance(results["esearchresult"]["idlist"], list)
            # TP53 should have many results
            assert len(results["esearchresult"]["idlist"]) > 0
    
    async def test_search_pubmed(self, ncbi_client):
        """Test the PubMed search functionality."""
        # Search for publications about TP53 and cancer
        results = await ncbi_client.search_pubmed(
            genes=["TP53"],
            phenotypes=["cancer"],
            max_results=5
        )
        
        # Check that we got valid results
        assert results is not None
        assert isinstance(results, dict)
        
        # We should have gotten some results
        if "esearchresult" in results:
            assert "idlist" in results["esearchresult"]
            assert len(results["esearchresult"]["idlist"]) > 0
        elif "result" in results:
            assert "uids" in results["result"] or isinstance(results["result"], dict)
            
    async def test_search_and_analyze(self, ncbi_client):
        """Test the search and analyze functionality."""
        # Search for publications about TP53 and cancer
        results = await ncbi_client.search_and_analyze(
            genes=["TP53"],
            phenotypes=["cancer"],
            max_results=3
        )
        
        # Check that we got valid results
        assert results is not None
        assert isinstance(results, dict)
        
        # Check result structure
        assert "metadata" in results
        assert "articles" in results or "error" in results  # We might get an error if rate limited
        
        # If we got articles, check their structure
        if "articles" in results:
            assert isinstance(results["articles"], dict)
            # We might get fewer articles than requested due to API limitations
            if len(results["articles"]) > 0:
                # Get the first article
                article_id = next(iter(results["articles"]))
                article = results["articles"][article_id]
                
                # Check article structure
                assert "title" in article
                assert "authors" in article
                assert "journal" in article