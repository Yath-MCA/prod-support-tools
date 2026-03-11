import os
import re
import json
from collections import Counter
from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from bs4 import BeautifulSoup
import requests
import threading
import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
cache_lock = threading.RLock()

# Backend in-memory cache for known words to avoid re-validating after sync
_known_words_memo = {"set": set(), "expiry": 0}

# Versioning
APP_VERSION = "2.4.1"
LAST_UPDATE = "2026-03-11 11:05"

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
STATIC_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
COMMON_WORDS_FILE = os.path.join(STATIC_FOLDER, 'common_words.txt')
CUSTOM_WORDS_FILE = os.path.join(STATIC_FOLDER, 'custom_dictionary.txt')
DICT_CACHE_FILE = os.path.join(STATIC_FOLDER, 'dictionary_cache.json')

# Configuration for Validation Sources
VALIDATION_SOURCES = [
    {
        "id": "primary",
        "name": "FREE DICT",
        "category": "General",
        "url_template": "https://api.dictionaryapi.dev/api/v2/entries/en/{word}",
        "save_file": os.path.join(STATIC_FOLDER, 'verified_primary.txt')
    },
    {
        "id": "wiktionary",
        "name": "Wiktionary",
        "category": "General",
        "url_template": "https://en.wiktionary.org/w/api.php?action=query&titles={word}&format=json",
        "save_file": os.path.join(STATIC_FOLDER, 'verified_wiktionary.txt')
    },
    {
        "id": "secondary",
        "name": "DATAMUSE",
        "category": "General",
        "url_template": "https://api.datamuse.com/words?sp={word}&md=f&max=1",
        "save_file": os.path.join(STATIC_FOLDER, 'verified_secondary.txt')
    },
    {
        "id": "medical",
        "name": "PubChem",
        "category": "Scientific",
        "url_template": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{word}/JSON",
        "save_file": os.path.join(STATIC_FOLDER, 'verified_scientific.txt')
    },
    {
        "id": "biology",
        "name": "GBIF",
        "category": "Scientific",
        "url_template": "https://api.gbif.org/v1/species/match?name={word}",
        "save_file": os.path.join(STATIC_FOLDER, 'verified_scientific.txt')
    }
]

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure folders and files exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)
required_files = [CUSTOM_WORDS_FILE, DICT_CACHE_FILE, COMMON_WORDS_FILE]
for src in VALIDATION_SOURCES:
    required_files.append(src['save_file'])

for f_path in required_files:
    if not os.path.exists(f_path):
        with open(f_path, 'w', encoding='utf-8') as f:
            if f_path.endswith('.json'): f.write('{}')
            else: f.write('')

