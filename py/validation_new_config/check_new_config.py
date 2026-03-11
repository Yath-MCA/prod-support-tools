import os
import xml.etree.ElementTree as ET
from datetime import datetime
import re
import time

# Version info
VERSION = "1.0.7"
BUILD_TIME = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Import validation module
try:
    from config_validator import validate_folder, print_validation_report, save_validation_report
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False
    print("⚠️ Warning: config_validator module not found. Validation will be skipped.")

# Import generator module
try:
    from config_generator import generate_html_form
    GENERATOR_AVAILABLE = True
except ImportError:
    GENERATOR_AVAILABLE = False


def renameCover(folder_path):
    """Rename cover files: remove _Cover and standardize extensions"""
    renamed_count = 0
    
    for filename in os.listdir(folder_path):
        old_path = os.path.join(folder_path, filename)
        
        # Skip directories
        if os.path.isdir(old_path):
            continue
        
        new_name = filename
        
        # Case 1: Remove "_Cover" (case-insensitive)
        if re.search(r'_cover', new_name, re.IGNORECASE):
            print(f"   🔎 Found '_cover' in {new_name}")
            new_name = re.sub(r'_cover', '', new_name, flags=re.IGNORECASE)
            print(f"   ✂️  Removed _Cover → {new_name}")
        
        # Case 2: Rename extension from .PNG to .png (case-sensitive)
        if new_name.endswith(".PNG"):
            new_name = new_name[:-4] + ".png"
            print(f"   Converted .PNG to .png → {new_name}")
        
        # Only rename if name has changed
        if new_name != filename:
            new_path = os.path.join(folder_path, new_name)
            try:
                os.rename(old_path, new_path)
                print(f"   ✅ Renamed: {filename} → {new_name}")
                renamed_count += 1
                time.sleep(0.1)  # Small delay for filesystem sync
            except OSError as e:
                print(f"   ❌ Error renaming {filename}: {e}")
    
    # Wait for filesystem to fully sync after all renames
    if renamed_count > 0:
        time.sleep(0.5)
        print(f"\n   📊 Summary: {renamed_count} file(s) renamed")
    else:
        print(f"\n   📊 No files needed renaming")


def mergeXML(config_folder_path, prefix="YA"):
    """Merge multiple XML files into a single combined XML file"""
    folder_path = config_folder_path
    output_file = os.path.join(folder_path, 'combined_output.xml')
    
    # Generate copy-by attribute with current date
    current_date = datetime.now()
    date_string = current_date.strftime("%d_%b_%y")  # Format: DD_MMM_YY
    copy_by_value = f"{prefix}_{date_string}"
    
    print(f"📅 Using copy-by attribute: {copy_by_value}")
    
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
                print(f"   ✅ Processed: {filename}")
                processed_count += 1
            except ET.ParseError as e:
                print(f"   ❌ Skipping {filename} due to parse error: {e}")
    
    if processed_count == 0:
        print(f"   ⚠️ No XML files found to merge")
        return
    
    # Build final tree and write to file
    combined_tree = ET.ElementTree(combined_root)
    combined_tree.write(output_file, encoding='utf-8', xml_declaration=True)
    print(f"\n✅ Combined XML saved to: {output_file}")
    print(f"   📊 Merged {processed_count} XML file(s)")


def createCSSFromCovers(cover_folder_path, jira_ticket):
    """Create individual CSS files for each cover image file"""
    folder_path = cover_folder_path
    
    # Common image extensions
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg'}
    
    # Check if folder exists
    if not os.path.exists(folder_path):
        print(f"❌ Folder not found: {folder_path}")
        return
    
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
        print(f"   ⚠️ No image files found in: {folder_path}")
        return
    
    print(f"   📊 Found {len(cover_files)} cover files")
    
    # Generate individual CSS files
    created_files = []
    for filename, name_without_ext, ext in cover_files:
        # Use the exact filename (without extension) for CSS filename
        css_filename = f"{name_without_ext}.css"
        css_file_path = os.path.join(folder_path, css_filename)
        
        print(f"   📝 Generating CSS for {filename}...")
        
        # Create CSS content (NO EXTRA INDENTATION)
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
        
        # DEBUG: Print CSS content length and preview
        print(f"   📄 CSS content length: {len(css_content)} chars, {len(css_content.splitlines())} lines")
        print(f"   📄 First 100 chars: {repr(css_content[:100])}")
        
        # Write individual CSS file
        try:
            with open(css_file_path, 'w', encoding='utf-8') as f:
                f.write(css_content)
                f.flush()
                os.fsync(f.fileno())
            
            # Delay to ensure file is fully written (PyInstaller fix)
            time.sleep(0.3)
            
            # Verify file was written correctly
            with open(css_file_path, 'r', encoding='utf-8') as f:
                written_content = f.read()
            print(f"   📄 Verified: wrote {len(written_content)} chars to {css_filename}")
            
            created_files.append(css_filename)
            print(f"   ✅ Created: {css_filename}")
            
        except Exception as e:
            print(f"   ❌ Error creating {css_filename}: {e}")
    
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
            
            print(f"\n   📋 Created master file: covers-master.css")
            print(f"   📁 Imports {len(created_files)} CSS files")
            
        except Exception as e:
            print(f"   ❌ Error creating master CSS file: {e}")
    
    print(f"\n🎨 CSS Generation Complete:")
    print(f"   ✅ Created {len(created_files)} individual CSS files")
    print(f"   📂 Location: {folder_path}")


