"""
API Hub module for BioChat.

This module provides client classes for accessing various bioinformatics database APIs,
including NCBI E-utilities, Ensembl, GWAS Catalog, UniProt, STRING, Reactome, IntAct,
PharmGKB, and BioGRID.
"""

from biochat.api_hub.ncbi import NCBIEutils
from biochat.api_hub.ensembl import EnsemblAPI
from biochat.api_hub.gwas import GWASCatalog
from biochat.api_hub.uniprot import UniProtAPI
from biochat.api_hub.string_db import StringDBClient
from biochat.api_hub.reactome import ReactomeClient
from biochat.api_hub.pharmgkb import PharmGKBClient
from biochat.api_hub.intact import IntActClient
from biochat.api_hub.biocyc import BioCyc
from biochat.api_hub.biogrid import BioGridClient
from biochat.api_hub.opentargets import OpenTargetsClient
from biochat.api_hub.chembl import ChemblAPI

# Re-export all these classes
__all__ = [
    'NCBIEutils', 'EnsemblAPI', 'GWASCatalog', 'UniProtAPI',
    'StringDBClient', 'ReactomeClient', 'PharmGKBClient',
    'IntActClient', 'BioCyc', 'BioGridClient', 'OpenTargetsClient',
    'ChemblAPI'
]