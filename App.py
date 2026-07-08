import streamlit as st
import google.generativeai as genai
import time
import re
import random
import tempfile
import sqlite3
import json
import hashlib
import concurrent.futures
import requests

# ==========================================
# 0. DATABASE MANAGER (V16)
# ==========================================
def init_db():
    conn = sqlite3.connect('studio_pro_v16.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS projects
                 (srt_hash TEXT PRIMARY KEY, 
                  last_input TEXT, 
                  master_context TEXT, 
                  enriched_chunks TEXT,
                  translated_chunks TEXT)''')
    conn.commit()
    return conn

def get_srt_hash(srt_text):
    return hashlib.md5(srt_text.encode('utf-8')).hexdigest()

def save_state_to_db(conn, srt_hash, last_input, master_context, enriched, translated):
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO projects 
                 (srt_hash, last_input, master_context, enriched_chunks, translated_chunks) 
                 VALUES (?, ?, ?, ?, ?)''', 
              (srt_hash, last_input, master_context, json.dumps(enriched), json.dumps(translated)))
    conn.commit()

def load_state_from_db(conn, srt_hash):
    c = conn.cursor()
    c.execute("SELECT * FROM projects WHERE srt_hash=?", (srt_hash,))
    row = c.fetchone()
    if row:
        return {
            'last_input': row[1],
            'master_context': row[2],
            'enriched_chunks': json.loads(row[3]) if row[3] else {},
            'translated_chunks': json.loads(row[4]) if row[4] else {}
        }
    return None

db_conn = init_db()

