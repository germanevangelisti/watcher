"""
Upload API endpoints for boletines.
Epic 1.2 & 1.3 - Batch file upload and generic URL download

Provides endpoints to:
- Upload PDF files directly via HTTP (multipart/form-data)
- Download PDFs from arbitrary URLs
- Automatic SHA256 deduplication
"""

import re
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
import httpx

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends,
    BackgroundTasks
)
from pydantic import BaseModel, validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db import crud
from app.core.config import settings
from app.services.hash_utils import compute_sha256_bytes

router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================

class UploadResult(BaseModel):
    """Result of a single file upload."""
    filename: str
    status: str  # 'uploaded', 'duplicate', 'failed'
    boletin_id: Optional[int] = None
    file_hash: Optional[str] = None
    file_size_bytes: Optional[int] = None
    error: Optional[str] = None
    duplicate_of: Optional[str] = None  # Filename of existing duplicate


class BatchUploadResponse(BaseModel):
    """Response for batch upload operations."""
    total: int
    uploaded: int
    duplicates: int
    failed: int
    results: List[UploadResult]


class DownloadFromURLRequest(BaseModel):
    """Request to download a file from a URL."""
    url: str
    filename: Optional[str] = None  # Override filename
    date: Optional[str] = None      # Override date (YYYYMMDD)
    section: Optional[str] = None   # Override section
    fuente: Optional[str] = "provincial"  # Source type
    
    @validator('date')
    def validate_date(cls, v):
        """Validate date format if provided."""
        if v and not re.match(r'^\d{8}$', v):
            raise ValueError("Date must be in YYYYMMDD format")
        return v


class BatchURLDownloadRequest(BaseModel):
    """Request to download multiple URLs."""
    urls: List[str]
    fuente: Optional[str] = "provincial"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def parse_filename(filename: str) -> Dict[str, Any]:
    """
    Parse filename to extract date and section.
    Expected format: YYYYMMDD_N_Secc.pdf
    
    Returns:
        Dict with 'date', 'section', and 'valid' flag
    """
    pattern = r'^(\d{8})_(\d+)_Secc\.pdf$'
    match = re.match(pattern, filename)
    
    if match:
        return {
            'valid': True,
            'date': match.group(1),
            'section': match.group(2)
        }
    
    return {'valid': False, 'date': None, 'section': None}


def validate_pdf(content: bytes) -> bool:
    """
    Validate that content is a PDF file.
    Checks PDF magic bytes (%PDF).
    """
    if len(content) < 4:
        return False
    return content[:4] == b'%PDF'


async def save_uploaded_file(
    filename: str,
    content: bytes,
    date: Optional[str] = None
) -> Path:
    """
    Save uploaded file to organized directory structure.
    
    Args:
        filename: Name of the file
        content: File content bytes
        date: Optional date in YYYYMMDD format
        
    Returns:
        Path where file was saved
    """
    # Determine save location
    if date and len(date) >= 6:
        year = date[:4]
        month = date[4:6]
        save_dir = settings.UPLOADS_DIR / year / month
    else:
        # Fallback: save in uploads root with timestamp
        save_dir = settings.UPLOADS_DIR / "manual_uploads"
    
    save_dir.mkdir(parents=True, exist_ok=True)
    filepath = save_dir / filename
    
    # Write file
    filepath.write_bytes(content)
    
    return filepath


# =============================================================================
# ENDPOINTS - FILE UPLOAD (Task 1.2)
# =============================================================================

