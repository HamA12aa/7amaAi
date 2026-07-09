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
import math

# ==========================================
# 0. SESSION STATE FIX
# ==========================================
if "is_running" not in st.session_state: st.session_state.is_running = False
if "current_hash" not in st.session_state: st.session_state.current_hash = ""
if "master_context" not in st.session_state: st.session_state.master_context = ""
if "enriched_chunks" not in st.session_state: st.session_state.enriched_chunks = {}
if "translated_chunks" not in st.session_state: st.session_state.translated_chunks = {}
if "start_time" not in st.session_state: st.session_state.start_time = 0
if "final_srt" not in st.session_state: st.session_state.final_srt = ""
if "console_logs" not in st.session_state: st.session_state.console_logs = []

# ==========================================
# 1. DATABASE MANAGER
# ==========================================
def init_db():
    conn = sqlite3.connect('studio_pro_v19.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS projects
                 (srt_hash TEXT PRIMARY KEY, last_input TEXT, master_context TEXT, enriched_chunks TEXT, translated_chunks TEXT)''')
    conn.commit()
    return conn

def get_srt_hash(srt_text): return hashlib.md5(srt_text.encode('utf-8')).hexdigest()

def save_state_to_db(conn, srt_hash, last_input, master_context, enriched, translated):
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO projects VALUES (?, ?, ?, ?, ?)''', 
              (srt_hash, last_input, master_context, json.dumps(enriched), json.dumps(translated)))
    conn.commit()

def load_state_from_db(conn, srt_hash):
    c = conn.cursor()
    c.execute("SELECT * FROM projects WHERE srt_hash=?", (srt_hash,))
    row = c.fetchone()
    if row:
        return {
            'last_input': row[1], 'master_context': row[2],
            'enriched_chunks': {int(k): v for k, v in (json.loads(row[3]) if row[3] else {}).items()},
            'translated_chunks': {int(k): v for k, v in (json.loads(row[4]) if row[4] else {}).items()}
        }
    return None

db_conn = init_db()

