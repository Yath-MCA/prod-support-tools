import os
import math
import datetime
import shutil
import re
import xml.etree.ElementTree as ET

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
# These could be moved to config.py later
ROOT_FOLDER = r"D:\IMPACT"
OUTPUT_BASE = r"D:\SEARCH_API"
BATCH_SIZE = 250

def fetch_doc_ids(from_date: datetime.datetime, output_folder_suffix: str = None, root_folder: str = None):
    """
    Scans ROOT_FOLDER (or custom root_folder) for directories modified on or after from_date.
    Generates batch files in OUTPUT_BASE.
    """
    print("\n" + "="*60)
    print("🔍 FETCH DOCUMENTS - PROCESS STARTED")
    print("="*60)
    
    # Use custom root folder if provided, otherwise use default
    scan_folder = root_folder if root_folder else ROOT_FOLDER
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = output_folder_suffix if output_folder_suffix else timestamp
    output_folder = os.path.join(OUTPUT_BASE, f"BATCH_LISTS_{suffix}")
    
    print(f"📂 Creating output folder: {output_folder}")
    os.makedirs(output_folder, exist_ok=True)
    
    print(f"🔎 Scanning root: {scan_folder}")
    if root_folder:
        print(f"   🎯 Using custom path (overriding default)")
    print(f"📅 Filtering folders modified on or after: {from_date}")

    all_doc_ids = []
    scanned_count = 0
    error_count = 0
    
    try:
        print("⏳ Processing directories...")
        for d in os.listdir(scan_folder):
            scanned_count += 1
            full_path = os.path.join(scan_folder, d)
            if not os.path.isdir(full_path):
                continue
            
            try:
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(full_path))
                if mtime >= from_date:
                    all_doc_ids.append(d)
                    if len(all_doc_ids) % 50 == 0:
                        print(f"   ✓ Found {len(all_doc_ids)} matching documents so far...")
            except Exception as e:
                error_count += 1
                print(f"   ⚠️  Error reading {d}: {e}")
    except FileNotFoundError:
        print(f"❌ Error: Root folder {scan_folder} not found.")
        return [], None

    total = len(all_doc_ids)
    print(f"\n📊 Scan Summary:")
    print(f"   • Total directories scanned: {scanned_count}")
    print(f"   • Matching documents found: {total}")
    print(f"   • Errors encountered: {error_count}")
    
    if total == 0:
        print("⚠️  No documents found matching the criteria.")
        return [], output_folder

    num_batches = math.ceil(total / BATCH_SIZE)
    batch_files = []
    
    print(f"\n📦 Creating {num_batches} batch file(s)...")
    
    for i in range(num_batches):
        start = i * BATCH_SIZE + 1
        end = min((i + 1) * BATCH_SIZE, total)
        filename = f"{start}_{end}.txt"
        batch_file_path = os.path.join(output_folder, filename)
        subset = all_doc_ids[start - 1:end]
        
        with open(batch_file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(subset))
        
        batch_files.append(batch_file_path)
        print(f"   ✓ Created batch {i+1}/{num_batches}: {filename} ({len(subset)} documents)")
    
    print(f"\n✅ FETCH COMPLETED - Generated {num_batches} batch file(s)")
    print(f"📁 Output folder: {output_folder}")
    print("="*60 + "\n")
    
    return batch_files, output_folder

def copy_files_for_batch(batch_file_path: str, root_folder: str = None, dest_root: str = None):
    """
    Reads doc_ids from batch_file_path and copies relevant files to dest_root.
    """
    print("\n" + "="*60)
    print("📋 COPY FILES - PROCESS STARTED")
    print("="*60)
    print(f"📄 Batch file: {batch_file_path}")
    
    if not os.path.exists(batch_file_path):
        print(f"❌ Error: Batch file not found!")
        raise FileNotFoundError(f"Batch file not found: {batch_file_path}")

    with open(batch_file_path, "r", encoding="utf-8") as f:
        doc_ids = [line.strip() for line in f if line.strip()]

    print(f"📊 Found {len(doc_ids)} document IDs in batch file")
    
    if not doc_ids:
        print("⚠️  No document IDs found in batch file")
        return 0, 0, 0, None # copied, skipped, total, dest

    # If dest_root is not provided, create one based on timestamp inside the batch folder's parent
    if not dest_root:
        # Assuming batch_file_path is like .../BATCH_LISTS_suffix/1_250.txt
        # We want .../BATCH_LISTS_suffix/BK_FILES/batch_name
        batch_dir = os.path.dirname(batch_file_path)
        batch_name = os.path.splitext(os.path.basename(batch_file_path))[0]
        dest_root = os.path.join(batch_dir, "BK_FILES", batch_name)

    print(f"📁 Destination folder: {dest_root}")
    os.makedirs(dest_root, exist_ok=True)

    copied_count = 0
    skipped_count = 0
    
    print(f"\n⏳ Processing {len(doc_ids)} documents...")
    
    # Resolve against root_folder if provided
    file_path = ROOT_FOLDER
    # file_path = r"C:/_IMPACT/_LOCAL_FILES"
    if root_folder:
        file_path = str(Path(root_folder) / file_path)

    print(f"\n⏳ Scaning {file_path} ...")    
    
    for idx, doc_id in enumerate(doc_ids, 1):
        src_path = os.path.join(file_path, doc_id)
        if not os.path.isdir(src_path):
            skipped_count += 1
            continue

        files_copied = False
        
        # Copy _updated.html
        for f in os.listdir(src_path):
            if f.endswith("_updated.html"):
                src = os.path.join(src_path, f)
                dst = os.path.join(dest_root, f"{doc_id}_updated.html")
                try:
                    shutil.copy2(src, dst)
                    files_copied = True
                except Exception:
                    pass

        # Copy config.xml
        xml_src = os.path.join(src_path, "impact_config.xml")
        xml_dst = os.path.join(dest_root, f"{doc_id}_config.xml")
        if os.path.exists(xml_src):
            try:
                shutil.copy2(xml_src, xml_dst)
                files_copied = True
            except Exception:
                pass
        
        if files_copied:
            copied_count += 1
            if copied_count % 25 == 0:
                print(f"   ✓ Copied {copied_count}/{len(doc_ids)} documents...")
        else:
            skipped_count += 1

    print(f"\n📊 Copy Summary:")
    print(f"   • Successfully copied: {copied_count}")
    print(f"   • Skipped (no files): {skipped_count}")
    print(f"   • Total processed: {len(doc_ids)}")
    print(f"\n✅ COPY COMPLETED")
    print(f"📁 Files copied to: {dest_root}")
    print("="*60 + "\n")

    return copied_count, skipped_count, len(doc_ids), dest_root