# ==========================================
# 1. UI & CSS (LIVE CONSOLE ADDED)
# ==========================================
st.set_page_config(page_title="AI Movie Studio PRO | V16 Ultimate", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;800&display=swap');
    html, body, [data-testid="stSidebar"], .stMarkdown { font-family: 'Vazirmatn', sans-serif; background-color: #050505;}
    
    .main-title { text-align: center; font-weight: 900; background: linear-gradient(90deg, #00ffcc, #ffaa00, #ff0055); background-size: 300% auto; -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px; font-size: 3.5rem; animation: shine 4s linear infinite;}
    @keyframes shine { to { background-position: 300% center; } }
    
    .status-box { background: rgba(15, 15, 20, 0.95); border: 1px solid #222; padding: 20px; border-radius: 12px; margin-bottom: 15px; border-left: 5px solid #00ffcc; color: #eee;}
    
    .console-box { background: #000; border: 1px solid #333; border-radius: 8px; padding: 15px; color: #00ff00; font-family: 'Courier New', monospace; font-size: 0.9em; height: 250px; overflow-y: auto; direction: ltr; margin-bottom: 20px; box-shadow: inset 0 0 10px rgba(0,255,0,0.1);}
    
    .live-preview-box { background: linear-gradient(180deg, #111, #0a0a0a); padding: 25px; border-radius: 15px; border-top: 5px solid #ff0055; color: #fff; direction: rtl; text-align: right; height: 400px; overflow-y: auto; font-size: 1.2em; line-height: 1.9;}
    
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background: linear-gradient(90deg, #ff0055 0%, #aa00ff 100%); color: white; font-size: 1.2em; font-weight: bold; border: none; transition: 0.3s;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SESSION STATE SAFE INIT
# ==========================================
defaults = {"current_hash": "", "master_context": "", "enriched_chunks": {}, "translated_chunks": {}, "is_running": False, "start_time": 0, "final_srt": ""}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

# ==========================================
# 3. SRT PARSER
# ==========================================
def parse_srt(srt_string):
    blocks = re.split(r'\n\n+', srt_string.replace('\r\n', '\n').strip())
    parsed = []
    for block in blocks:
        lines = block.split('\n')
        if len(lines) >= 3:
            parsed.append({'id': lines[0].strip(), 'time': lines[1].strip(), 'text': '\n'.join(lines[2:]).strip()})
    return parsed

def build_srt(parsed_list):
    return '\n\n'.join([f"{item['id']}\n{item['time']}\n{item['text']}" for item in parsed_list])

# ==========================================
# 4. REST API FUNCTION (THE MAGIC FIX FOR THREADS)
# ==========================================
def generate_content_rest(prompt, api_key, model_name, temp=0.2):
    """Direct HTTP request to avoid global `genai` thread crashes."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temp}
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=40)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"ERROR_API: {response.status_code}"
    except Exception as e:
        return f"ERROR_TIMEOUT"

# ==========================================
# 5. AGENT 1: STORY ANALYST
# ==========================================
def agent_1_analyze(active_keys, model_name, srt_text, glossary, video_file=None):
    prompt = f"""You are AGENT 1: The Director. Create a concise Translation Bible based on these subtitles.
Glossary: {glossary}
Subtitles: {srt_text[:8000]}"""
    for key in active_keys:
        res = generate_content_rest(prompt, key, model_name, 0.4)
        if "ERROR" not in res: return res
    return "Basic Context: Translate properly."

# ==========================================
# 6. AGENT 2 & 3: ENRICHER & TRANSLATOR (SWARM)
# ==========================================
def agent_2_enrich(chunk, key, master_context, model_name):
    xml_input = "".join([f'<sub id="{item["id"]}">{item["text"].replace("<","").replace(">","")}</sub>\n' for item in chunk])
    prompt = f"""You are AGENT 2 (The Enricher). Context: {master_context}
For each line, output ONLY valid XML with the Japanese Romaji guess and a strong Kurdish translation.
Input:
{xml_input}
Format MUST BE EXACTLY:
<sub id="1">
<jp>romaji...</jp>
<kur>kurdish translation...</kur>
</sub>"""
    
    res = generate_content_rest(prompt, key, model_name, 0.3)
    if "ERROR" in res: return None
    
    clean_res = res.replace('```xml', '').replace('```', '').strip()
    data = {}
    blocks = re.findall(r'<sub id="(\d+)"\s*>(.*?)</sub>', clean_res, re.DOTALL)
    for b_id, content in blocks:
        data[b_id.strip()] = content.strip()
    return data

def agent_3_translate(chunk, enriched_map, key, model_name, split_limit, temp):
    input_text = ""
    for item in chunk:
        b_id = str(item['id'])
        context = enriched_map.get(b_id, f"<kur>{item['text']}</kur>") # fallback
        input_text += f'<sub id="{b_id}">\nENG: {item["text"]}\n{context}\n</sub>\n'

    prompt = f"""You are AGENT 3 (The Swarm Reviewer). 
Check the `<kur>` translation against the `ENG` text. Perfect it into cinematic Kurdish Sorani.
RULES: 
1. Never shorten. 
2. If text >{split_limit} chars, split with \\n.
3. OUTPUT ONLY FINAL XML.

Input:
{input_text}

Output format:
<sub id="1">Final Kurdish Text</sub>"""
    
    res = generate_content_rest(prompt, key, model_name, temp)
    if "ERROR" in res: return None
    
    clean_res = res.replace('```xml', '').replace('```', '').strip()
    matches = re.findall(r'<sub id="(\d+)"\s*>(.*?)</sub>', clean_res, re.DOTALL)
    if matches: return {m[0].strip(): m[1].strip() for m in matches}
    return None

# ==========================================
# 7. THE PARALLEL WORKER ENGINE
# ==========================================
def process_swarm_pipeline(chunk_15, key1, key2, model_name, split_limit, temp, console_ui):
    # هەنگاوی یەکەم: بریکاری ٢ داتا دروست دەکات
    enriched = agent_2_enrich(chunk_15, key1, master_context=st.session_state.master_context, model_name=model_name)
    if not enriched:
        console_ui.markdown(f"<span style='color:red;'>⚠️ بریکاری ٢ شکستی هێنا بۆ دێڕی {chunk_15[0]['id']}</span><br>", unsafe_allow_html=True)
        enriched = {}
    else:
        sample_jp = re.search(r'<jp>(.*?)</jp>', list(enriched.values())[0])
        jp_txt = sample_jp.group(1) if sample_jp else "N/A"
        console_ui.markdown(f"<span style='color:yellow;'>🧠 بریکاری ٢ ژاپۆنی دۆزییەوە: {jp_txt}</span><br>", unsafe_allow_html=True)

    # هەنگاوی دووەم: بریکاری ٣ پێداچوونەوە دەکات
    final_res = agent_3_translate(chunk_15, enriched, key2, model_name, split_limit, temp)
    if not final_res:
        console_ui.markdown(f"<span style='color:red;'>⚠️ بریکاری ٣ شکستی هێنا. گەڕانەوە بۆ ئینگلیزی.</span><br>", unsafe_allow_html=True)
    else:
        sample_txt = list(final_res.values())[0]
        console_ui.markdown(f"<span style='color:lime;'>✅ بریکاری ٣ وەرگێڕا: {sample_txt}</span><br>", unsafe_allow_html=True)
        
    return final_res, enriched

# ==========================================
# 8. MAIN UI & LOGIC
# ==========================================
st.markdown("<h1 class='main-title'>AI Movie Studio PRO 🎬 V16</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.header("🔑 کلیلەکان")
    active_keys = [k.strip() for k in [st.text_input(f"Slot {i+1}", type="password") for i in range(4)] if k.strip()]
    
    st.markdown("---")
    gemini_model_name = None
    if active_keys:
        try:
            genai.configure(api_key=active_keys[0])
            models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            if models: gemini_model_name = st.selectbox("🤖 مۆدێل:", models)
        except: st.error("کێشەی کلیل.")
            
    st.markdown("---")
    glossary = st.text_area("📚 فەرهەنگ", placeholder="وشەکان...")
    
    st.header("⚙️ ڕێکخستنەکان")
    swarm_temp = st.slider("🌡️ هەستیاری", 0.0, 1.0, 0.1, 0.05)
    split_limit = st.number_input("✂️ شکاندنی دێڕ (پیت)", 30, 80, 45)
    if st.button("🗑️ سڕینەوەی داتابەیس"):
        c = db_conn.cursor()
        c.execute("DELETE FROM projects")
        db_conn.commit()
        for k in defaults.keys():
            if k in st.session_state: del st.session_state[k]
        st.success("✅ داتابەیس سڕایەوە! ڕیفرێش بکە.")

tab1, tab2, tab3 = st.tabs(["📥 ١. پڕۆژە", "⚙️ ٢. ستۆدیۆ (Live)", "✅ ٣. بەرهەم"])

with tab1:
    input_srt = st.text_area("دەقی SRT لێرە دابنێ:", height=300)
    if st.button("🚀 وەرگێڕانی تایتان دەستپێبکە"):
        if input_srt and active_keys:
            new_hash = get_srt_hash(input_srt)
            db_data = load_state_from_db(db_conn, new_hash)
            if db_data:
                st.session_state.master_context = db_data['master_context']
                st.session_state.enriched_chunks = {int(k): v for k, v in db_data['enriched_chunks'].items()}
                st.session_state.translated_chunks = {int(k): v for k, v in db_data['translated_chunks'].items()}
                st.toast("🔄 داتا لە Database هێنرایەوە!")
            elif new_hash != st.session_state.current_hash:
                st.session_state.master_context = ""
                st.session_state.enriched_chunks = {}
                st.session_state.translated_chunks = {}
            st.session_state.current_hash = new_hash
            st.session_state.is_running = True
            st.session_state.start_time = time.time()

if st.session_state.is_running:
    with tab2:
        st.markdown(f"⏱️ **کاتی تێپەڕبوو:** {int(time.time() - st.session_state.start_time)} چرکە")

        # کۆنسۆڵی ڕاستەوخۆ (دەتوانیت بیبینیت چی ڕوودەدات!)
        st.markdown("### 🖥️ کۆنسۆڵی ڕاستەوخۆی بریکارەکان")
        console_box = st.empty()
        console_text = ">> دەستپێکردنی سیستەمی تایتان...\n"
        console_box.markdown(f"<div class='console-box'>{console_text}</div>", unsafe_allow_html=True)

        if not st.session_state.master_context:
            console_text += "<br>>> بریکاری ١ خەریکی شیکاری چیرۆکە..."
            console_box.markdown(f"<div class='console-box'>{console_text}</div>", unsafe_allow_html=True)
            st.session_state.master_context = agent_1_analyze(active_keys, gemini_model_name, input_srt, glossary)
            save_state_to_db(db_conn, st.session_state.current_hash, input_srt, st.session_state.master_context, st.session_state.enriched_chunks, st.session_state.translated_chunks)
            console_text += f"<br><span style='color:lime;'>✅ بریکاری ١ کۆتایی هات!</span>"
            console_box.markdown(f"<div class='console-box'>{console_text}</div>", unsafe_allow_html=True)

        parsed_data = parse_srt(input_srt)
        
        # پارچەکردن بۆ ١٥ دێڕ (باشترین قەبارە بۆ ئەوەی AI نەبوورێتەوە)
        chunks = [parsed_data[i:i+15] for i in range(0, len(parsed_data), 15)]
        
        trans_bar = st.progress(0)
        preview_box = st.empty()
        
        final_srt_items = []
        
        # پیشاندانی پێشوو
        for k, v in sorted(st.session_state.translated_chunks.items()):
            final_srt_items.extend(v)
        if final_srt_items:
            preview_box.markdown(f"<div class='live-preview-box'>{build_srt(final_srt_items)[-1000:].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

        # شانەی هەنگ بە سەلامەتی (ThreadPool)
        chunks_to_process = [ (i, c) for i, c in enumerate(chunks) if i not in st.session_state.translated_chunks ]
        
        if chunks_to_process:
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(active_keys)) as executor:
                future_to_chunk = {}
                for idx, chunk_data in enumerate(chunks_to_process):
                    i, chunk = chunk_data
                    k1 = active_keys[idx % len(active_keys)]
                    k2 = active_keys[(idx + 1) % len(active_keys)]
                    
                    # ناردن بۆ ناو Thread
                    future = executor.submit(process_swarm_pipeline, chunk, k1, k2, gemini_model_name, split_limit, swarm_temp, st.empty())
                    future_to_chunk[future] = (i, chunk)
                
                for future in concurrent.futures.as_completed(future_to_chunk):
                    i, chunk = future_to_chunk[future]
                    final_res, enriched_data = future.result()
                    
                    temp_chunk = []
                    for item in chunk:
                        new_item = item.copy()
                        b_id = str(item['id'])
                        if final_res and b_id in final_res:
                            new_item['text'] = final_res[b_id]
                        elif enriched_data and b_id in enriched_data:
                            # ئەگەر بریکاری ٣ شکستی هێنا، وەرگێڕانەکەی بریکاری ٢ بەکاردێنین
                            kur_match = re.search(r'<kur>(.*?)</kur>', enriched_data[b_id])
                            if kur_match: new_item['text'] = kur_match.group(1)
                        # ئەگەر هەردووکیان شکستیان هێنا، ئینگلیزییەکە دەمێنێتەوە بۆ ئەوەی فایلەکە تێک نەچێت
                        temp_chunk.append(new_item)
                        
                    st.session_state.translated_chunks[i] = temp_chunk
                    save_state_to_db(db_conn, st.session_state.current_hash, input_srt, st.session_state.master_context, st.session_state.enriched_chunks, st.session_state.translated_chunks)
                    
                    # Update Progress
                    completed = len(st.session_state.translated_chunks)
                    trans_bar.progress(completed / len(chunks))
                    
                    # Update Preview (Rebuild from sorted chunks)
                    current_items = []
                    for k, v in sorted(st.session_state.translated_chunks.items()):
                        current_items.extend(v)
                    preview_box.markdown(f"<div class='live-preview-box'>{build_srt(current_items)[-1000:].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

        # دروستکردنی فایلی کۆتایی
        final_list = []
        for k, v in sorted(st.session_state.translated_chunks.items()):
            final_list.extend(v)
        st.session_state.final_srt = build_srt(final_list)
        st.session_state.is_running = False
        
        console_text += f"<br><span style='color:aqua;'>🎉 پرۆسەکە بەسەرکەوتوویی تەواو بوو!</span>"
        console_box.markdown(f"<div class='console-box'>{console_text}</div>", unsafe_allow_html=True)

with tab3:
    if "final_srt" in st.session_state and st.session_state.final_srt:
        st.balloons()
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("📥 داگرتنی فایلی تایتان (.srt)", st.session_state.final_srt, "Studio_PRO_V16_Titan.srt")
        with col2:
            st.download_button("📝 داگرتنی وەک دەقی سادە (.txt)", st.session_state.final_srt.replace('-->', '>>'), "Studio_PRO_Text.txt")
        st.text_area("کۆدی پەسەندکراو:", st.session_state.final_srt, height=450)
