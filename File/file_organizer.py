import os
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from file_scanner import FileInfo
import utils

class FileOrganizer:
    """Handles organization of duplicate files into structured folders"""
    
    def __init__(self, duplicate_groups: Dict[str, List[FileInfo]], 
                 destination_dir: str, keep_original: bool = True):
        self.duplicate_groups = duplicate_groups
        self.destination_dir = destination_dir
        self.keep_original = keep_original
        self.operations_log = []
        
    def generate_organization_plan(self) -> Dict[str, List[Dict[str, str]]]:
        """Generate organization plan without executing"""
        plan = {}
        
        for group_id, files in self.duplicate_groups.items():
            if len(files) <= 1:
                continue
                
            # Create folder name based on file type and group
            first_file = files[0]
            file_ext = Path(first_file.path).suffix
            folder_name = f"Duplicates_{first_file.name}_{group_id[:8]}"
            
            plan[folder_name] = []
            
            # Keep one file in original location if specified
            files_to_move = files[1:] if self.keep_original else files
            
            for file_info in files_to_move:
                source = file_info.path
                dest_folder = os.path.join(self.destination_dir, folder_name)
                destination = os.path.join(dest_folder, file_info.name)
                
                plan[folder_name].append({
                    "source": source,
                    "destination": destination,
                    "size": file_info.size
                })
        
        return plan
    
    def execute_organization_plan(self, move_files: bool = True) -> Dict[str, Any]:
        """Execute the organization plan"""
        plan = self.generate_organization_plan()
        stats = {"moved": 0, "copied": 0, "errors": 0, "total_size": 0}
        
        for folder_name, operations in plan.items():
            dest_folder = os.path.join(self.destination_dir, folder_name)
            
            # Create destination folder
            try:
                os.makedirs(dest_folder, exist_ok=True)
            except Exception as e:
                stats["errors"] += 1
                continue
            
            for op in operations:
                try:
                    if move_files:
                        shutil.move(op["source"], op["destination"])
                        stats["moved"] += 1
                    else:
                        shutil.copy2(op["source"], op["destination"])
                        stats["copied"] += 1
                    
                    stats["total_size"] += op["size"]
                    
                except Exception as e:
                    stats["errors"] += 1
        
        return stats
    
    def get_summary(self) -> Dict[str, Any]:
        """Get organization summary"""
        total_groups = len(self.duplicate_groups)
        total_files = sum(len(files) for files in self.duplicate_groups.values())
        
        return {
            "total_groups": total_groups,
            "total_files": total_files,
            "destination": self.destination_dir
        }