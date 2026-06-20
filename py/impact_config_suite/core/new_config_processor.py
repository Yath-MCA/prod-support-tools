import os
import xml.etree.ElementTree as ET
from datetime import datetime
import re
import time

class NewConfigProcessor:
    def __init__(self):
        pass

    def rename_covers(self, folder_path, log_callback=None):
        """Rename cover files: remove _Cover and standardize extensions"""
        if log_callback is None:
            log_callback = print
            
        renamed_count = 0
        
        if not os.path.exists(folder_path):
            log_callback(f"❌ Folder not found: {folder_path}")
            return 0
            
        for filename in os.listdir(folder_path):
            old_path = os.path.join(folder_path, filename)
            
            # Skip directories
            if os.path.isdir(old_path):
                continue
            
            new_name = filename
            
            # Case 1: Remove "_Cover" (case-insensitive)
            if re.search(r'_cover', new_name, re.IGNORECASE):
                new_name = re.sub(r'_cover', '', new_name, flags=re.IGNORECASE)
            
            # Case 2: Rename extension from .PNG to .png (case-sensitive)
            if new_name.endswith(".PNG"):
                new_name = new_name[:-4] + ".png"
            
            # Only rename if name has changed
            if new_name != filename:
                new_path = os.path.join(folder_path, new_name)
                try:
                    os.rename(old_path, new_path)
                    log_callback(f"✅ Renamed: {filename} → {new_name}")
                    renamed_count += 1
                    time.sleep(0.1)  # Small delay for filesystem sync
                except OSError as e:
                    log_callback(f"❌ Error renaming {filename}: {e}")
        
        return renamed_count

    def merge_xml(self, config_folder_path, prefix="YA", log_callback=None):
        """Merge multiple XML files into a single combined XML file"""
        if log_callback is None:
            log_callback = print
            
        folder_path = config_folder_path
        output_file = os.path.join(folder_path, 'combined_output.xml')
        
        if not os.path.exists(folder_path):
            log_callback(f"❌ Folder not found: {folder_path}")
            return False
            
        # Generate copy-by attribute with current date
        current_date = datetime.now()
        date_string = current_date.strftime("%d_%b_%y")  # Format: DD_MMM_YY
        copy_by_value = f"{prefix}_{date_string}"
        
        log_callback(f"📅 Using copy-by attribute: {copy_by_value}")
        
        # Create a new root element for the combined XML
        combined_root = ET.Element('CombinedConfigs')
        processed_count = 0
        
        # Loop through each XML file
        for filename in os.listdir(folder_path):
            if filename.lower().endswith('.xml') and filename != 'combined_output.xml':
                file_path = os.path.join(folder_path, filename)
                try:
                    tree = ET.parse(file_path)
                    root = tree.getroot()
                    # Add attribute to the root element of this individual XML
                    root.set('copy-by', copy_by_value)
                    # Append the modified root to the combined root
                    combined_root.append(root)
                    log_callback(f"✅ Processed: {filename}")
                    processed_count += 1
                except ET.ParseError as e:
                    log_callback(f"❌ Skipping {filename} due to parse error: {e}")
        
        if processed_count == 0:
            log_callback(f"⚠️ No XML files found to merge")
            return False
        
        # Build final tree and write to file
        combined_tree = ET.ElementTree(combined_root)
        combined_tree.write(output_file, encoding='utf-8', xml_declaration=True)
        log_callback(f"✅ Combined XML saved to: {output_file}")
        return True

    def create_css_from_covers(self, cover_folder_path, jira_ticket, log_callback=None):
        """Create individual CSS files for each cover image file"""
        if log_callback is None:
            log_callback = print
            
        folder_path = cover_folder_path
        
        # Common image extensions
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg'}
        
        # Check if folder exists
        if not os.path.exists(folder_path):
            log_callback(f"❌ Folder not found: {folder_path}")
            return 0
        
        cover_files = []
        
        # Loop through all files in the cover folder
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            
            # Skip directories
            if os.path.isdir(file_path):
                continue
            
            # Get file extension
            name, ext = os.path.splitext(filename)
            
            # Only process image files
            if ext.lower() in image_extensions:
                cover_files.append((filename, name, ext))
        
        # Sort files for consistent processing
        cover_files.sort()
        
        if not cover_files:
            log_callback(f"⚠️ No image files found in: {folder_path}")
            return 0
        
        log_callback(f"📊 Found {len(cover_files)} cover files")
        
        # Generate individual CSS files
        created_files = []
        for filename, name_without_ext, ext in cover_files:
            # Use the exact filename (without extension) for CSS filename
            css_filename = f"{name_without_ext}.css"
            css_file_path = os.path.join(folder_path, css_filename)
            
            # Create CSS content
            css_content = f"""/* Auto-generated CSS for cover: {filename} */
/* Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} */
/* Mantis Ticket: {jira_ticket} */

div.ref .mixed-citation .source {{
    font-style: italic !important;
}}

div.ref .mixed-citation .etal {{
    font-style: italic !important;
}}

div.ref .mixed-citation .volume {{
    font-style: bold !important;
}}

div.ref .mixed-citation .year {{
    font-style: bold !important;
}}
"""
            
            # Write individual CSS file
            try:
                with open(css_file_path, 'w', encoding='utf-8') as f:
                    f.write(css_content)
                
                created_files.append(css_filename)
                log_callback(f"✅ Created: {css_filename}")
                
            except Exception as e:
                log_callback(f"❌ Error creating {css_filename}: {e}")
        
        # Create a master index CSS file that imports all individual CSS files
        if created_files:
            master_css_path = os.path.join(folder_path, 'covers-master.css')
            try:
                with open(master_css_path, 'w', encoding='utf-8') as f:
                    f.write(f"/* Master CSS file - imports all cover CSS files */\n")
                    f.write(f"/* Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} */\n")
                    f.write(f"/* Mantis Ticket: {jira_ticket} */\n")
                    f.write(f"/* Total files: {len(created_files)} */\n\n")
                    
                    for css_file in created_files:
                        f.write(f"@import url('./{css_file}');\n")
                
                log_callback(f"📋 Created master file: covers-master.css")
                
            except Exception as e:
                log_callback(f"❌ Error creating master CSS file: {e}")
        
        return len(created_files)