def get_user_paths():
    """Get folder paths and user preferences from input"""
    print("=" * 60)
    print("📁 FOLDER PATH CONFIGURATION")
    print("=" * 60)
    
    # Get user prefix for copy-by attribute
    default_prefix = "YA"
    user_prefix = input(f"\n👤 Enter prefix for copy-by attribute (default: {default_prefix}): ").strip()
    if not user_prefix:
        user_prefix = default_prefix
    
    # Get Jira ticket number for CSS files
    jira_ticket = input(f"\n🎫 Enter Mantis ticket number (e.g., PROJ-1234): ").strip()
    if not jira_ticket:
        jira_ticket = "NO-TICKET"
    
    # Preview the copy-by format
    current_date = datetime.now()
    date_string = current_date.strftime("%d_%b_%y")
    preview_copy_by = f"{user_prefix}_{date_string}"
    print(f"📅 Copy-by attribute will be: {preview_copy_by}")
    print(f"🎫 Mantis ticket for CSS: {jira_ticket}")
    
    # Get base project folder
    while True:
        base_path = input("\n📂 Enter the base project folder path: ").strip()
        if base_path:
            # Remove quotes if user added them
            base_path = base_path.strip('"\'')
            if os.path.exists(base_path):
                break
            else:
                print(f"❌ Path not found: {base_path}")
                print("   Please enter a valid folder path.")
        else:
            print("❌ Please enter a folder path.")
    
    # Construct cover and config paths
    cover_path = os.path.join(base_path, 'Cover')
    config_path = os.path.join(base_path, 'config')
    
    print(f"\n📋 Detected paths:")
    print(f"   📂 Base folder: {base_path}")
    print(f"   🖼️  Cover folder: {cover_path}")
    print(f"   ⚙️  Config folder: {config_path}")
    
    # Check if paths exist
    paths_exist = True
    if not os.path.exists(cover_path):
        print(f"   ⚠️  Cover folder not found: {cover_path}")
        paths_exist = False
    if not os.path.exists(config_path):
        print(f"   ⚠️  Config folder not found: {config_path}")
        paths_exist = False
    
    if not paths_exist:
        print(f"\n❓ Some folders don't exist. Do you want to:")
        print(f"   1. Enter custom paths for Cover and Config folders")
        print(f"   2. Continue anyway (will skip missing operations)")
        choice = input("   Enter choice (1 or 2): ").strip()
        
        if choice == "1":
            # Get custom paths
            cover_path = input(f"\n🖼️  Enter Cover folder path: ").strip().strip('"\'')
            config_path = input(f"⚙️  Enter Config folder path: ").strip().strip('"\'')
    
    return cover_path, config_path, user_prefix, jira_ticket


