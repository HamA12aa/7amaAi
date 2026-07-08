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
# 0. ABSOLUTE TOP: SESSION STATE FIX
# مەحاڵە لێرە بەدواوە هەڵەی AttributeError بدات
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
# 1. DATABASE MANAGER (V17)
# ==========================================
def init_db():
    conn = sqlite3.connect('studio_pro_v17.db', check_same_thread=False)
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
            'enriched_chunks': {int(k): v for k, v in (json.loads(row[3]) if row[3] else {}).items()},
            'translated_chunks': {int(k): v for k, v in (json.loads(row[4]) if row[4] else {}).items()}
        }
    return None

db_conn = init_db()

# ==========================================
# 2. UI & CSS
# ==========================================
st.set_page_config(page_title="AI Movie Studio PRO | V17 Grandmaster", layout="wide", page_icon="🎬")

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
        if len(lines) >= 3:
            parsed.append({'id': lines[0].strip(), 'time': lines[1].strip(), 'text': '\n'.join(lines[2:]).strip()})
    return parsed

def build_srt(parsed_list):
    return '\n\n'.join([f"{item['id']}\n{item['time']}\n{item['text']}" for item in parsed_list])

def log_to_console(message, color="lime"):
    st.session_state.console_logs.append(f"<span style='color:{color};'>> {message}</span><br>")
    # هێشتنەوەی تەنها ٥٠ هێڵی کۆتایی بۆ ئەوەی قورس نەبێت
    if len(st.session_state.console_logs) > 50: st.session_state.console_logs.pop(0)

def generate_content_rest(prompt, api_key, model_name, temp=0.2):
    """بەکارهێنانی REST API بۆ ڕێگریکردن لە پێکدادانی کلیلەکان لە یەک کاتدا"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": temp}}
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60) # زیادکردنی کات بۆ ٦٠ چرکە بۆ زانیاری قووڵ
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"ERROR_API: {response.status_code} - {response.text}"
    except Exception as e:
        return f"ERROR_TIMEOUT: {str(e)}"

# ==========================================
# 4. AGENTS DEFINITION (POWERED UP)
# ==========================================
def agent_1_analyze(active_keys, model_name, srt_text, glossary, video_file=None):
    prompt = f"""You are AGENT 1: The Master Anime Director. Create a deeply detailed Translation Bible.
Include: Story Summary, Character tone (Age, gender, aggression), and Cultural notes.
Glossary: {glossary}
Subtitles: {srt_text[:12000]}"""
    for key in active_keys:
        res = generate_content_rest(prompt, key, model_name, 0.4)
        if "ERROR" not in res: return res
    return "Basic Context: Maintain high cinematic quality."

def agent_2_enrich(chunk, key, master_context, model_name):
    # بریکاری ٢ کە داوات کرد زانیارییەکانی زۆر بێت و پێشنیار بکات
    xml_input = "".join([f'<sub id="{item["id"]}">{item["text"].replace("<","").replace(">","")}</sub>\n' for item in chunk])
    prompt = f"""You are AGENT 2 (The Blueprint Master). Context: {master_context}

For EVERY SINGLE LINE, provide a deep analysis and 3 translation suggestions.
Do not skip any ID. Output MUST be ONLY this XML format exactly:

<sub id="1">
<fixed_eng>Corrected english if broken</fixed_eng>
<jp_guess>Romaji Japanese guess</jp_guess>
<emotion>Scene emotion</emotion>
<sug1>Literal Kurdish Sorani translation</sug1>
<sug2>Natural Kurdish Sorani translation</sug2>
<sug3>Cinematic Anime Kurdish Sorani translation</sug3>
</sub>

Input:
{xml_input}"""
    
    res = generate_content_rest(prompt, key, model_name, 0.3)
    if "ERROR" in res: return None
    
    clean_res = res.replace('```xml', '').replace('```', '').strip()
    data = {}
    blocks = re.findall(r'<sub id="(\d+)"\s*>(.*?)</sub>', clean_res, re.DOTALL)
    for b_id, content in blocks:
        data[b_id.strip()] = content.strip()
    return data

def agent_3_translate(chunk, enriched_map, key, model_name, split_limit, temp):
    # بریکاری ٣ کە تەنها پێداچوونەوە و هەڵبژاردنی باشترین دەکات
    input_text = ""
    for item in chunk:
        b_id = str(item['id'])
        context = enriched_map.get(b_id, f"<sug3>{item['text']}</sug3>")
        input_text += f'<sub id="{b_id}">\nENG: {item["text"]}\n{context}\n</sub>\n'

    prompt = f"""You are AGENT 3 (The Final Reviewer). 
