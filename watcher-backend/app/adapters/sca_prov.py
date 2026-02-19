"""
SCA-PROV - Provincial Source Adapter

Transforms data from Boletín Oficial de Córdoba into unified DocumentSchema.
"""

import logging
import re
from datetime import date, datetime
from typing import Dict, List, Optional, Any

from .base_adapter import (
    BaseAdapter,
    AdapterResult,
    DocumentSchema,
    SourceType,
    DocumentCategory
)

logger = logging.getLogger(__name__)


class ProvincialAdapter(BaseAdapter):
    """
    Adapter for Provincial Bulletin data.
    
    Transforms boletines from Córdoba province into unified schema.
    """
    
    def __init__(self):
        """Initialize provincial adapter."""
        super().__init__(SourceType.PROVINCIAL)
        
        # Jurisdiction ID for Provincia de Córdoba
        self.default_jurisdiction_id = 1
        self.default_jurisdiction_name = "Provincia de Córdoba"
    
    async def adapt_document(
        self,
        raw_data: Dict[str, Any],
        **kwargs
    ) -> AdapterResult:
        """
        Transform a single provincial bulletin into DocumentSchema.
        
        Args:
            raw_data: Dict with keys like 'filename', 'date', 'section', 'content', etc.
            **kwargs: Additional context
            
        Returns:
            AdapterResult with normalized document
        """
        warnings = []
        
        try:
            # Extract core data
            filename = raw_data.get('filename', '')
            if not filename:
                return AdapterResult(
                    success=False,
                    error="Missing required field: filename"
                )
            
            # Parse date from filename or raw_data
            doc_date = self._parse_date(raw_data, warnings)
            if not doc_date:
                return AdapterResult(
                    success=False,
                    error="Could not parse document date"
                )
            
            # Parse section
            section = self._parse_section(raw_data, warnings)
            
            # Generate document ID
            document_id = f"prov_{doc_date.strftime('%Y%m%d')}_{section}"
            if raw_data.get('id'):
                document_id = f"prov_{raw_data['id']}"
            
            # Create normalized document
            document = DocumentSchema(
                source_type=SourceType.PROVINCIAL,
                document_id=document_id,
                filename=filename,
                category=DocumentCategory.BOLETIN,
                document_date=doc_date,
                ingestion_date=datetime.now(),
                title=self._generate_title(doc_date, section),
                content=raw_data.get('content') or raw_data.get('contenido'),
                summary=raw_data.get('summary') or raw_data.get('resumen'),
                jurisdiction_id=self.default_jurisdiction_id,
                jurisdiction_name=self.default_jurisdiction_name,
                section=str(section) if section else None,
                file_path=raw_data.get('file_path') or raw_data.get('filepath'),
                file_size=raw_data.get('file_size') or raw_data.get('size'),
                extraction_status=raw_data.get('status', 'pending'),
                metadata={
                    'source': 'boletinoficial.cba.gov.ar',
                    'scraper_type': 'pds_prov',
                    'original_data': {k: v for k, v in raw_data.items() 
                                     if k not in ['content', 'contenido']}
                }
            )
            
            # Validate
            if not self.validate_document(document):
                warnings.append("Document validation failed, but continuing")
            
            result = AdapterResult(
                success=True,
                document=document,
                warnings=warnings
            )
            
            self._update_stats(result)
            return result
        
        except Exception as e:
            logger.error(f"Error adapting provincial document: {e}", exc_info=True)
            result = AdapterResult(
                success=False,
                error=str(e),
                warnings=warnings
            )
            self._update_stats(result)
            return result
    
    async def adapt_batch(
        self,
        raw_data_list: List[Dict[str, Any]],
        **kwargs
    ) -> List[AdapterResult]:
        """
        Transform a batch of provincial bulletins.
        
        Args:
            raw_data_list: List of raw bulletin data
            **kwargs: Additional context
            
        Returns:
            List of AdapterResult objects
        """
        results = []
        
        for raw_data in raw_data_list:
            result = await self.adapt_document(raw_data, **kwargs)
            results.append(result)
        
        logger.info(f"Adapted {len(results)} provincial documents: "
                   f"{self.stats['successful']} successful, {self.stats['failed']} failed")
        
        return results
    
    def validate_document(self, document: DocumentSchema) -> bool:
        """
        Validate provincial document.
        
        Args:
            document: Document to validate
            
        Returns:
            True if valid
        """
        # Required fields
        if not document.document_id:
            logger.warning("Missing document_id")
            return False
        
        if not document.filename:
            logger.warning("Missing filename")
            return False
        
        if not document.document_date:
            logger.warning("Missing document_date")
            return False
        
        if document.source_type != SourceType.PROVINCIAL:
            logger.warning(f"Invalid source_type: {document.source_type}")
            return False
        
        return True
    
    def _parse_date(self, raw_data: Dict[str, Any], warnings: List[str]) -> Optional[date]:
        """Parse date from various sources."""
        # Try direct date field
        if 'date' in raw_data:
            date_val = raw_data['date']
            if isinstance(date_val, date):
                return date_val
            if isinstance(date_val, datetime):
                return date_val.date()
            if isinstance(date_val, str):
                # Try parsing string date
                try:
                    # Try YYYY-MM-DD format
                    return datetime.fromisoformat(date_val.split()[0]).date()
                except Exception:
                    pass
                
                try:
                    # Try YYYYMMDD format
                    if len(date_val) == 8 and date_val.isdigit():
                        return datetime.strptime(date_val, '%Y%m%d').date()
                except Exception:
                    pass
        
        # Try parsing from filename: YYYYMMDD_N_Secc.pdf
        filename = raw_data.get('filename', '')
        match = re.match(r'(\d{8})', filename)
        if match:
            try:
                return datetime.strptime(match.group(1), '%Y%m%d').date()
            except Exception:
                pass
        
        warnings.append("Could not parse date, using today as fallback")
        return datetime.now().date()
    
    def _parse_section(self, raw_data: Dict[str, Any], warnings: List[str]) -> Optional[int]:
        """Parse section number."""
        # Try direct section field
        if 'section' in raw_data:
            try:
                return int(raw_data['section'])
            except Exception:
                pass
        
        # Try parsing from filename
        filename = raw_data.get('filename', '')
        match = re.search(r'_(\d+)_Secc', filename)
        if match:
            try:
                return int(match.group(1))
            except Exception:
                pass
        
        warnings.append("Could not parse section number")
        return None
    
    def _generate_title(self, doc_date: date, section: Optional[int]) -> str:
        """Generate a descriptive title."""
        title = f"Boletín Oficial de Córdoba - {doc_date.strftime('%d/%m/%Y')}"
        if section:
            title += f" - Sección {section}"
        return title


def create_provincial_adapter() -> ProvincialAdapter:
    """Create a provincial adapter instance."""
    return ProvincialAdapter()