def parse_emails(xml_path):
    """Extract client, file-id, emails; skip if link-info == pubkitdev"""
    try:        
        tree = ET.parse(xml_path)
        root = tree.getroot()

        def get_tag(tag):
            el = root.find(tag)
            return el.text.strip() if el is not None and el.text else ""

        link_info = get_tag("link-info").lower()
        # if link_info == "pubkitdev1":
        #     return None, None, None, True  # mark as skip

        client = get_tag("client")
        file_id = get_tag("file-id")

        emails_raw = []
        # for contrib in root.findall(".//contributor[@role='author']"):
        #     for e_node in contrib.findall("email"):
        #         if e_node.text:
        #             for em in e_node.text.split(","):
        #                 val = em.strip()
        #                 if val:
        #                     emails_raw.append(val)

        return client, file_id, emails_raw, False

    except Exception as e:
        return "NA", "NA", [], False

def search_in_batch(batch_folder: str, search_terms: list):
    """
    Searches for terms in HTML files within the batch_folder.
    search_terms: list of dicts or strings. 
    """
    print("\n" + "="*60)
    print("🔍 SEARCH IN BATCH - PROCESS STARTED")
    print("="*60)
    print(f"📁 Batch folder: {batch_folder}")
    
    if not os.path.exists(batch_folder):
        print(f"❌ Error: Batch folder not found!")
        return []

    html_files = [f for f in os.listdir(batch_folder) if f.endswith("_updated.html")]
    print(f"📄 Found {len(html_files)} HTML files to search")
    
    results = []

    # Normalize search terms to a dictionary {key: pattern}
    search_map = {}
    if len(search_terms) > 0 and isinstance(search_terms[0], dict):
        for item in search_terms:
            k = list(item.keys())[0]
            v = list(item.values())[0]
            search_map[k] = v
    else:
        for i, term in enumerate(search_terms):
            search_map[f"term_{i+1}"] = term
    
    print(f"🔎 Search terms: {', '.join(search_map.values())}")
    print(f"\n⏳ Searching through files...")

    processed = 0
    skipped_no_xml = 0
    skipped_pubkitdev = 0
    
    for html_file in html_files:
        processed += 1
        doc_id = html_file.replace("_updated.html", "")
        xml_file = os.path.join(batch_folder, f"{doc_id}_config.xml")
        html_path = os.path.join(batch_folder, html_file)

        if not os.path.exists(xml_file):
            skipped_no_xml += 1
            continue

        client, file_id, emails, skip = parse_emails(xml_file)
        if skip:
            skipped_pubkitdev += 1
            continue

        try:
            with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            continue

        found_keys = []
        for key, val in search_map.items():
            if re.search(re.escape(val), content, re.IGNORECASE):
                found_keys.append(key)

        if found_keys:
            results.append({
                "client": client,
                "file_id": file_id,
                "emails": emails,
                "found_keys": found_keys,
                "doc_id": doc_id
            })
            
        if processed % 10 == 0:
            print(f"   ✓ Processed {processed}/{len(html_files)} files, found {len(results)} matches...")
            
    print(f"\n📊 Search Summary:")
    print(f"   • Files processed: {processed}")
    print(f"   • Results found: {len(results)}")
    print(f"   • Skipped (no XML): {skipped_no_xml}")
    print(f"   • Skipped (pubkitdev): {skipped_pubkitdev}")
    print(f"\n✅ SEARCH COMPLETED - Found {len(results)} matching documents")
    print("="*60 + "\n")
    
    return results