You will see the original English, Japanese guess, Emotion, and 3 Kurdish suggestions.
Your job is to read them all and output the absolute best, most cinematic Kurdish Sorani translation.
RULES: 
1. NEVER shorten sentences.
2. Fix any Kurdish grammar mistakes.
3. If the final Kurdish text is >{split_limit} chars, split it with \\n.
4. Output ONLY the final XML.

Input:
{input_text}

Output format ONLY:
<sub id="X">Perfect Kurdish Text</sub>"""
    
    res = generate_content_rest(prompt, key, model_name, temp)
    if "ERROR" in res: return None
    
    clean_res = res.replace('```xml', '').replace('```', '').strip()
    matches = re.findall(r'<sub id="(\d+)"\s*>(.*?)</sub>', clean_res, re.DOTALL)
    if matches: return {m[0].strip(): m[1].strip() for m in matches}
    return None

def process_swarm_pipeline(chunk_15, key1, key2, model_name, split_limit, temp):
    # هەنگاوی 1: بریکاری 2 (دەوڵەمەندکردن)
    enriched = agent_2_enrich(chunk_15, key1, st.session_state.master_context, model_name)
    if not enriched:
        return None, {}, f"⚠️ بریکاری ٢ شکستی هێنا بۆ پارچەی {chunk_15[0]['id']}"
    
    sample_jp = re.search(r'<jp_guess>(.*?)</jp_guess>', list(enriched.values())[0])
    jp_txt = sample_jp.group(1) if sample_jp else "N/A"

    # هەنگاوی 2: بریکاری 3 (وەرگێڕانی کۆتایی)
    final_res = agent_3_translate(chunk_15, enriched, key2, model_name, split_limit, temp)
    if not final_res:
        return None, enriched, f"⚠️ بریکاری ٣ شکستی هێنا. بەکارهێنانی پێشنیاری بریکاری ٢."
        
    sample_final = list(final_res.values())[0]
    return final_res, enriched, f"🧠 ژاپۆنی: {jp_txt} | ✅ وەرگێڕا: {sample_final}"

# ==========================================
# 5. MAIN UI & SIDEBAR
# ==========================================
st.markdown("<h1 class='main-title'>AI Movie Studio PRO 🎬 V17</h1>", unsafe_allow_html=True)

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
    uploaded_video = st.file_uploader("🎥 ڤیدیۆ (بۆ هەستی کارەکتەرەکان)", type=['mp4'])
    
    st.header("⚙️ ڕێکخستنەکان")
    swarm_temp = st.slider("🌡️ هەستیاری", 0.0, 1.0, 0.1, 0.05)
    split_limit = st.number_input("✂️ شکاندنی دێڕ (پیت)", 30, 80, 45)
    if st.button("🗑️ سڕینەوەی داتابەیس"):
        c = db_conn.cursor()
        c.execute("DELETE FROM projects")
        db_conn.commit()
        for k in st.session_state.keys(): del st.session_state[k]
        st.success("✅ داتابەیس سڕایەوە! ڕیفرێش بکە.")

tab1, tab2, tab3 = st.tabs(["📥 ١. پڕۆژە", "⚙️ ٢. ستۆدیۆ (Live)", "✅ ٣. بەرهەم"])

with tab1:
    input_srt = st.text_area("دەقی SRT لێرە دابنێ:", height=300)
    
    # خەمڵاندنی کات (ETA Calculation)
    if input_srt and active_keys:
        lines_count = len(parse_srt(input_srt))
        chunks_count = math.ceil(lines_count / 15)
        keys_qty = len(active_keys)
        
        agent1_eta = 2 # خولەک
        swarm_eta = math.ceil(chunks_count / keys_qty) * 1.5 # بریکاری ٢ و ٣ کاتیان دەوێت
        total_eta = int(agent1_eta + swarm_eta)
        
        st.markdown(f"""
        <div class='eta-box'>
        <b>⏳ کاتی پێشبینیکراو بۆ {lines_count} دێڕ:</b> نزیکەی {total_eta} خولەک<br>
        <small>- بریکاری ١ (شیکاری قووڵ): ~٢ خولەک</small><br>
        <small>- بریکاری ٢ و ٣ (پێشنیار و وەرگێڕان): ~{int(swarm_eta)} خولەک (بەپێی ژمارەی کلیلەکانت خێراتر دەبێت)</small>
        </div>
        """, unsafe_allow_html=True)

    if st.button("🚀 وەرگێڕانی تایتان دەستپێبکە"):
        if input_srt and active_keys:
            new_hash = get_srt_hash(input_srt)
            db_data = load_state_from_db(db_conn, new_hash)
            if db_data:
                st.session_state.master_context = db_data['master_context']
                st.session_state.enriched_chunks = db_data['enriched_chunks']
                st.session_state.translated_chunks = db_data['translated_chunks']
                st.toast("🔄 داتا لە Database هێنرایەوە!")
            elif new_hash != st.session_state.current_hash:
                st.session_state.master_context = ""
                st.session_state.enriched_chunks = {}
                st.session_state.translated_chunks = {}
                st.session_state.console_logs = []
            st.session_state.current_hash = new_hash
            st.session_state.is_running = True
            st.session_state.start_time = time.time()

if st.session_state.is_running:
    with tab2:
        st.markdown(f"⏱️ **کاتی تێپەڕبوو:** {int(time.time() - st.session_state.start_time) // 60} خولەک")

        st.markdown("### 🖥️ کۆنسۆڵی ڕاستەوخۆی بریکارەکان")
        console_placeholder = st.empty()
        
        def update_console():
            console_placeholder.markdown(f"<div class='console-box'>{''.join(st.session_state.console_logs)}</div>", unsafe_allow_html=True)

        if not st.session_state.master_context:
            log_to_console("بریکاری ١ خەریکی شیکاری چیرۆکە... (ئەمە نزیکەی ٢ خولەکی پێدەچێت)", "yellow")
            update_console()
            
            st.session_state.master_context = agent_1_analyze(active_keys, gemini_model_name, input_srt, glossary, uploaded_video)
            save_state_to_db(db_conn, st.session_state.current_hash, input_srt, st.session_state.master_context, st.session_state.enriched_chunks, st.session_state.translated_chunks)
            
            log_to_console("بریکاری ١ کۆتایی هات! کتێبی وەرگێڕان ئامادەیە.", "lime")
            update_console()

        parsed_data = parse_srt(input_srt)
        chunks = [parsed_data[i:i+15] for i in range(0, len(parsed_data), 15)] # ١٥ دێڕ بۆ ئەوەی داتا زۆرەکە جێگەی ببێتەوە
        
        trans_bar = st.progress(0)
        preview_box = st.empty()
        
        def update_preview():
            current_items = []
            for k, v in sorted(st.session_state.translated_chunks.items()): current_items.extend(v)
            if current_items:
                preview_box.markdown(f"<div class='live-preview-box'>{build_srt(current_items)[-1000:].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

        update_preview()

        chunks_to_process = [ (i, c) for i, c in enumerate(chunks) if i not in st.session_state.translated_chunks ]
        
        if chunks_to_process:
            # دابەشکردنی ئەرکەکان بەسەر کلیلەکاندا
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(active_keys)) as executor:
                future_to_chunk = {}
                for idx, chunk_data in enumerate(chunks_to_process):
                    i, chunk = chunk_data
                    k1 = active_keys[idx % len(active_keys)]
                    k2 = active_keys[(idx + 1) % len(active_keys)]
                    
                    log_to_console(f"ناردنی پارچەی {i+1} بۆ بریکاری ٢ و ٣...", "aqua")
                    update_console()
                    
                    future = executor.submit(process_swarm_pipeline, chunk, k1, k2, gemini_model_name, split_limit, swarm_temp)
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
                            # گەڕانەوە بۆ پێشنیاری 3 (Cinematic) ئەگەر بریکاری کۆتایی شکستی هێنا
                            kur_match = re.search(r'<sug3>(.*?)</sug3>', enriched_data[b_id])
                            if kur_match: new_item['text'] = kur_match.group(1)
                        temp_chunk.append(new_item)
                        
                    st.session_state.translated_chunks[i] = temp_chunk
                    st.session_state.enriched_chunks[i] = enriched_data
                    save_state_to_db(db_conn, st.session_state.current_hash, input_srt, st.session_state.master_context, st.session_state.enriched_chunks, st.session_state.translated_chunks)
                    
                    completed = len(st.session_state.translated_chunks)
                    trans_bar.progress(completed / len(chunks))
                    update_preview()

        final_list = []
        for k, v in sorted(st.session_state.translated_chunks.items()):
            final_list.extend(v)
        st.session_state.final_srt = build_srt(final_list)
        st.session_state.is_running = False
        
        log_to_console("🎉 پرۆسەکە بەسەرکەوتوویی تەواو بوو! بڕۆ بۆ تابی بەرهەم.", "lime")
        update_console()

with tab3:
    if "final_srt" in st.session_state and st.session_state.final_srt:
        st.balloons()
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("📥 داگرتنی فایلی تایتان (.srt)", st.session_state.final_srt, "Studio_PRO_V17_Master.srt")
        with col2:
            st.download_button("📝 داگرتنی وەک دەقی سادە (.txt)", st.session_state.final_srt.replace('-->', '>>'), "Studio_PRO_Text.txt")
        st.text_area("کۆدی پەسەندکراو:", st.session_state.final_srt, height=450)
