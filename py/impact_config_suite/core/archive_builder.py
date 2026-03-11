## Additional File: core/archive_builder.py

import os
import zipfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from PIL import Image
import logging


class ArchiveBuilder:
    """Advanced archive builder with folder and image support"""

    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def create_archive(self, source_dir: str, file_id: str,
                       archive_type: str = "files",  # "files" or "folders"
                       include_images: bool = True,
                       selected_items: Optional[List[str]] = None) -> str:
        """Create archive with flexible options"""

        archive_path = os.path.join(
            self.config["auto_upload"].get("archive_location", "."),
            f"{file_id}.zip"
        )

        if archive_type == "folders":
            return self._create_folder_archive(source_dir, file_id, archive_path,
                                               include_images, selected_items)
        else:
            return self._create_file_archive(source_dir, file_id, archive_path,
                                             include_images, selected_items)

    def _create_file_archive(self, source_dir: str, file_id: str, archive_path: str,
                             include_images: bool, selected_items: List[str]) -> str:
        """Create traditional file-based archive"""
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            files = self._get_files_to_archive(source_dir, include_images, selected_items)

            for file_path in files:
                file_extension = Path(file_path).suffix
                new_filename = f"{file_id}{file_extension}"

                # Optimize images if needed
                if include_images and self._is_image_file(file_path):
                    optimized_path = self._optimize_image(file_path, file_id)
                    if optimized_path:
                        zipf.write(optimized_path, new_filename)
                        os.remove(optimized_path)  # Cleanup temp file
                    else:
                        zipf.write(file_path, new_filename)
                else:
                    zipf.write(file_path, new_filename)

        self.logger.info(f"File archive created: {archive_path}")
        return archive_path

    def _create_folder_archive(self, source_dir: str, file_id: str, archive_path: str,
                               include_images: bool, selected_items: List[str]) -> str:
        """Create archive preserving folder structure"""
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                # Filter based on selected items
                if selected_items:
                    dirs[:] = [d for d in dirs if d in selected_items]
                    files = [f for f in files if f in selected_items or
                             any(f.startswith(folder) for folder in selected_items)]

                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, source_dir)

                    # Skip config file
                    if file == self.config["file_handling"]["config_file"]:
                        continue

                    # Handle image optimization
                    if include_images and self._is_image_file(file_path):
                        optimized_path = self._optimize_image(file_path, file_id)
                        if optimized_path:
                            zipf.write(optimized_path, rel_path)
                            os.remove(optimized_path)
                        else:
                            zipf.write(file_path, rel_path)
                    else:
                        zipf.write(file_path, rel_path)

        self.logger.info(f"Folder archive created: {archive_path}")
        return archive_path

    def _get_files_to_archive(self, source_dir: str, include_images: bool,
                              selected_items: List[str]) -> List[str]:
        """Get list of files to include in archive"""
        all_files = []
        exclude_files = self.config["file_handling"]["exclude_files"]

        for item in os.listdir(source_dir):
            item_path = os.path.join(source_dir, item)
            if os.path.isfile(item_path) and item not in exclude_files:
                if selected_items and item not in selected_items:
                    continue
                if not include_images and self._is_image_file(item_path):
                    continue
                all_files.append(item_path)

        return all_files

    def _is_image_file(self, file_path: str) -> bool:
        """Check if file is an image"""
        image_extensions = self.config["file_handling"].get(
            "supported_images", [".png", ".jpg", ".jpeg", ".gif", ".bmp"]
        )
        return Path(file_path).suffix.lower() in image_extensions

    def _optimize_image(self, image_path: str, file_id: str) -> Optional[str]:
        """Optimize image for archiving"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')

                # Resize if too large
                max_size = self.config["file_handling"].get("max_image_size", 2048)
                if max(img.size) > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

                # Save optimized version
                temp_path = f"temp_{file_id}_{Path(image_path).name}"
                quality = self.config["file_handling"].get("image_quality", 85)
                img.save(temp_path, quality=quality, optimize=True)

                return temp_path
        except Exception as e:
            self.logger.warning(f"Image optimization failed for {image_path}: {e}")
            return None