@router.post("/files", response_model=BatchUploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload one or more PDF files with automatic deduplication.
    
    Epic 1.2 - Batch file upload
    
    Features:
    - Accepts multiple files via multipart/form-data
    - Validates PDF format (magic bytes)
    - Computes SHA256 hash for deduplication
    - Parses filename to extract date/section (if format matches)
    - Organizes files by year/month
    - Returns detailed results for each file
    
    Example filename: 20250210_1_Secc.pdf
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Validate file count
    MAX_FILES_PER_REQUEST = 50
    if len(files) > MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_FILES_PER_REQUEST} files per request"
        )
    
    results = []
    uploaded = 0
    duplicates = 0
    failed = 0
    
    for upload_file in files:
        try:
            # Read file content
            content = await upload_file.read()
            
            # Validate size
            MAX_SIZE = 50 * 1024 * 1024  # 50MB
            MIN_SIZE = 10 * 1024  # 10KB
            
            if len(content) > MAX_SIZE:
                results.append(UploadResult(
                    filename=upload_file.filename,
                    status="failed",
                    error=f"File too large (max {MAX_SIZE // (1024*1024)}MB)"
                ))
                failed += 1
                continue
            
            if len(content) < MIN_SIZE:
                results.append(UploadResult(
                    filename=upload_file.filename,
                    status="failed",
                    error=f"File too small (min {MIN_SIZE // 1024}KB)"
                ))
                failed += 1
                continue
            
            # Validate PDF
            if not validate_pdf(content):
                results.append(UploadResult(
                    filename=upload_file.filename,
                    status="failed",
                    error="Not a valid PDF file"
                ))
                failed += 1
                continue
            
            # Compute hash
            file_hash = compute_sha256_bytes(content)
            file_size = len(content)
            
            # Parse filename
            parsed = parse_filename(upload_file.filename)
            date = parsed['date'] if parsed['valid'] else 'unknown'
            section = parsed['section'] if parsed['valid'] else 'unknown'
            
            # Check for duplicate
            boletin = await crud.create_boletin(
                db=db,
                filename=upload_file.filename,
                date=date,
                section=section,
                status="pending",
                file_hash=file_hash,
                file_size_bytes=file_size,
                origin="uploaded"
            )
            
            # Check if this is a new upload or duplicate
            is_duplicate = boletin.file_hash == file_hash and \
                          await db.scalar(
                              crud.select(crud.Boletin).where(
                                  crud.Boletin.file_hash == file_hash,
                                  crud.Boletin.id < boletin.id
                              ).exists().select()
                          )
            
            if is_duplicate:
                # This is a duplicate
                results.append(UploadResult(
                    filename=upload_file.filename,
                    status="duplicate",
                    boletin_id=boletin.id,
                    file_hash=file_hash,
                    file_size_bytes=file_size,
                    duplicate_of=boletin.filename
                ))
                duplicates += 1
            else:
                # Save file
                _filepath = await save_uploaded_file(
                    upload_file.filename,
                    content,
                    date=date if parsed['valid'] else None
                )
                
                results.append(UploadResult(
                    filename=upload_file.filename,
                    status="uploaded",
                    boletin_id=boletin.id,
                    file_hash=file_hash,
                    file_size_bytes=file_size
                ))
                uploaded += 1
        
        except Exception as e:
            results.append(UploadResult(
                filename=upload_file.filename,
                status="failed",
                error=str(e)
            ))
            failed += 1
    
    # Commit all DB changes
    await db.commit()
    
    return BatchUploadResponse(
        total=len(files),
        uploaded=uploaded,
        duplicates=duplicates,
        failed=failed,
        results=results
    )


# =============================================================================
# ENDPOINTS - URL DOWNLOAD (Task 1.3)
# =============================================================================