# ==========================================
# 2. UI & CSS
# ==========================================
st.set_page_config(page_title="AI Movie Studio PRO | V19", layout="wide", page_icon="🎬")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;800&display=swap');
    html, body, [data-testid="stSidebar"], .stMarkdown { font-family: 'Vazirmatn', sans-serif; background-color: #050505;}
    .main-title { text-align: center; font-weight: 900; background: linear-gradient(90deg, #ff0055, #00ffcc, #ffaa00); background-size: 300% auto; -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px; font-size: 3.5rem; animation: shine 4s linear infinite;}
    @keyframes shine { to { background-position: 300% center; } }
    .console-box { background: #000; border: 1px solid #333; border-radius: 8px; padding: 15px; color: #00ff00; font-family: 'Courier New', monospace; font-size: 0.9em; height: 300px; overflow-y: auto; direction: rtl; margin-bottom: 20px; box-shadow: inset 0 0 10px rgba(0,255,0,0.1); line-height: 1.6;}
    .live-preview-box { background: linear-gradient(180deg, #111, #0a0a0a); padding: 25px; border-radius: 15px; border-top: 5px solid #ff0055; color: #fff; direction: rtl; text-align: right; height: 400px; overflow-y: auto; font-size: 1.2em; line-height: 1.9;}
    .eta-box { background: rgba(0, 255, 204, 0.1); border-left: 4px solid #00ffcc; padding: 15px; border-radius: 8px; margin-bottom: 15px; color: #fff;}
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background: linear-gradient(90deg, #ff0055 0%, #aa00ff 100%); color: white; font-size: 1.2em; font-weight: bold; border: none; transition: 0.3s;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def parse_srt(srt_string):
    blocks = re.split(r'\n\n+', srt_string.replace('\r\n', '\n').strip())
    parsed = []
    for block in blocks:
        lines = block.split('\n')
        if len(lines) >= 3: parsed.append({'id': lines[0].strip(), 'time': lines[1].strip(), 'text': '\n'.join(lines[2:]).strip()})
    return parsed

def build_srt(parsed_list):
    return '\n\n'.join([f"{item['id']}\n{item['time']}\n{item['text']}" for item in parsed_list])

def log_to_console(message, color="lime"):
    st.session_state.console_logs.append(f"<span style='color:{color};'>> {message}</span><br>")
    if len(st.session_state.console_logs) > 60: st.session_state.console_logs.pop(0)

def generate_content_with_retry(prompt, active_keys, model_name, temp=0.2):
    """ئەم فەنکشنە چاککراوە بۆ ئەوەی ڕێگری لە بلۆککردنی ناوەڕۆک بکات"""
    max_attempts = 8
    
    # چارەسەری کێشەی سانسۆر و بلۆککردن
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
    ]
    
    for attempt in range(max_attempts):
        key = random.choice(active_keys)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{"parts": [{"text": prompt}]}], 
            "generationConfig": {"temperature": temp},
            "safetySettings": safety_settings
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=60) 
            if response.status_code == 200:
                resp_json = response.json()
                if 'candidates' in resp_json and resp_json['candidates'][0].get('content'):
                    return resp_json['candidates'][0]['content']['parts'][0]['text']
                else:
                    # ئەگەر لێرە بلۆک بوو، هەوڵ دەدەینەوە
                    time.sleep(2)
            elif response.status_code == 429:
                time.sleep(4) 
            else:
                time.sleep(2)
        except Exception as e:
            time.sleep(2)
            
    return None 

# ==========================================
# 4. AGENTS DEFINITION
# ==========================================
def agent_1_analyze(active_keys, model_name, srt_text, glossary, video_file=None):
    prompt = f"You are AGENT 1: The Master Anime Director. Create a Translation Bible.\nGlossary: {glossary}\nSubtitles: {srt_text[:12000]}"
    res = generate_content_with_retry(prompt, active_keys, model_name, 0.4)
    return res if res else "Context: Cinematic Anime Tone."

def agent_2_enrich(chunk, active_keys, master_context, model_name):
    xml_input = "".join([f'<sub id="{item["id"]}">{item["text"].replace("<","").replace(">","")}</sub>\n' for item in chunk])
    prompt = f"""You are AGENT 2. Context: {master_context}
Output ONLY EXACT XML. NO Markdown, NO extra text.
<sub id="1">
<jp_guess>Romaji Japanese guess</jp_guess>
<sug3>Cinematic Anime Kurdish Sorani translation</sug3>
</sub>
Input:
{xml_input}"""
    
    res = generate_content_with_retry(prompt, active_keys, model_name, 0.3)
    if not res: return None
    
    clean_res = res.replace('```xml', '').replace('```', '').strip()
    data = {}
    blocks = re.findall(r'<sub id="(\d+)"[^>]*>(.*?)</sub>', clean_res, re.DOTALL | re.IGNORECASE)
    for b_id, content in blocks:
        data[b_id.strip()] = content.strip()
    return data

def agent_3_translate(chunk, enriched_map, active_keys, model_name, split_limit, temp):
    input_text = ""
    for item in chunk:
        b_id = str(item['id'])
        context = enriched_map.get(b_id, f"<sug3>{item['text']}</sug3>")
        input_text += f'<sub id="{b_id}">\nENG: {item["text"]}\n{context}\n</sub>\n'

    prompt = f"""You are AGENT 3. Output the absolute best Kurdish Sorani translation.
Output ONLY EXACT XML format: <sub id="X">Perfect Kurdish Text</sub>
1. NEVER shorten sentences.
2. If text >{split_limit} chars, split with \\n.
Input:
{input_text}"""
    
    res = generate_content_with_retry(prompt, active_keys, model_name, temp)
    if not res: return None
    
    clean_res = res.replace('```xml', '').replace('```', '').strip()
    matches = re.findall(r'<sub id="(\d+)"[^>]*>(.*?)</sub>', clean_res, re.DOTALL | re.IGNORECASE)
    if matches: return {m[0].strip(): m[1].strip() for m in matches}
    return None

def process_swarm_pipeline(chunk_15, active_keys, model_name, split_limit, temp, master_context):
    enriched = agent_2_enrich(chunk_15, active_keys, master_context, model_name)
    if not enriched: return None, {}, f"⚠️ بریکاری ٢ شکستی هێنا."
    
    sample_jp = re.search(r'<jp_guess>(.*?)</jp_guess>', list(enriched.values())[0], re.DOTALL | re.IGNORECASE)
    jp_txt = sample_jp.group(1).strip() if sample_jp else "N/A"

    final_res = agent_3_translate(chunk_15, enriched, active_keys, model_name, split_limit, temp)
    if not final_res: return None, enriched, f"⚠️ بریکاری ٣ شکستی هێنا."
        
    sample_final = list(final_res.values())[0]
    return final_res, enriched, f"🧠 ژاپۆنی: {jp_txt[:20]} | ✅ وەرگێڕا: {sample_final[:30]}..."

# ==========================================
# 5. MAIN UI & SIDEBAR
# ==========================================
with st.sidebar:
    st.header("🔑 کلیلەکان")
    active_keys = [k.strip() for k in [st.text_input(f"Slot {i+1}", type="password", key=f"key_{i}") for i in range(4)] if k.strip()]
    st.markdown("---")
    gemini_model_name = "gemini-1.5-flash" # بە فۆڵت ئەمە دادەنێین بۆ خێرایی
    if active_keys:
        try:
            genai.configure(api_key=active_keys[0])
            models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            if models: gemini_model_name = st.selectbox("🤖 مۆدێل:", models)
        except: st.error("کێشەی کلیل.")
            
    glossary = st.text_area("📚 فەرهەنگ", placeholder="وشەکان...")
    uploaded_video = st.file_uploader("🎥 ڤیدیۆ", type=['mp4'])
    
    st.header("⚙️ ڕێکخستنەکان")
    swarm_temp = st.slider("🌡️ هەستیاری", 0.0, 1.0, 0.1, 0.05)
    split_limit = st.number_input("✂️ شکاندنی دێڕ (پیت)", 30, 80, 45)
    if st.button("🗑️ سڕینەوەی داتابەیس"):
        c = db_conn.cursor()
        c.execute("DELETE FROM projects")
        db_conn.commit()
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.success("✅ داتابەیس سڕایەوە! ڕیفرێش بکە.")
        st.rerun()

tab1, tab2, tab3 = st.tabs(["📥 ١. پڕۆژە", "⚙️ ٢. ستۆدیۆ (Live)", "✅ ٣. بەرهەم"])

with tab1:
    input_srt = st.text_area("دەقی SRT لێرە دابنێ:", height=300)
    if input_srt and active_keys:
        lines_count = len(parse_srt(input_srt))
        st.markdown(f"<div class='eta-box'><b>⏳ کاتی پێشبینیکراو بۆ {lines_count} دێڕ:</b> نزیکەی {int(2 + (lines_count/15/max(1, len(active_keys)))*1.5)} خولەک</div>", unsafe_allow_html=True)

    if st.button("🚀 وەرگێڕانی تایتان دەستپێبکە"):
        if input_srt and active_keys:
            new_hash = get_srt_hash(input_srt)
            db_data = load_state_from_db(db_conn, new_hash)
            if db_data:
                st.session_state.master_context = db_data['master_context']
                st.session_state.enriched_chunks = db_data['enriched_chunks']
                st.session_state.translated_chunks = db_data['translated_chunks']
            else:
                st.session_state.master_context = ""
                st.session_state.enriched_chunks = {}
                st.session_state.translated_chunks = {}
                st.session_state.console_logs = []
            st.session_state.current_hash = new_hash
            st.session_state.is_running = True
            st.session_state.start_time = time.time()
            st.rerun()

if st.session_state.is_running:
    with tab2:
        st.markdown(f"⏱️ **کاتی تێپەڕبوو:** {int(time.time() - st.session_state.start_time) // 60} خولەک")
        console_placeholder = st.empty()
        def update_console(): console_placeholder.markdown(f"<div class='console-box'>{''.join(st.session_state.console_logs)}</div>", unsafe_allow_html=True)

        if not st.session_state.master_context:
            log_to_console("بریکاری ١ خەریکی شیکاری چیرۆکە...", "yellow")
            update_console()
            st.session_state.master_context = agent_1_analyze(active_keys, gemini_model_name, input_srt, glossary, uploaded_video)
            save_state_to_db(db_conn, st.session_state.current_hash, input_srt, st.session_state.master_context, st.session_state.enriched_chunks, st.session_state.translated_chunks)
            log_to_console("بریکاری ١ کۆتایی هات!", "lime")
            update_console()

        parsed_data = parse_srt(input_srt)
        chunks = [parsed_data[i:i+15] for i in range(0, len(parsed_data), 15)] 
        trans_bar = st.progress(len(st.session_state.translated_chunks) / len(chunks) if chunks else 0)
        preview_box = st.empty()
        
        def update_preview():
            current_items = []
            for k, v in sorted(st.session_state.translated_chunks.items()): current_items.extend(v)
            if current_items: preview_box.markdown(f"<div class='live-preview-box'>{build_srt(current_items)[-1000:].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

        update_preview()
        chunks_to_process = [ (i, c) for i, c in enumerate(chunks) if i not in st.session_state.translated_chunks ]
        
        if chunks_to_process:
            safe_master = st.session_state.master_context
            max_threads = min(3, len(active_keys)) if len(active_keys) > 0 else 1
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
                future_to_chunk = {}
                for idx, chunk_data in enumerate(chunks_to_process):
                    i, chunk = chunk_data
                    future = executor.submit(process_swarm_pipeline, chunk, active_keys, gemini_model_name, split_limit, swarm_temp, safe_master)
                    future_to_chunk[future] = (i, chunk)
                
                for future in concurrent.futures.as_completed(future_to_chunk):
                    i, chunk = future_to_chunk[future]
                    final_res, enriched_data, log_msg = future.result()
                    
                    color = "lime" if "✅" in log_msg else ("yellow" if "⚠️" in log_msg else "red")
                    log_to_console(f"پارچەی {i+1}: {log_msg}", color)
                    update_console()
                    
                    temp_chunk = []
                    for item in chunk:
                        new_item = item.copy()
                        b_id = str(item['id'])
                        if final_res and b_id in final_res:
                            new_item['text'] = final_res[b_id]
                        elif enriched_data and b_id in enriched_data:
                            kur_match = re.search(r'<sug3>(.*?)</sug3>', enriched_data[b_id], re.DOTALL | re.IGNORECASE)
                            if kur_match: new_item['text'] = kur_match.group(1).strip()
                        temp_chunk.append(new_item)
                        
                    st.session_state.translated_chunks[i] = temp_chunk
                    st.session_state.enriched_chunks[i] = enriched_data
                    save_state_to_db(db_conn, st.session_state.current_hash, input_srt, st.session_state.master_context, st.session_state.enriched_chunks, st.session_state.translated_chunks)
                    
                    trans_bar.progress(len(st.session_state.translated_chunks) / len(chunks))
                    update_preview()

        final_list = []
        for k, v in sorted(st.session_state.translated_chunks.items()): final_list.extend(v)
        st.session_state.final_srt = build_srt(final_list)
        st.session_state.is_running = False
        log_to_console("🎉 پرۆسەکە بەسەرکەوتوویی تەواو بوو!", "lime")
        update_console()
        st.rerun()

with tab3:
    if "final_srt" in st.session_state and st.session_state.final_srt:
        st.balloons()
        c1, c2 = st.columns(2)
        with c1: st.download_button("📥 داگرتنی فایلی SRT", st.session_state.final_srt, "Studio_PRO_V19.srt")
        with c2: st.download_button("📝 داگرتنی وەک TXT", st.session_state.final_srt.replace('-->', '>>'), "Studio_PRO.txt")
        st.text_area("دەقی کۆتایی:", st.session_state.final_srt, height=450)
