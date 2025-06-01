import os
import hashlib
import time
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Set, Optional, Generator, Tuple
import pandas as pd

from pdf_similarity import calculate_pdf_similarity

@dataclass
class FileInfo:
    """Class for storing file information"""
    path: str
    name: str
    size: int
    modified: datetime
    content_hash: Optional[str] = None
    similarity_group: Optional[str] = None

class FileScanner:
    """Handles file scanning, hashing, and duplicate detection"""
    
    def __init__(self, base_directory: str, include_subdirs: bool = True, 
                 similarity_threshold: float = 1.0, 
                 file_extensions: Optional[List[str]] = None):
        """
        Initialize the file scanner.
        
        Args:
            base_directory: Directory to scan for duplicates
            include_subdirs: Whether to scan subdirectories
            similarity_threshold: Threshold for considering PDFs similar (0.0-1.0)
            file_extensions: List of file extensions to include, None for all
        """
        self.base_directory = os.path.abspath(base_directory)
        self.include_subdirs = include_subdirs
        self.similarity_threshold = similarity_threshold
        self.file_extensions = file_extensions
        
        # File inventory and duplicate groups
        self.file_inventory: List[FileInfo] = []
        self.duplicate_map: Dict[str, List[FileInfo]] = {}
        self.name_map: Dict[str, List[FileInfo]] = {}
        self.similarity_groups: Dict[str, List[FileInfo]] = {}
    
    def inventory_files(self) -> None:
        """
        Create an inventory of all files in the base directory (and subdirectories if enabled).
        """
        self.file_inventory = []
        
        for root, _, files in os.walk(self.base_directory):
            # Skip subdirectories if not included
            if not self.include_subdirs and root != self.base_directory:
                continue
                
            for file_name in files:
                file_path = os.path.join(root, file_name)
                
                # Skip if file doesn't have one of the specified extensions
                if self.file_extensions:
                    ext = os.path.splitext(file_name)[1].lower()
                    if ext not in self.file_extensions:
                        continue
                
                try:
                    # Get file stats
                    file_stat = os.stat(file_path)
                    
                    # Create FileInfo object
                    file_info = FileInfo(
                        path=file_path,
                        name=file_name,
                        size=file_stat.st_size,
                        modified=datetime.fromtimestamp(file_stat.st_mtime),
                        content_hash=None
                    )
                    
                    self.file_inventory.append(file_info)
                    
                    # Add to name map for tracking files with identical names
                    if file_name not in self.name_map:
                        self.name_map[file_name] = []
                    self.name_map[file_name].append(file_info)
                    
                except (FileNotFoundError, PermissionError) as e:
                    # Skip files that can't be accessed
                    continue
    
    def process_files(self) -> Generator[Tuple[FileInfo, str], None, None]:
        """
        Process all files in the inventory - calculate hashes and find duplicates.
        Yields file info and hash for each processed file.
        """
        for file_info in self.file_inventory:
            # Calculate content hash
            try:
                file_hash = self._calculate_file_hash(file_info.path)
                file_info.content_hash = file_hash
                
                # Add to duplicate map
                if file_hash not in self.duplicate_map:
                    self.duplicate_map[file_hash] = []
                self.duplicate_map[file_hash].append(file_info)
                
                yield file_info, file_hash
            
            except (FileNotFoundError, PermissionError, IOError):
                # Skip files that can't be accessed
                continue
        
        # After all files are processed, find PDF similarity groups
        self._group_similar_pdfs()
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate MD5 hash for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            String representation of the file's hash
        """
        # Use buffer to efficiently hash large files
        buffer_size = 65536  # 64kb chunks
        md5_hash = hashlib.md5()
        
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(buffer_size)
                if not data:
                    break
                md5_hash.update(data)
        
        return md5_hash.hexdigest()
    
    def _group_similar_pdfs(self) -> None:
        """
        Group PDF files that have similar content but different hashes.
        Uses the similarity threshold to determine if two PDFs are similar.
        """
        # Find all PDF files
        pdf_files = [f for f in self.file_inventory 
                     if f.path.lower().endswith('.pdf')]
        
        # Skip if no PDFs
        if not pdf_files:
            return
        
        # Group PDFs by name first to reduce comparison space
        for name, files in self.name_map.items():
            if not name.lower().endswith('.pdf') or len(files) <= 1:
                continue
                
            # Compare each pair of PDFs with the same name
            for i in range(len(files)):
                for j in range(i + 1, len(files)):
                    # Skip if they have the same hash (exact duplicates)
                    if files[i].content_hash == files[j].content_hash:
                        continue
                    
                    # Calculate similarity
                    try:
                        similarity = calculate_pdf_similarity(files[i].path, files[j].path)
                        
                        # If similarity exceeds threshold, group them
                        if similarity >= self.similarity_threshold:
                            # Create or assign similarity group
                            group_id = files[i].similarity_group or files[j].similarity_group or f"sim_{hash(name)}_{i}_{j}"
                            files[i].similarity_group = group_id
                            files[j].similarity_group = group_id
                            
                            # Add to similarity groups
                            if group_id not in self.similarity_groups:
                                self.similarity_groups[group_id] = []
                            
                            if files[i] not in self.similarity_groups[group_id]:
                                self.similarity_groups[group_id].append(files[i])
                            if files[j] not in self.similarity_groups[group_id]:
                                self.similarity_groups[group_id].append(files[j])
                    except Exception:
                        # Skip on error during PDF comparison
                        continue
    
    def get_duplicate_groups(self) -> Dict[str, List[FileInfo]]:
        """
        Get groups of duplicate files based on content hash and similarity.
        
        Returns:
            Dictionary mapping group IDs to lists of file information
        """
        results = {}
        
        # Add content hash based duplicates
        for hash_value, files in self.duplicate_map.items():
            if len(files) > 1:  # Only include actual duplicates
                results[hash_value] = files
        
        # Add similarity based duplicates
        for group_id, files in self.similarity_groups.items():
            if len(files) > 1:  # Only include actual duplicates
                results[group_id] = files
        
        return results
    
    def get_identical_names(self) -> Dict[str, List[FileInfo]]:
        """
        Get files with identical names but potentially different content.
        
        Returns:
            Dictionary mapping filenames to lists of file information
        """
        return {
            name: files for name, files in self.name_map.items()
            if len(files) > 1
        }
    
    def get_statistics(self) -> Dict[str, any]:
        """
        Get statistics about the scan results.
        
        Returns:
            Dictionary with various statistics
        """
        total_files = len(self.file_inventory)
        exact_duplicates = sum(len(files) - 1 for files in self.duplicate_map.values() if len(files) > 1)
        similar_files = sum(len(files) - 1 for files in self.similarity_groups.values() if len(files) > 1)
        identical_names = sum(len(files) - 1 for files in self.name_map.values() if len(files) > 1)
        
        duplicate_groups = len([k for k, v in self.duplicate_map.items() if len(v) > 1])
        similarity_groups = len(self.similarity_groups)
        
        # Total space used by duplicates
        duplicate_space = sum(
            sum(f.size for f in files[1:])  # Skip first file in each group
            for files in self.duplicate_map.values() 
            if len(files) > 1
        )
        
        return {
            "total_files": total_files,
            "exact_duplicates": exact_duplicates,
            "similar_files": similar_files,
            "identical_names": identical_names,
            "duplicate_groups": duplicate_groups,
            "similarity_groups": similarity_groups,
            "space_wasted": duplicate_space,
            "space_saved_potential": duplicate_space
        }