@router.post("/from-url", response_model=UploadResult)
async def download_from_url(
    request: DownloadFromURLRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Download a PDF from a URL with automatic deduplication.
    
    Epic 1.3 - Generic URL download
    
    Features:
    - Downloads file from any URL
    - Validates PDF format
    - Computes SHA256 for deduplication
    - Supports filename, date, section overrides
    - Times out after 60 seconds
    
    Example:
    ```json
    {
        "url": "https://example.com/documento.pdf",
        "filename": "20250210_1_Secc.pdf",
        "date": "20250210",
        "section": "1",
        "fuente": "municipal_capital"
    }
    ```
    """
    try:
        # Download file with timeout
        timeout = httpx.Timeout(60.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(request.url, follow_redirects=True)
            response.raise_for_status()
            
            content = response.content
        
        # Validate size
        MAX_SIZE = 50 * 1024 * 1024  # 50MB
        MIN_SIZE = 10 * 1024  # 10KB
        
        if len(content) > MAX_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large (max {MAX_SIZE // (1024*1024)}MB)"
            )
        
        if len(content) < MIN_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too small (min {MIN_SIZE // 1024}KB)"
            )
        
        # Validate PDF
        if not validate_pdf(content):
            raise HTTPException(status_code=400, detail="Downloaded file is not a valid PDF")
        
        # Determine filename
        if request.filename:
            filename = request.filename
        else:
            # Extract from URL or Content-Disposition header
            content_disp = response.headers.get('content-disposition', '')
            if 'filename=' in content_disp:
                filename = content_disp.split('filename=')[1].strip('"\'')
            else:
                # Use last part of URL path
                filename = request.url.split('/')[-1]
                if not filename.endswith('.pdf'):
                    filename += '.pdf'
        
        # Compute hash
        file_hash = compute_sha256_bytes(content)
        file_size = len(content)
        
        # Parse or use provided metadata
        if request.date and request.section:
            date = request.date
            section = request.section
        else:
            parsed = parse_filename(filename)
            date = request.date or (parsed['date'] if parsed['valid'] else 'unknown')
            section = request.section or (parsed['section'] if parsed['valid'] else 'unknown')
        
        # Check for duplicate and create/update record
        boletin = await crud.create_boletin(
            db=db,
            filename=filename,
            date=date,
            section=section,
            status="pending",
            file_hash=file_hash,
            file_size_bytes=file_size
        )
        
        # Check if duplicate
        from sqlalchemy import select, func
        duplicate_count = await db.scalar(
            select(func.count(crud.Boletin.id)).where(
                crud.Boletin.file_hash == file_hash
            )
        )
        
        is_duplicate = duplicate_count > 1
        
        if not is_duplicate:
            # Save file
            _filepath = await save_uploaded_file(filename, content, date=date)
        
        await db.commit()
        
        return UploadResult(
            filename=filename,
            status="duplicate" if is_duplicate else "uploaded",
            boletin_id=boletin.id,
            file_hash=file_hash,
            file_size_bytes=file_size,
            duplicate_of=boletin.filename if is_duplicate else None
        )
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Failed to download: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/from-urls", response_model=BatchUploadResponse)
async def download_from_urls(
    request: BatchURLDownloadRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Download multiple PDFs from URLs with rate limiting.
    
    Epic 1.3 - Batch URL download
    
    Features:
    - Downloads from multiple URLs sequentially
    - Rate limiting (1 second between requests)
    - Automatic deduplication
    - Returns summary of all downloads
    
    Example:
    ```json
    {
        "urls": [
            "https://example.com/doc1.pdf",
            "https://example.com/doc2.pdf"
        ],
        "fuente": "provincial"
    }
    ```
    """
    if not request.urls:
        raise HTTPException(status_code=400, detail="No URLs provided")
    
    MAX_URLS = 20
    if len(request.urls) > MAX_URLS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_URLS} URLs per request"
        )
    
    results = []
    uploaded = 0
    duplicates = 0
    failed = 0
    
    for idx, url in enumerate(request.urls):
        # Rate limiting: 1 second between requests
        if idx > 0:
            await asyncio.sleep(1.0)
        
        try:
            # Download each URL
            download_request = DownloadFromURLRequest(url=url, fuente=request.fuente)
            result = await download_from_url(download_request, db)
            
            results.append(result)
            
            if result.status == "uploaded":
                uploaded += 1
            elif result.status == "duplicate":
                duplicates += 1
            else:
                failed += 1
        
        except Exception as e:
            results.append(UploadResult(
                filename=url.split('/')[-1],
                status="failed",
                error=str(e)
            ))
            failed += 1
    
    return BatchUploadResponse(
        total=len(request.urls),
        uploaded=uploaded,
        duplicates=duplicates,
        failed=failed,
        results=results
    )
