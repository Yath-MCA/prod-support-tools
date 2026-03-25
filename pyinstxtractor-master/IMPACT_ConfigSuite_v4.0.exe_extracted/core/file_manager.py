import os
import shutil
import zipfile
import glob
from typing import Tuple, Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

class FileManager:
    def __init__(self, config: Any):
        # Handle both dict and ConfigLoader object
        self.config_obj = config
        self.config = config.config if hasattr(config, 'config') else config
        
    def cleanup_existing_archives(self, folder_path: str, file_id: str = None) -> int:
        """
        Remove existing archive files from the folder
        Returns number of files deleted
        """
        try:
            # Look for zip files
            zip_pattern = os.path.join(folder_path, "*.zip")
            zip_files = glob.glob(zip_pattern)
            
            # Also look for archives with specific file_id pattern if provided
            if file_id:
                specific_pattern = os.path.join(folder_path, f"{file_id}*.zip")
                specific_files = glob.glob(specific_pattern)
                zip_files.extend(specific_files)
            
            # Remove duplicates
            zip_files = list(set(zip_files))
            
            deleted_count = 0
            for zip_file in zip_files:
                try:
                    os.remove(zip_file)
                    deleted_count += 1
                    print(f"Removed existing archive: {os.path.basename(zip_file)}")
                except Exception as e:
                    print(f"Warning: Could not remove {zip_file}: {e}")
            
            return deleted_count
            
        except Exception as e:
            print(f"Error cleaning up archives: {e}")
            return 0
    
    def rename_files_and_create_archive(self, folder_path: str, file_id: str, 
                                      exclude_patterns: List[str] = None,
                                      cleanup_existing: bool = True) -> Optional[str]:
        """
        Rename all files in folder and create zip archive
        Excludes files matching patterns in exclude_patterns
        Optionally cleans up existing archives first
        """
        if exclude_patterns is None:
            exclude_patterns = [".backup"]  # Default exclude backup files
            
        try:
            # Clean up existing archives if requested
            if cleanup_existing:
                deleted_count = self.cleanup_existing_archives(folder_path, file_id)
                if deleted_count > 0:
                    print(f"Cleaned up {deleted_count} existing archive files")
            
            # Get all files in the folder recursively
            all_files = []
            
            for root, dirs, files in os.walk(folder_path):
                # Filter out backup files and excluded patterns
                files = [f for f in files if not any(pattern in f for pattern in exclude_patterns)]
                dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]
                
                for file in files:
                    file_full_path = os.path.join(root, file)
                    # Skip the archive we're about to create if it exists
                    archive_name = f"{file_id}.zip"
                    if file == archive_name:
                        continue
                    all_files.append(file_full_path)
            
            if not all_files:
                print("No files found to archive")
                return None
            
            # Create archive path in the source folder
            archive_dir = folder_path
            archive_path = os.path.join(archive_dir, f"{file_id}.zip")
            
            # Create zip archive
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add files with new names
                for file_path in all_files:
                    # Skip the archive we're about to create
                    if file_path == archive_path:
                        continue
                        
                    # Get file extension
                    file_ext = Path(file_path).suffix
                    
                    # Create new filename: file_id + original_extension
                    new_filename = f"{file_id}{file_ext}"
                    
                    # Add to zip with new name
                    zipf.write(file_path, new_filename)
            
            print(f"Archive created successfully: {archive_path}")
            return archive_path
            
        except Exception as e:
            print(f"Error creating archive: {e}")
            return None
    
    def rename_files_and_create_archive_preserve_structure(self, folder_path: str, file_id: str, 
                                                         exclude_patterns: List[str] = None,
                                                         cleanup_existing: bool = True) -> Optional[str]:
        """
        Create archive preserving the original folder structure
        """
        if exclude_patterns is None:
            exclude_patterns = [".backup"]
            
        try:
            # Clean up existing archives if requested
            if cleanup_existing:
                self.cleanup_existing_archives(folder_path, file_id)
            
            archive_dir = folder_path
            archive_path = os.path.join(archive_dir, f"{file_id}.zip")
            
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(folder_path):
                    # Filter out backup files and excluded patterns
                    files = [f for f in files if not any(pattern in f for pattern in exclude_patterns)]
                    dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]
                    
                    for file in files:
                        file_path = os.path.join(root, file)
                        
                        # Skip the archive we're about to create
                        if file_path == archive_path:
                            continue
                            
                        # Preserve folder structure
                        rel_path = os.path.relpath(file_path, folder_path)
                        zipf.write(file_path, rel_path)
            
            print(f"Archive created with preserved structure: {archive_path}")
            return archive_path
            
        except Exception as e:
            print(f"Error creating archive with structure: {e}")
            return None
    
    def get_folder_summary(self, folder_path: str) -> Dict[str, int]:
        """Get summary of files in folder (excluding backups and archives)"""
        if not os.path.exists(folder_path):
            return {"total_files": 0, "total_folders": 0, "xml_files": 0, "pdf_files": 0, "archive_files": 0}
        
        total_files = 0
        total_folders = 0
        xml_files = 0
        pdf_files = 0
        archive_files = 0
        
        for root, dirs, files in os.walk(folder_path):
            # Exclude backup files
            files = [f for f in files if ".backup" not in f]
            dirs = [d for d in dirs if ".backup" not in d]
            
            total_folders += len(dirs)
            total_files += len(files)
            
            for file in files:
                if file.endswith('.xml'):
                    xml_files += 1
                elif file.endswith('.pdf'):
                    pdf_files += 1
                elif file.endswith('.zip'):
                    archive_files += 1
        
        return {
            "total_files": total_files,
            "total_folders": total_folders,
            "xml_files": xml_files,
            "pdf_files": pdf_files,
            "archive_files": archive_files
        }
    
    def create_backup(self, file_path: str) -> str:
        """Create backup of a file"""
        backup_path = file_path + self.config["file_handling"]["backup_suffix"]
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    def cleanup_temp_files(self, folder_path: str, file_id: str):
        """Cleanup temporary files"""
        temp_dir = os.path.join(folder_path, f"temp_{file_id}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    def get_existing_archives(self, folder_path: str) -> List[str]:
        """Get list of existing archive files in folder"""
        zip_pattern = os.path.join(folder_path, "*.zip")
        return glob.glob(zip_pattern)