# Run the functions
if __name__ == "__main__":
    print("=" * 60)
    print(f"🚀 IMPACT CONFIG TOOLS v{VERSION}")
    print(f"   Build Time: {BUILD_TIME}")
    print(f"   Runtime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("   Created by: YA")
    print("=" * 60)
    
    print("\n📋 Select an option:")
    print("   1. Process new journal config (rename, CSS, validate, merge)")
    print("   2. Generate HTML Config Form (create new journals via form)")
    print("   3. Validate existing config folder only")
    print("   4. Exit")
    
    choice = input("\n   Enter choice (1-4): ").strip()
    
    if choice == "2":
        # Generate HTML form
        if GENERATOR_AVAILABLE:
            print("\n🎨 GENERATING HTML CONFIG FORM")
            print("=" * 60)
            generated_path = generate_html_form()
            if generated_path:
                import webbrowser
                open_browser = input("\n🌐 Open in browser? (y/n): ").strip().lower()
                if open_browser == 'y':
                    webbrowser.open(f'file://{os.path.abspath(generated_path)}')
        else:
            print("❌ Generator module not available")
        input("\nPress Enter to exit...")
        exit(0)
    
    elif choice == "3":
        # Validate only
        if VALIDATOR_AVAILABLE:
            print("\n🔍 VALIDATION MODE")
            config_path = input("📂 Enter config folder path: ").strip().strip('"\'')
            if os.path.exists(config_path):
                result = validate_folder(config_path)
                print_validation_report(result)
                save_choice = input("\nSave report? (y/n): ").strip().lower()
                if save_choice == 'y':
                    save_validation_report(result)
            else:
                print(f"❌ Path not found: {config_path}")
        else:
            print("❌ Validator module not available")
        input("\nPress Enter to exit...")
        exit(0)
    
    elif choice == "4":
        print("👋 Goodbye!")
        exit(0)
    
    elif choice != "1":
        print("❌ Invalid choice")
        input("\nPress Enter to exit...")
        exit(1)
    
    # Choice 1: Full workflow
    cover_folder, config_folder, user_prefix, jira_ticket = get_user_paths()
    
    print(f"\n" + "=" * 60)
    print("🔄 STARTING OPERATIONS")
    print("=" * 60)
    
    # Step 1: Rename covers if cover folder exists
    if os.path.exists(cover_folder):
        print(f"\n1️⃣ Renaming cover files in: {cover_folder}")
        renameCover(cover_folder)
    else:
        print(f"\n⏭️  Skipping cover rename - folder not found: {cover_folder}")
    
    # Step 2: Generate CSS if cover folder exists
    if os.path.exists(cover_folder):
        print(f"\n2️⃣ Generating CSS from cover files...")
        createCSSFromCovers(cover_folder, jira_ticket)
    else:
        print(f"\n⏭️  Skipping CSS generation - folder not found: {cover_folder}")
    
    # Step 3: VALIDATION
    validation_passed = True
    if os.path.exists(config_folder) and VALIDATOR_AVAILABLE:
        print(f"\n3️⃣ Validating XML files in: {config_folder}")
        validation_result = validate_folder(config_folder)
        print_validation_report(validation_result)
        
        if not validation_result['valid']:
            validation_passed = False
            print("\n⚠️  VALIDATION FAILED!")
            print("   Some config values are not in the allowed list.")
            print("\n   Options:")
            print("   1. Fix the errors and re-run")
            print("   2. Continue anyway (merge XML with invalid values)")
            print("   3. Add new values to allowed list (contact admin)")
            
            choice = input("\n   Enter choice (1/2/3): ").strip()
            if choice == "2":
                validation_passed = True
                print("   ⚠️ Continuing with warnings...")
            elif choice == "3":
                print("\n   📝 To add new values, edit: allowed_values.json")
                print("   Or use: python config_validator.py --add-value")
                save_report = input("   Save validation report? (y/n): ").strip().lower()
                if save_report == 'y':
                    save_validation_report(validation_result)
            else:
                print("   🛑 Aborting. Please fix the errors and re-run.")
                save_report = input("   Save validation report? (y/n): ").strip().lower()
                if save_report == 'y':
                    save_validation_report(validation_result)
        else:
            print("   ✅ All values are valid!")
    elif not VALIDATOR_AVAILABLE:
        print(f"\n3️⃣ Skipping validation - validator module not available")
    else:
        print(f"\n⏭️  Skipping validation - folder not found: {config_folder}")
    
    # Step 4: Merge XML if config folder exists AND validation passed
    if os.path.exists(config_folder) and validation_passed:
        print(f"\n4️⃣ Merging XML files in: {config_folder}")
        mergeXML(config_folder, user_prefix)
    elif os.path.exists(config_folder):
        print(f"\n⏭️  Skipping XML merge - validation failed")
    else:
        print(f"\n⏭️  Skipping XML merge - folder not found: {config_folder}")
    
    print(f"\n" + "=" * 60)
    if validation_passed:
        print("✅ ALL OPERATIONS COMPLETED")
    else:
        print("⚠️ OPERATIONS COMPLETED WITH WARNINGS")
    print("=" * 60)
    input("\nPress Enter to exit...")
