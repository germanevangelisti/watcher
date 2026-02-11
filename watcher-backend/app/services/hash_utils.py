"""
Hash utility functions for file deduplication.
Epic 1.1 - SHA256-based deduplication
"""

import hashlib
from pathlib import Path
from typing import Union


def compute_sha256(filepath: Union[str, Path]) -> str:
    """
    Compute SHA256 hash of a file.
    
    Args:
        filepath: Path to the file
        
    Returns:
        Hexadecimal SHA256 hash string (64 characters)
        
    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    sha256 = hashlib.sha256()
    
    # Read file in chunks to handle large files efficiently
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    
    return sha256.hexdigest()


def compute_sha256_bytes(content: bytes) -> str:
    """
    Compute SHA256 hash of bytes content.
    
    Args:
        content: Bytes content to hash
        
    Returns:
        Hexadecimal SHA256 hash string (64 characters)
    """
    return hashlib.sha256(content).hexdigest()


def verify_file_hash(filepath: Union[str, Path], expected_hash: str) -> bool:
    """
    Verify that a file matches an expected SHA256 hash.
    
    Args:
        filepath: Path to the file
        expected_hash: Expected SHA256 hash (64-character hex string)
        
    Returns:
        True if file hash matches expected_hash, False otherwise
    """
    try:
        actual_hash = compute_sha256(filepath)
        return actual_hash.lower() == expected_hash.lower()
    except (FileNotFoundError, IOError):
        return False
