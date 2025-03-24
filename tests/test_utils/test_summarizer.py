"""
Tests for the ResponseSummarizer utility.
"""

import pytest
from biochat.utils.summarizer import ResponseSummarizer

class TestResponseSummarizer:
    """Test the ResponseSummarizer utility."""
    
    def test_summarize_opentargets_response(self):
        """Test summarization of OpenTargets API responses."""
        # Create a summarizer
        summarizer = ResponseSummarizer()
        
        # Sample OpenTargets response
        response = {
            "data": {
                "drugs": {
                    "count": 2,
                    "rows": [
                        {
                            "drug": {
                                "name": "Drug A",
                                "drugType": "Small molecule"
                            },
                            "status": "Phase 3",
                            "mechanismOfAction": "Inhibitor",
                            "disease": {
                                "name": "Cancer"
                            },
                            "phase": 3
                        },
                        {
                            "drug": {
                                "name": "Drug B",
                                "drugType": "Antibody"
                            },
                            "status": "Phase 2",
                            "mechanismOfAction": "Antagonist",
                            "disease": {
                                "name": "Autoimmune"
                            },
                            "phase": 2
                        }
                    ]
                }
            }
        }
        
        # Summarize response
        summary = summarizer.summarize_response("opentargets", response)
        
        # Check summary structure
        assert summary is not None
        assert isinstance(summary, dict)
        assert "total_drugs" in summary
        assert summary["total_drugs"] == 2
        assert "drugs" in summary
        assert len(summary["drugs"]) == 2
        assert summary["drugs"][0]["name"] == "Drug A"
        assert summary["drugs"][1]["name"] == "Drug B"
    
    def test_summarize_biogrid_response(self):
        """Test summarization of BioGRID API responses."""
        # Create a summarizer
        summarizer = ResponseSummarizer()
        
        # Sample BioGRID response
        response = {
            "success": True,
            "data": {
                "1": {
                    "chemical_name": "Compound X",
                    "protein_target": "Protein A",
                    "interaction_type": "Inhibition",
                    "interaction_evidence": "Experimental",
                    "publication": "Author et al.",
                    "pubmed_id": "12345678"
                },
                "2": {
                    "chemical_name": "Compound Y",
                    "protein_target": "Protein B",
                    "interaction_type": "Binding",
                    "interaction_evidence": "In vitro",
                    "publication": "Researcher et al.",
                    "pubmed_id": "87654321"
                }
            },
            "chemical_list": ["Compound X", "Compound Y"],
            "interaction_count": 2,
            "metadata": {
                "chemicals_found": 2,
                "protein_targets": 2,
                "experiment_types": ["Inhibition", "Binding"]
            }
        }
        
        # Summarize response
        summary = summarizer.summarize_response("biogrid", response)
        
        # Check summary structure
        assert summary is not None
        assert isinstance(summary, dict)
        assert "chemicals_searched" in summary
        assert "chemicals_found" in summary
        assert "total_interactions" in summary
        assert "top_interactions" in summary
        assert len(summary["top_interactions"]) == 2
        assert summary["top_interactions"][0]["chemical"] == "Compound X"
    
    def test_summarize_error_response(self):
        """Test summarization of error responses."""
        # Create a summarizer
        summarizer = ResponseSummarizer()
        
        # Sample error response
        response = {"error": "API rate limit exceeded"}
        
        # Summarize response
        summary = summarizer.summarize_response("opentargets", response)
        
        # Check that the error is passed through
        assert summary is not None
        assert isinstance(summary, dict)
        assert "error" in summary
        assert summary["error"] == "API rate limit exceeded"