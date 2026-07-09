import streamlit as st
import google.generativeai as genai
import time
import re
import random
import sqlite3
import json
import hashlib
import concurrent.futures
import requests
import tempfile

# ==========================================
# 0. ABSOLUTE INITIALIZATION (FIXING ATTRIBUTE ERROR)
# ==========================================
if 'console_logs' not in st.session_state: st.session_state['console_logs'] = []
if 'is_running' not in st.session_state: st.session_state['is_running'] = False
if 'master_context' not in st.session_state: st.session_state['master_context'] = ""
if 'translated_chunks' not in st.session_state: st.session_state['translated_chunks'] = {}
if 'enriched_chunks' not in st.session_state: st.session_state['enriched_chunks'] = {}
if 'final_srt' not in st.session_state: st.session_state['final_srt'] = ""
if 'start_time' not in st.session_state: st.session_state['start_time'] = 0

# ==========================================
# 1. DATABASE & UI SETUP
# ==========================================
def init_db():
    conn = sqlite3.connect('titan_v21.db', check_same_thread=False)
    conn.cursor().execute('''CREATE TABLE IF NOT EXISTS projects (hash TEXT PRIMARY KEY, context TEXT, trans TEXT)''')
    conn.commit()
    return conn

db_conn = init_db()

st.set_page_config(page_title="AI Movie Studio PRO | V21", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;700&display=swap');
    html, body, [data-testid="stSidebar"], .stMarkdown { font-family: 'Vazirmatn', sans-serif; background-color: #050505; color: #eee; }
    .main-title { text-align: center; font-weight: 800; background: linear-gradient(90deg, #00ffcc, #ff0055); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 3.5rem; }
    .console-box { background: #000; border: 1px solid #333; padding: 15px; height: 280px; overflow-y: auto; color: #00ff00; font-family: 'Courier New', monospace; font-size: 0.9em; border-radius: 10px; box-shadow: inset 0 0 10px #00ff0022; }
    .live-preview { background: #111; padding: 20px; border-radius: 15px; border-top: 5px solid #ff0055; direction: rtl; text-align: right; height: 400px; overflow-y: auto; font-size: 1.2em; line-height: 1.8; }
    .status-card { background: #1a1a1a; padding: 15px; border-radius: 10px; border-left: 5px solid #00ffcc; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CORE UTILS & API
# ==========================================
def log(msg, color="lime"):
    timestamp = time.strftime("%H:%M:%S")
    st.session_state['console_logs'].append(f"<span style='color:grey'>[{timestamp}]</span> <span style='color:{color}'>- {msg}</span>")
    if len(st.session_state['console_logs']) > 100: st.session_state['console_logs'].pop(0)

def call_rest_api(prompt, api_key, model="gemini-1.5-flash", temp=0.3):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]],
        "generationConfig": {"temperature": temp, "maxOutputTokens": 4096}
    }
    try:
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        return f"ERROR_{response.status_code}"
    except:
        return "ERROR_TIMEOUT"

# ==========================================
# 3. THE 3-AGENT ARCHITECTURE (ENHANCED)
# ==========================================

# بریکاری ١: شیکەرەوەی قووڵ
def agent_1_master_analysis(srt_text, glossary, keys, model, video_file=None):
    log("بریکاری ١: دەستی کرد بە شیکاری قووڵی چیرۆک و ڤیدیۆ...", "yellow")
    prompt = f"""Analyze this anime/movie script and create a Translation Bible.
1. Summary of plot. 2. Tone of characters. 3. Cultural nuance. 
Glossary: {glossary}
Script: {srt_text[:10000]}"""
    
    # لێرەدا دەتوانیت لۆژیکی ڤیدیۆ زیاد بکەیت ئەگەر کلیلەکانت لیمیت نەکراون، بۆ خێرایی تەنها تێکست بەکاردێنین
    res = call_rest_api(prompt, random.choice(keys), model)
    if "ERROR" in res: return "Translate with high cinematic emotion."
    return res

# بریکاری ٢: دروستکەری نەخشە (Enricher)
def agent_2_blueprint(chunk, context, keys, model):
    xml_input = "".join([f'<line id="{i["id"]}">{i["text"]}</line>' for i in chunk])
    prompt = f"""You are AGENT 2 (The Mastermind). Context: {context}
For each line, output this XML exactly:
<line id="X">
  <jp>Guess Japanese/Anime expression</jp>
  <emotion>Tone of scene</emotion>
  <sug1>Literal Kurdish</sug1>
  <sug2>Simple Kurdish</sug2>
  <sug3>Cinematic Kurdish (Epic/Anime style)</sug3>
</line>

Input:
{xml_input}"""
    
    res = call_rest_api(prompt, random.choice(keys), model, temp=0.4)
    if "ERROR" in res: return None
    
    # پارس کردنی بلۆکەکان
    data = {}
    matches = re.findall(r'<line id="(\d+)">(.*?)</line>', res, re.DOTALL)
    for b_id, content in matches: data[b_id.strip()] = content.strip()
    return data

# بریکاری ٣: وەرگێڕی کۆتایی (Finalizer)
def agent_3_translator(chunk, blueprint, keys, model):
    input_combined = ""
    for item in chunk:
        b_id = str(item['id'])
        info = blueprint.get(b_id, f"<sug3>{item['text']}</sug3>")
        input_combined += f'<line id="{b_id}">\nENG: {item["text"]}\nINFO: {info}\n</line>\n'

    prompt = f"""You are AGENT 3 (The Final Director).
Look at the English and the 3 Kurdish suggestions. 
Pick/Create the most perfect, cinematic Kurdish Sorani translation.
RULES: 
1. NEVER shorten sentences. 
2. If text > 45 chars, split with \\n.
3. OUTPUT ONLY: <line id="X">Perfect Kurdish</line>

Input:
{input_combined}"""

    res = call_rest_api(prompt, random.choice(keys), model, temp=0.2)
    if "ERROR" in res: return None
    
    matches = re.findall(r'<line id="(\d+)">(.*?)</line>', res, re.DOTALL)
    return {m[0]: m[1].strip() for m in matches} if matches else None

# ==========================================
# 4. SWARM PIPELINE (PARALLEL)
# ==========================================
def process_chunk_swarm(idx, chunk, context, keys, model):
    # هەنگاوی ١: بریکاری ٢
    blueprint = agent_2_blueprint(chunk, context, keys, model)
    if not blueprint: return idx, None, "❌ بریکاری ٢ شکستی هێنا"
    
    # هەنگاوی ٢: بریکاری ٣
    final_res = agent_3_translator(chunk, blueprint, keys, model)
    if not final_res: return idx, None, "❌ بریکاری ٣ شکستی هێنا"
    
    # ئامادەکردنی داتا
    translated_lines = []
    for item in chunk:
        new_item = item.copy()
        if item['id'] in final_res:
            new_item['text'] = final_res[item['id']]
        translated_lines.append(new_item)
    
    return idx, translated_lines, "✅ سەرکەوتوو بوو"

# ==========================================
# 5. UI LAYOUT
# ==========================================
st.markdown("<h1 class='main-title'>AI MOVIE STUDIO TITAN V21</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.header("🔑 API ACCESS")
    keys_input = [st.text_input(f"API Key {i+1}", type="password") for i in range(4)]
    active_keys = [k.strip() for k in keys_input if k.strip()]
    
    st.markdown("---")
    model_choice = st.selectbox("Intelligence Level", ["gemini-1.5-flash", "gemini-1.5-pro"])
    glossary = st.text_area("📚 Glossary / فەرهەنگ")
    
    if st.button("🗑️ Reset All Data"):
        st.session_state.clear()
        st.rerun()

tab1, tab2, tab3 = st.tabs(["🎬 Production", "🖥️ System Logs", "📥 Export"])

with tab1:
    input_srt = st.text_area("Paste SRT Content Here", height=250)
    
    col1, col2 = st.columns(2)
    with col1:
        start_btn = st.button("🚀 LAUNCH TITAN ENGINE")
    with col2:
        if input_srt:
            line_count = len(re.split(r'\n\n+', input_srt.strip()))
            st.info(f"Detected: {line_count} Lines | ETA: ~{int(line_count/15 * 1.2)} min")

    if start_btn and active_keys and input_srt:
        st.session_state['is_running'] = True
        st.session_state['start_time'] = time.time()
        st.session_state['translated_chunks'] = {}
        st.session_state['master_context'] = ""
        st.session_state['console_logs'] = []

    # UI Elements for Progress
    console_ui = st.empty()
    preview_ui = st.empty()

    if st.session_state['is_running']:
        # Step 1: Master Context
        if not st.session_state['master_context']:
            st.session_state['master_context'] = agent_1_master_analysis(input_srt, glossary, active_keys, model_choice)
            log("✅ بریکاری ١: شیکاری چیرۆک کۆتایی هات.", "lime")

        # Step 2: Parse & Chunk
        blocks = re.split(r'\n\n+', input_srt.strip())
        parsed = []
        for b in blocks:
            lines = b.split('\n')
            if len(lines) >= 3:
                parsed.append({'id': lines[0].strip(), 'time': lines[1].strip(), 'text': '\n'.join(lines[2:]).strip()})
        
        chunks = [parsed[i:i+12] for i in range(0, len(parsed), 12)] # هەر جارەی ١٢ دێڕ بۆ کوالێتی بەرز
        
        # Parallel Execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(active_keys)) as executor:
            futures = {executor.submit(process_chunk_swarm, i, chunk, st.session_state['master_context'], active_keys, model_choice): i for i, chunk in enumerate(chunks)}
            
            for future in concurrent.futures.as_completed(futures):
                idx, result, status = future.result()
                if result:
                    st.session_state['translated_chunks'][idx] = result
                    log(f"پارچەی {idx+1}: {status}", "lime")
                else:
                    log(f"پارچەی {idx+1}: {status}", "red")
                
                # Live Refresh UI
                with console_ui:
                    st.markdown(f"<div class='console-box'>{''.join(st.session_state['console_logs'])}</div>", unsafe_allow_html=True)
                
                with preview_ui:
                    all_trans = []
                    for k in sorted(st.session_state['translated_chunks'].keys()): all_trans.extend(st.session_state['translated_chunks'][k])
                    preview_text = "\n\n".join([f"{x['id']}\n{x['time']}\n{x['text']}" for x in all_trans])
                    st.markdown(f"<div class='live-preview'>{preview_text[-1200:].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

        st.session_state['is_running'] = False
        st.success("TITAN ENGINE COMPLETED.")

with tab2:
    st.markdown(f"<div class='console-box' style='height:600px;'>{''.join(st.session_state['console_logs'])}</div>", unsafe_allow_html=True)

with tab3:
    all_final = []
    for k in sorted(st.session_state['translated_chunks'].keys()): all_final.extend(st.session_state['translated_chunks'][k])
    if all_final:
        final_srt_text = "\n\n".join([f"{x['id']}\n{x['time']}\n{x['text']}" for x in all_final])
        st.download_button("📥 DOWNLOAD FINAL SRT", final_srt_text, "Titan_Studio_PRO.srt")
        st.text_area("Final Output Raw", final_srt_text, height=400)
