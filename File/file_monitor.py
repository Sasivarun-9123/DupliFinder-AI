import os
import time
from datetime import datetime
from typing import List, Dict, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from file_scanner import FileScanner, FileInfo

class FileEventHandler(FileSystemEventHandler):
    """Handles file system events for monitoring"""
    
    def __init__(self, monitor):
        self.monitor = monitor
        
    def on_created(self, event):
        if not event.is_directory:
            self.monitor.process_new_file(event.src_path)
            
    def on_moved(self, event):
        if not event.is_directory:
            self.monitor.process_new_file(event.dest_path)

class FileMonitor:
    """Monitors directories for new files and detects duplicates"""
    
    def __init__(self, directory: str, auto_organize: bool = True,
                 organize_path: Optional[str] = None):
        self.directory = directory
        self.auto_organize = auto_organize
        self.organize_path = organize_path or os.path.join(directory, "Auto_Organized")
        
        self.observer = Observer()
        self.event_handler = FileEventHandler(self)
        self.activity_log = []
        self.known_files = {}
        
        # Initial scan to build inventory
        self._build_initial_inventory()
    
    def _build_initial_inventory(self):
        """Build initial file inventory"""
        scanner = FileScanner(self.directory, include_subdirs=True)
        scanner.inventory_files()
        
        for file_info in scanner.file_inventory:
            file_hash = scanner._calculate_file_hash(file_info.path)
            self.known_files[file_hash] = file_info
    
    def start_monitoring(self):
        """Start monitoring the directory"""
        self.observer.schedule(self.event_handler, self.directory, recursive=True)
        self.observer.start()
        self.log_activity("Started monitoring directory")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.observer.stop()
        self.observer.join()
        self.log_activity("Stopped monitoring directory")
    
    def process_new_file(self, file_path: str):
        """Process a newly detected file"""
        try:
            # Wait a bit for file to be completely written
            time.sleep(1)
            
            # Calculate hash of new file
            scanner = FileScanner(os.path.dirname(file_path))
            file_hash = scanner._calculate_file_hash(file_path)
            
            # Check if it's a duplicate
            if file_hash in self.known_files:
                duplicate_file = self.known_files[file_hash]
                self.log_activity(f"Duplicate detected: {os.path.basename(file_path)} matches {duplicate_file.name}")
                
                if self.auto_organize:
                    self._organize_duplicate(file_path, duplicate_file)
            else:
                # Add to known files
                file_stat = os.stat(file_path)
                file_info = FileInfo(
                    path=file_path,
                    name=os.path.basename(file_path),
                    size=file_stat.st_size,
                    modified=datetime.fromtimestamp(file_stat.st_mtime),
                    content_hash=file_hash
                )
                self.known_files[file_hash] = file_info
                self.log_activity(f"New unique file: {os.path.basename(file_path)}")
                
        except Exception as e:
            self.log_activity(f"Error processing {file_path}: {str(e)}")
    
    def _organize_duplicate(self, file_path: str, original_file: FileInfo):
        """Organize a duplicate file"""
        try:
            # Create organize directory
            os.makedirs(self.organize_path, exist_ok=True)
            
            # Move duplicate to organized folder
            filename = os.path.basename(file_path)
            dest_path = os.path.join(self.organize_path, filename)
            
            # Handle name conflicts
            counter = 1
            while os.path.exists(dest_path):
                name, ext = os.path.splitext(filename)
                dest_path = os.path.join(self.organize_path, f"{name}_{counter}{ext}")
                counter += 1
            
            os.rename(file_path, dest_path)
            self.log_activity(f"Organized duplicate: {filename} → {dest_path}")
            
        except Exception as e:
            self.log_activity(f"Failed to organize duplicate: {str(e)}")
    
    def log_activity(self, message: str):
        """Log activity with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.activity_log.append({
            "timestamp": timestamp,
            "event": message
        })
    
    def get_activity_log(self) -> List[Dict[str, str]]:
        """Get activity log"""
        return self.activity_log