import os
import shutil
import hashlib
from typing import List, Dict, Tuple, Any, Optional
from pathlib import Path
import pandas as pd
import humanize
from datetime import datetime

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in a human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable size string
    """
    return humanize.naturalsize(size_bytes)

def format_timestamp(timestamp: float) -> str:
    """
    Format a timestamp into a human-readable date and time.
    
    Args:
        timestamp: Unix timestamp
        
    Returns:
        Formatted date/time string
    """
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def get_file_extension(file_path: str) -> str:
    """
    Get the file extension from a path.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File extension (lowercase, with dot)
    """
    return os.path.splitext(file_path)[1].lower()

def is_same_file(file1_path: str, file2_path: str) -> bool:
    """
    Check if two files are the same based on content.
    
    Args:
        file1_path: Path to the first file
        file2_path: Path to the second file
        
    Returns:
        True if files have identical content, False otherwise
    """
    if not os.path.exists(file1_path) or not os.path.exists(file2_path):
        return False
    
    # Fast check: if sizes differ, files are different
    if os.path.getsize(file1_path) != os.path.getsize(file2_path):
        return False
    
    # Compare hashes
    hash1 = calculate_file_hash(file1_path)
    hash2 = calculate_file_hash(file2_path)
    
    return hash1 == hash2

def calculate_file_hash(file_path: str, algorithm: str = 'md5') -> str:
    """
    Calculate hash for a file.
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use
        
    Returns:
        Hexadecimal hash string
    """
    if algorithm.lower() == 'md5':
        hash_obj = hashlib.md5()
    elif algorithm.lower() == 'sha1':
        hash_obj = hashlib.sha1()
    elif algorithm.lower() == 'sha256':
        hash_obj = hashlib.sha256()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    
    buffer_size = 65536  # 64kb chunks
    
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(buffer_size)
            if not data:
                break
            hash_obj.update(data)
    
    return hash_obj.hexdigest()

def get_common_directory(file_paths: List[str]) -> str:
    """
    Find the common parent directory for a list of file paths.
    
    Args:
        file_paths: List of file paths
        
    Returns:
        Common parent directory path
    """
    if not file_paths:
        return ""
    
    # Convert to Path objects
    paths = [Path(p) for p in file_paths]
    
    # Get common parent
    common_parent = os.path.commonpath([str(p) for p in paths])
    
    return common_parent

def safe_file_operation(operation_fn, *args, **kwargs) -> Tuple[bool, Optional[str]]:
    """
    Safely execute a file operation with error handling.
    
    Args:
        operation_fn: Function to execute
        *args, **kwargs: Arguments to pass to the function
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        operation_fn(*args, **kwargs)
        return True, None
    except Exception as e:
        return False, str(e)

def create_duplicate_summary(duplicate_groups: Dict[str, List[Any]]) -> pd.DataFrame:
    """
    Create a summary dataframe for duplicate groups.
    
    Args:
        duplicate_groups: Dictionary of duplicate groups
        
    Returns:
        Pandas DataFrame with summary information
    """
    summary_data = []
    
    for group_id, files in duplicate_groups.items():
        if len(files) <= 1:
            continue
            
        group_size = sum(f.size for f in files)
        waste_size = sum(f.size for f in files[1:])  # All but the first file
        
        summary_data.append({
            'Group ID': group_id[:8],
            'Files': len(files),
            'Total Size': format_file_size(group_size),
            'Wasted Space': format_file_size(waste_size),
            'File Type': get_file_extension(files[0].path) if files else ''
        })
    
    return pd.DataFrame(summary_data)
