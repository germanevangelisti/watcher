"""
Scrapers package - Portal Data Scrapers (PDS Layer)

This package contains specialized scrapers for different data sources.
Each scraper implements the BaseScraper interface.
"""

from .base_scraper import BaseScraper, ScraperResult, ScraperConfig, DocumentType, ScraperType
from .pds_prov import ProvincialScraper, create_provincial_scraper
from .pds_muni import MunicipalScraper, create_municipal_scraper
from .pds_nat import NationalScraper, create_national_scraper

__all__ = [
    "BaseScraper",
    "ScraperResult",
    "ScraperConfig",
    "DocumentType",
    "ScraperType",
    "ProvincialScraper",
    "create_provincial_scraper",
    "MunicipalScraper",
    "create_municipal_scraper",
    "NationalScraper",
    "create_national_scraper",
]