def load_dict_cache():
    with cache_lock:
        if not os.path.exists(DICT_CACHE_FILE):
            return {}
        try:
            with open(DICT_CACHE_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return {}
                data = json.loads(content)
                return data if isinstance(data, dict) else {}
        except Exception as e:
            print(f"Error loading cache file: {e}")
            return None 

def save_dict_cache(new_data):
    if not new_data:
        return

    with cache_lock:
        current_cache = load_dict_cache()
        if current_cache is None:
            if os.path.exists(DICT_CACHE_FILE):
                print("CRITICAL: Aborting cache save because existing file could not be loaded. Data preservation prioritized.")
                return 
            else:
                current_cache = {}
        
        now_iso = datetime.datetime.now().isoformat()
        for word, result in new_data.items():
            if "timestamp" not in result:
                result["timestamp"] = now_iso
        
        current_cache.update(new_data)
        
        tmp_file = DICT_CACHE_FILE + ".tmp"
        try:
            with open(tmp_file, 'w', encoding='utf-8') as f:
                json.dump(current_cache, f, indent=4)
            
            if os.path.exists(DICT_CACHE_FILE):
                os.replace(tmp_file, DICT_CACHE_FILE)
            else:
                os.rename(tmp_file, DICT_CACHE_FILE)
        except Exception as e:
            print(f"Error writing to cache file: {e}")
            if os.path.exists(tmp_file):
                try: os.remove(tmp_file)
                except: pass

def load_common_words(include_cache=True):
    global _known_words_memo
    if time.time() < _known_words_memo["expiry"]:
        return _known_words_memo["set"]

    ignored = set()
    files_to_load = [COMMON_WORDS_FILE, CUSTOM_WORDS_FILE]
    for src in VALIDATION_SOURCES:
        files_to_load.append(src['save_file'])
        
    for filepath in files_to_load:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                ignored.update(line.strip().lower() for line in f if line.strip())
    
    if include_cache:
        cache = load_dict_cache()
        if cache:
            for word, res in cache.items():
                if res.get('is_known'):
                    ignored.add(word.lower())
    
    _known_words_memo["set"] = ignored
    _known_words_memo["expiry"] = time.time() + 60
    return ignored

def tokenize(text):
    return re.findall(r'[a-z]+', text.lower())

def extract_body_text(content, file_type):
    parser = 'xml' if file_type == 'xml' else 'html.parser'
    soup = BeautifulSoup(content, parser)
    
    body = None
    if file_type == 'xml':
        body = soup.find('book-body')
    elif file_type == 'html':
        body = soup.find('div', class_='book-body')
    
    if not body:
        body = soup.find('body') or soup

    for tag in body.select('.ref, .front, .back, ref, [class*="ref"], [data-name="ref"], [data-role="ref"]'):
        tag.decompose()
        
    return body.get_text()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    if 'content' not in request.files:
        return redirect(url_for('index'))
    
    content_file = request.files['content']
    if content_file.filename == '':
        return redirect(url_for('index'))
    
    filename = content_file.filename.lower()
    if filename.endswith('.xml'): file_type = 'xml'
    elif filename.endswith(('.html', '.htm')): file_type = 'html'
    else: file_type = 'txt'
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    content_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(content_file.filename))
    content_file.save(content_path)
    
    with open(content_path, 'r', encoding='utf-8', errors='ignore') as f:
        raw_content = f.read()
    
    if file_type == 'txt':
        clean_text = raw_content
    else:
        clean_text = extract_body_text(raw_content, file_type)
    
    words = tokenize(clean_text)
    word_counts = Counter(words)
    common_words_set = load_common_words()
    
    common_found = {word: count for word, count in word_counts.items() if word in common_words_set}
    spelling_errors = {word: count for word, count in word_counts.items() if word not in common_words_set}
    
    results = {
        'total_words': len(words),
        'unique_words': len(word_counts),
        'unique_error_count': len(spelling_errors),
        'total_error_count': sum(spelling_errors.values()),
        'unique_common_count': len(common_found),
        'total_common_count': sum(common_found.values()),
        'error_list': sorted(spelling_errors.items(), key=lambda x: x[1], reverse=True),
        'common_list': sorted(common_found.items(), key=lambda x: x[1], reverse=True)
    }
    
    return render_template('report.html', results=results)

@app.route('/harvest', methods=['POST'])
def harvest():
    words = request.form.getlist('words')
    if not words:
        return redirect(url_for('index'))
    
    unique_words = sorted(list(set(w.lower() for w in words)))
    return render_template('harvest_preview.html', words=unique_words)

@app.route('/api/validate_word', methods=['GET'])
def validate_word():
    word = request.args.get('word', '').strip().lower()
    force = request.args.get('force', 'false').lower() == 'true'
    exclude = request.args.get('exclude', '').strip()
    
    if not word: return {"error": "no word"}, 400
    
    cache = load_dict_cache()
    if not force and cache and word in cache:
        return cache[word]
    
    return _validate_word_logic(word, cache, exclude_source=exclude)

@app.route('/save_verified', methods=['POST'])
def save_verified():
    words = request.form.getlist('words')
    target_id = request.form.get('target', 'primary')
    
    target_file = None
    for src in VALIDATION_SOURCES:
        if src['id'] == target_id:
            target_file = src['save_file']
            break
            
    if not target_file:
        return jsonify({"success": False, "message": "Invalid target"}), 400
    
    existing = set()
    if os.path.exists(target_file):
        with open(target_file, 'r', encoding='utf-8') as f:
            existing = set(line.strip().lower() for line in f if line.strip())
            
    added = 0
    with open(target_file, 'a', encoding='utf-8') as f:
        for w in sorted(list(set(words))):
            w_clean = w.strip().lower()
            if w_clean and w_clean not in existing:
                f.write(w_clean + '\n')
                added += 1
                
    _known_words_memo["expiry"] = 0
    return jsonify({"success": True, "count": added, "target": target_id})

@app.route('/api/validate_batch', methods=['POST'])
def validate_batch():
    words = request.json.get('words', [])
    if not words: return jsonify({})
    
    cache = load_dict_cache()
    results = {}
    new_results = {}
    known_set = load_common_words()

    for word in words:
        word = word.strip().lower()
        if not word: continue
        if cache and word in cache:
            results[word] = cache[word]
        else:
            res = _validate_word_logic(word, cache, save_to_cache=False, known_set=known_set) 
            results[word] = res
            new_results[word] = res
            if cache is not None: cache[word] = res
    
    if new_results:
        save_dict_cache(new_results)

    return jsonify(results)

