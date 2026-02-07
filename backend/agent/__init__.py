"""
Gemini-powered CRM Analytics Agent
Two-stage prompting system for intelligent data retrieval and analysis
"""

from .agent import CRMAnalyticsAgent
from .catalog import DATA_CATALOG, get_catalog_summary
from .data_loader import DataLoader
from .gemini_client import GeminiAgent

__all__ = [
    "CRMAnalyticsAgent",
    "DATA_CATALOG",
    "get_catalog_summary",
    "DataLoader",
    "GeminiAgent"
]
