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

# ==========================================
# 0. DATABASE MANAGER (V14 - TITAN EDITION)
# ==========================================
def init_db():
    conn = sqlite3.connect('studio_pro_v14.db', check_same_thread=False)
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
# 1. UI & CSS (10X BETTER)
# ==========================================
st.set_page_config(page_title="AI Movie Studio PRO | V14 Titan", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;800&display=swap');
    html, body, [data-testid="stSidebar"], .stMarkdown { font-family: 'Vazirmatn', sans-serif; background-color: #050505;}
    
    .main-title { text-align: center; font-weight: 900; background: linear-gradient(90deg, #ff0055, #ffaa00, #00ffcc, #ff0055); background-size: 300% auto; -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px; font-size: 3.8rem; animation: shine 4s linear infinite; text-shadow: 0px 5px 15px rgba(255,0,85,0.2);}
    @keyframes shine { to { background-position: 300% center; } }
    
    .sub-title { text-align: center; color: #888; margin-bottom: 30px; font-size: 1.3rem; letter-spacing: 2px; text-transform: uppercase;}
    
    .status-box { background: rgba(15, 15, 20, 0.95); border: 1px solid #222; padding: 20px; border-radius: 12px; margin-bottom: 15px; border-left: 5px solid #ffaa00; color: #eee; box-shadow: 0 5px 20px rgba(255, 170, 0, 0.1);}
    
    .console-box { background: #0a0a0a; border: 1px solid #333; border-radius: 8px; padding: 15px; color: #00ffcc; font-family: 'Courier New', monospace; font-size: 0.9em; height: 200px; overflow-y: auto; direction: ltr; margin-bottom: 20px;}
    
    .live-preview-box { background: linear-gradient(180deg, #111, #0a0a0a); padding: 25px; border-radius: 15px; border-top: 5px solid #00ffcc; color: #fff; direction: rtl; text-align: right; height: 400px; overflow-y: auto; font-size: 1.2em; line-height: 1.9; box-shadow: 0 10px 30px rgba(0,255,204,0.15);}
    
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background: linear-gradient(90deg, #ff0055 0%, #aa00ff 100%); color: white; font-size: 1.2em; font-weight: bold; border: none; transition: 0.3s;}
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0 10px 30px rgba(255, 0, 85, 0.4); }
    
    .agent-badge { display: inline-block; padding: 5px 12px; border-radius: 20px; font-size: 0.85em; font-weight: bold; margin-bottom: 10px; background: #222; color: #00ffcc; border: 1px solid #00ffcc;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SRT PARSER & BUILDER (Untouched Timelines)
# ==========================================
def parse_srt(srt_string):
    srt_string = srt_string.replace('\r\n', '\n').strip()
    blocks = re.split(r'\n\n+', srt_string)
    parsed = []
    for block in blocks:
        lines = block.split('\n')
        if len(lines) >= 3:
            parsed.append({'id': lines[0].strip(), 'time': lines[1].strip(), 'text': '\n'.join(lines[2:]).strip()})
    return parsed

def build_srt(parsed_list):
    return '\n\n'.join([f"{item['id']}\n{item['time']}\n{item['text']}" for item in parsed_list])

# ==========================================
# 3. AGENT 1: STORY & VIDEO ANALYST
# ==========================================
def agent_1_analyze(active_keys, model_name, srt_text, glossary, video_file=None):
    prompt = f"""You are AGENT 1: The Master Anime Director.
Analyze this subtitle snippet and create a 'Translation Bible'.
1. Identify the main plot and emotion.
2. Identify characters, their age, and tone (Aggressive, soft, formal).
3. Provide rules for the translators based on the glossary.
Glossary: {glossary}
Subtitles: {srt_text[:10000]}"""
    
    for key in active_keys:
        genai.configure(api_key=key)
        try:
            model = genai.GenerativeModel(model_name)
            contents = [prompt]
            if video_file:
                video_file.seek(0)
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                    tmp.write(video_file.read())
                    v_path = tmp.name
                g_file = genai.upload_file(path=v_path)
                while g_file.state.name == "PROCESSING":
                    time.sleep(3)
                    g_file = genai.get_file(g_file.name)
                if g_file.state.name == "ACTIVE":
                    contents.insert(0, g_file)
            return model.generate_content(contents).text
        except Exception as e: continue
    return "Basic Context: Translate dynamically."

# ==========================================
# 4. AGENT 2: THE ENRICHER (Fix English + Add Japanese + Suggestions)
# ==========================================
def agent_2_enrich_chunk(chunk, active_keys, master_context, selected_model):
    # ناردنی پارچەی بچووک بۆ ئەوەی هەرگیز هەڵە نەکات
    xml_input = "".join([f'<sub id="{item["id"]}">{item["text"].replace("<","").replace(">","")}</sub>\n' for item in chunk])
    
    prompt = f"""You are AGENT 2: The Deep Context Enricher.
Master Context: {master_context}

For every single line in the input, you MUST output an enriched XML format. 
1. Fix the English text if it's broken.
2. Guess the Japanese Romaji or Anime expression they are likely saying.
3. Provide the Scene Emotion.
4. Give 3 Kurdish Sorani suggestions (Literal, Simple, Cinematic).

Input:
{xml_input}

Output EXACTLY like this for every line, do not miss any ID:
<sub id="1">
    <fixed_eng>...</fixed_eng>
    <jp_guess>...</jp_guess>
    <emotion>...</emotion>
    <sug1>...</sug1>
    <sug2>...</sug2>
    <sug3>...</sug3>
</sub>
"""
    attempts = 0
    while attempts < len(active_keys) * 2:
        key = random.choice(active_keys)
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(selected_model, generation_config={"temperature": 0.3})
            res = model.generate_content(prompt).text.replace('```xml', '').replace('```', '').strip()
            
            # دەرهێنانی داتا زەبەلاحەکە
            enriched_data = {}
            blocks = re.findall(r'<sub id="(\d+)"\s*>(.*?)</sub>', res, re.DOTALL)
            for b_id, content in blocks:
                enriched_data[b_id.strip()] = content.strip()
            if enriched_data: return enriched_data
        except: time.sleep(1)
        attempts += 1
    return None

# ==========================================
# 5. AGENT 3: THE SWARM TRANSLATOR (10 LINES AT A TIME)
# ==========================================
def swarm_worker_translate(chunk_10, enriched_data_map, key, selected_model):
    # ئەمە ئەو بریکارەیە کە لەناو شانەی هەنگەکەدا تەنها ١٠ دێڕ دەکات
    input_text = ""
    for item in chunk_10:
        b_id = str(item['id'])
        context = enriched_data_map.get(b_id, f"<fixed_eng>{item['text']}</fixed_eng>")
        input_text += f'<sub id="{b_id}">\n{context}\n</sub>\n\n'

    prompt = f"""You are AGENT 3: The Final Translator.
You have 10 lines. Look at the <fixed_eng>, <jp_guess>, and the 3 Kurdish suggestions.
Your ONLY job is to output the final, perfect, cinematic Kurdish Sorani translation.
Rule 1: NEVER SHORTEN THE TEXT.
Rule 2: DO NOT MISS ANY ID.
Rule 3: If text is >45 chars, split with \n.

Input:
{input_text}

Output ONLY this XML format:
<sub id="X">Perfect Kurdish Text</sub>
"""
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel(selected_model, generation_config={"temperature": 0.1})
        res = model.generate_content(prompt).text.replace('```xml', '').replace('```', '').strip()
        matches = re.findall(r'<sub id="(\d+)"\s*>(.*?)</sub>', res, re.DOTALL)
        if matches: return {m[0].strip(): m[1].strip() for m in matches}
    except: pass
    return None

def process_50_lines_in_swarm(chunk_50, enriched_data_map, keys, selected_model):
    # دابەشکردنی ٥٠ دێڕەکە بۆ ٥ پارچەی ١٠ دێڕی
    chunks_10 = [chunk_50[i:i+10] for i in range(0, len(chunk_50), 10)]
    final_results = {}
    
    # لێرەدا فێڵە گەورەکەیە: هەر ١٠ دێڕێک بە بەکارهێنانی کلیلێکی جیاواز لە یەک کاتدا (Parallel) دەڕوات
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(keys)) as executor:
        futures = []
        for i, c10 in enumerate(chunks_10):
            k = keys[i % len(keys)]
            futures.append(executor.submit(swarm_worker_translate, c10, enriched_data_map, k, selected_model))
            
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: final_results.update(res)
            
    return final_results

# ==========================================
# 6. MAIN UI & INITIALIZATION
# ==========================================
st.markdown("<h1 class='main-title'>AI Movie Studio PRO 🎬 V14 TITAN</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>سیستەمی شانەی هەنگ (Swarm AI) | شیکاری ژاپۆنی | خێرایی خەیاڵی</p>", unsafe_allow_html=True)

if "current_hash" not in st.session_state:
    st.session_state.current_hash = ""
    st.session_state.master_context = ""
    st.session_state.enriched_chunks = {}
    st.session_state.translated_chunks = {}
    st.session_state.is_running = False

with st.sidebar:
    st.header("🔑 کلیلەکان (Swarm Engine)")
    api_inputs = [st.text_input(f"Slot {i+1}", type="password") for i in range(4)]
    active_keys = [k.strip() for k in api_inputs if k.strip()]
    
    st.markdown("---")
    gemini_model_name = None
    if active_keys:
        try:
            genai.configure(api_key=active_keys[0])
            available_models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            if available_models: gemini_model_name = st.selectbox("مۆدێل:", available_models)
        except: st.error("⚠️ کێشەی کلیل.")
            
    st.markdown("---")
    glossary = st.text_area("📚 فەرهەنگ", placeholder="وشەکان...")
    uploaded_video = st.file_uploader("🎥 ڤیدیۆ", type=['mp4'])

tab1, tab2, tab3 = st.tabs(["📥 ١. پڕۆژە", "⚙️ ٢. ستۆدیۆی ئەلیکترۆنی", "✅ ٣. بەرهەم"])

with tab1:
    input_srt = st.text_area("دەقی SRT لێرە دابنێ (٤٠٠ دێڕ بە ٥ خولەک!):", height=300)
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

# ==========================================
# 7. THE TITAN ENGINE (PIPELINE)
# ==========================================
if st.session_state.is_running:
    with tab2:
        # Time Tracker
        elapsed = int(time.time() - st.session_state.start_time)
        st.markdown(f"⏱️ **کاتی تێپەڕبوو:** {elapsed // 60} خولەک و {elapsed % 60} چرکە")

        # --- AGENT 1 ---
        if not st.session_state.master_context:
            with st.spinner("🕵️ بریکاری ١: شیکاری ڤیدیۆ و چیرۆک..."):
                st.session_state.master_context = agent_1_analyze(active_keys, gemini_model_name, input_srt, glossary, uploaded_video)
                save_state_to_db(db_conn, st.session_state.current_hash, input_srt, st.session_state.master_context, st.session_state.enriched_chunks, st.session_state.translated_chunks)
        
        with st.expander("👁️ بینینی مێشکی بریکاری ١ (Master Context)", expanded=False):
            st.markdown(f"<div class='console-box'>{st.session_state.master_context}</div>", unsafe_allow_html=True)

        parsed_data = parse_srt(input_srt)
        
        # --- AGENT 2 (ENRICHER) ---
        st.markdown("### 🧠 قۆناغی دروستکردنی Blueprint (ئینگلیزی، ژاپۆنی، پێشنیار)")
        enrich_chunks = [parsed_data[i:i+20] for i in range(0, len(parsed_data), 20)] # ٢٠ دێڕ بە ٢٠ دێڕ بۆ دڵنیایی
        enrich_bar = st.progress(0)
        
        flat_enriched_data = {}
        for i, chunk in enumerate(enrich_chunks):
            if i not in st.session_state.enriched_chunks:
                res = agent_2_enrich_chunk(chunk, active_keys, st.session_state.master_context, gemini_model_name)
                if res:
                    st.session_state.enriched_chunks[i] = res
                    save_state_to_db(db_conn, st.session_state.current_hash, input_srt, st.session_state.master_context, st.session_state.enriched_chunks, st.session_state.translated_chunks)
            
            if i in st.session_state.enriched_chunks:
                flat_enriched_data.update(st.session_state.enriched_chunks[i])
            enrich_bar.progress((i + 1) / len(enrich_chunks))
            
        with st.expander("👁️ بینینی کاری بریکاری ٢ (دەقی دەوڵەمەندکراو)", expanded=False):
            sample_enrich = list(flat_enriched_data.values())[:3]
            st.markdown(f"<div class='console-box'>{str(sample_enrich)}</div>", unsafe_allow_html=True)

        # --- AGENT 3 (SWARM TRANSLATORS - PARALLEL) ---
        st.markdown("### 🐝 قۆناغی وەرگێڕانی شانەی هەنگ (٥٠ دێڕ پێکەوە، دابەشی ١٠)")
        translate_chunks = [parsed_data[i:i+50] for i in range(0, len(parsed_data), 50)]
        trans_bar = st.progress(0)
        preview_box = st.empty()
        
        final_srt_items = []
        current_preview = ""
        
        for i, chunk_50 in enumerate(translate_chunks):
            if i not in st.session_state.translated_chunks:
                with st.spinner(f"🐝 شانەی هەنگ هێرش دەکاتە سەر پارچەی {i+1}..."):
                    res = process_50_lines_in_swarm(chunk_50, flat_enriched_data, active_keys, gemini_model_name)
                    
                    # کۆکردنەوەی ئەنجامەکان
                    temp_chunk = []
                    for item in chunk_50:
                        new_item = item.copy()
                        b_id = str(item['id'])
                        if res and b_id in res:
                            new_item['text'] = res[b_id]
                        else:
                            # ئەگەر زۆر دەگمەن هەڵەی کرد، پێشنیاری یەکەمی بریکاری ٢ بەکاردێنین
                            fallback = flat_enriched_data.get(b_id, "")
                            sug_match = re.search(r'<sug3>(.*?)</sug3>', fallback)
                            if sug_match: new_item['text'] = sug_match.group(1)
                        temp_chunk.append(new_item)
                        
                    st.session_state.translated_chunks[i] = temp_chunk
                    save_state_to_db(db_conn, st.session_state.current_hash, input_srt, st.session_state.master_context, st.session_state.enriched_chunks, st.session_state.translated_chunks)
            
            final_srt_items.extend(st.session_state.translated_chunks[i])
            
            # Live Preview
            current_preview = build_srt(final_srt_items)
            preview_box.markdown(f"<div class='live-preview-box'>{current_preview[-1500:].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
            trans_bar.progress((i + 1) / len(translate_chunks))
            
        st.session_state.final_srt = build_srt(final_srt_items)
        st.session_state.is_running = False
        st.success(f"🎉 هەموو شتێک بە {int(time.time() - st.session_state.start_time) // 60} خولەک تەواو بوو!")

with tab3:
    if "final_srt" in st.session_state and st.session_state.final_srt:
        st.balloons()
        st.download_button("📥 داگرتنی فایلی تایتان (.srt)", st.session_state.final_srt, "Studio_PRO_V14_Titan.srt")
        st.text_area("کۆدی پەسەندکراو:", st.session_state.final_srt, height=450)