def _validate_word_logic(word, cache, save_to_cache=True, known_set=None, exclude_source=None):
    if known_set is None:
        known_set = load_common_words()
    
    if word in known_set:
        return {
            "status_code": 200, "is_known": True,
            "message": "Known (Found in storage files)",
            "source": "storage", "category": "General", "details": {}
        }

    final_result = {
        "status_code": 404, "is_known": False,
        "message": "Not found (Potential Technical Term)",
        "source": None, "details": {}
    }
    
    def check_source(src, word):
        if exclude_source and src['id'] == exclude_source: return None
        try:
            url = src['url_template'].format(word=word)
            resp = requests.get(url, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                if src['id'] == 'wiktionary':
                    pages = data.get('query', {}).get('pages', {})
                    if "-1" in pages: return None
                if src['id'] == 'secondary':
                    if not data or data[0]['word'].lower() != word: return None
                    tags = data[0].get('tags', [])
                    freq = 0
                    for t in tags:
                        if t.startswith('f:'): freq = float(t[2:])
                    if freq <= 0.1: return None
                    return {"src": src, "freq": freq}
                if src['id'] == 'biology':
                    if data.get('matchType') == 'NONE' or data.get('confidence', 0) < 90: return None
                if src['id'] == 'medical':
                    if 'PC_Compounds' not in data: return None
                return {"src": src}
        except: return None
        return None

    with ThreadPoolExecutor(max_workers=len(VALIDATION_SOURCES)) as executor:
        future_to_src = {executor.submit(check_source, src, word): src for src in VALIDATION_SOURCES}
        found_result = None
        for future in as_completed(future_to_src):
            res = future.result()
            if res:
                src = res['src']
                final_result.update({
                    "status_code": 200, "is_known": True,
                    "message": f"Found ({src['name']})",
                    "source": src['id'], "category": src['category']
                })
                if "freq" in res: final_result["details"]["frequency"] = res["freq"]
                found_result = final_result
                break 

    if not found_result: found_result = final_result
    if save_to_cache: save_dict_cache({word: found_result})
    return found_result

@app.route('/api/sync_cache', methods=['POST'])
def sync_cache():
    cache = load_dict_cache()
    if not cache: return jsonify({"success": True, "total_added": 0})
    
    stats = {}
    total_added = 0
    for word, res in cache.items():
        if res.get('is_known'):
            source_id = res.get('source')
            target_file = next((s['save_file'] for s in VALIDATION_SOURCES if s['id'] == source_id), None)
            if target_file:
                stats.setdefault(target_file, []).append(word)

    results_list = []
    for target_file, words in stats.items():
        existing = set()
        if os.path.exists(target_file):
            with open(target_file, 'r', encoding='utf-8') as f:
                existing = set(line.strip().lower() for line in f if line.strip())
        
        added_to_this = 0
        with open(target_file, 'a', encoding='utf-8') as f:
            for w in sorted(list(set(words))):
                if w.lower() not in existing:
                    f.write(w.lower() + '\n')
                    added_to_this += 1
                    total_added += 1
        results_list.append({"file": os.path.basename(target_file), "added": added_to_this})

    if total_added > 0: _known_words_memo["expiry"] = 0
    return jsonify({"success": True, "total_added": total_added, "details": results_list})

@app.route('/save_words', methods=['POST'])
def save_words():
    words_to_add = request.form.getlist('words_to_add')
    target = request.form.get('target', 'custom') 
    target_file = COMMON_WORDS_FILE if target == 'common' else CUSTOM_WORDS_FILE
    
    existing = set()
    if os.path.exists(target_file):
        with open(target_file, 'r', encoding='utf-8') as f:
            existing = set(line.strip().lower() for line in f if line.strip())
            
    added_count = 0
    with open(target_file, 'a', encoding='utf-8') as f:
        for word in words_to_add:
            if word.lower() not in existing:
                f.write(word.lower() + '\n')
                added_count += 1
    
    _known_words_memo["expiry"] = 0
    return render_template('harvest_success.html', count=added_count, target=target)

@app.context_processor
def inject_version():
    return dict(version=APP_VERSION, last_update=LAST_UPDATE)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
