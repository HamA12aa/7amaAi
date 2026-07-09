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

# ==========================================
# 0. INITIAL STATE & DB
# ==========================================
for k in ["is_running", "current_hash", "master_context", "translated_chunks", "console_logs", "final_srt"]:
    if k not in st.session_state: st.session_state[k] = False if "is" in k else ""
if "console_logs" not in st.session_state: st.session_state.console_logs = []
if "translated_chunks" not in st.session_state: st.session_state.translated_chunks = {}

def init_db():
    conn = sqlite3.connect('studio_v20.db', check_same_thread=False)
    conn.cursor().execute('''CREATE TABLE IF NOT EXISTS projects (hash TEXT PRIMARY KEY, context TEXT, trans TEXT)''')
    conn.commit()
    return conn

db_conn = init_db()

# ==========================================
# 1. UI & DESIGN
# ==========================================
st.set_page_config(page_title="AI Movie Studio PRO | V20", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn&display=swap');
    html, body, .stMarkdown { font-family: 'Vazirmatn', sans-serif; background-color: #050505; color: white; }
    .main-title { text-align: center; color: #00ffcc; font-size: 3rem; font-weight: 800; text-shadow: 0 0 10px #00ffcc; }
    .console { background: #000; border: 1px solid #333; padding: 10px; height: 250px; overflow-y: auto; color: #00ff00; font-family: monospace; direction: ltr; }
    .preview { background: #111; padding: 20px; border-radius: 10px; border-top: 4px solid #ff0055; direction: rtl; text-align: right; height: 350px; overflow-y: auto; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CORE LOGIC & API
# ==========================================
def log(msg, color="lime"):
    st.session_state.console_logs.append(f"<span style='color:{color}'>- {msg}</span>")
    if len(st.session_state.console_logs) > 50: st.session_state.console_logs.pop(0)

def call_gemini_api(prompt, api_key, model_name):
    # ناردنی ڕاستەوخۆ بە فلتەری کوژاوە
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ],
        "generationConfig": {"temperature": 0.2, "topP": 0.8, "topK": 40}
    }
    try:
        response = requests.post(url, json=payload, timeout=50)
        if response.status_code == 200:
            res_json = response.json()
            if 'candidates' in res_json:
                return res_json['candidates'][0]['content']['parts'][0]['text']
        return f"ERROR_CODE_{response.status_code}"
    except Exception as e:
        return f"EXCEPTION_{str(e)}"

# ==========================================
# 3. AGENT LOGIC
# ==========================================
def translate_chunk(chunk, context, keys, model):
    xml_data = "".join([f'<line id="{item["id"]}">{item["text"]}</line>\n' for item in chunk])
    
    prompt = f"""You are a professional Kurdish Sorani translator. 
Context: {context}
Task: Translate every single line to Kurdish Sorani perfectly.

RULES:
1. Output ONLY the Kurdish translation inside <line id="X">...</line> tags.
2. NEVER keep English text.
3. Keep the original ID.

Input:
{xml_data}"""

    for _ in range(3): # ٣ جار هەوڵ دەداتەوە ئەگەر ئێرۆر بوو
        key = random.choice(keys)
        result = call_gemini_api(prompt, key, model)
        if "ERROR" not in result and "EXCEPTION" not in result:
            # پاککردنەوە و دەرهێنانی داتا
            matches = re.findall(r'<line id="(\d+)">(.*?)</line>', result, re.DOTALL)
            if matches:
                return {m[0]: m[1].strip() for m in matches}
        time.sleep(2)
    return None

# ==========================================
# 4. MAIN APP
# ==========================================
st.markdown("<h1 class='main-title'>AI Movie Studio PRO V20</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.header("🔑 API Keys")
    keys = [st.text_input(f"Key {i+1}", type="password") for i in range(4)]
    active_keys = [k.strip() for k in keys if k.strip()]
    model_name = st.selectbox("Model", ["gemini-1.5-flash", "gemini-1.5-pro"])
    glossary = st.text_area("Glossary")
    if st.button("🗑️ Clear Database"):
        db_conn.cursor().execute("DELETE FROM projects")
        db_conn.commit()
        st.experimental_rerun()

input_srt = st.text_area("Paste SRT here", height=250)

tab1, tab2 = st.tabs(["🚀 Translation Studio", "✅ Output"])

with tab1:
    col_run, col_status = st.columns([1, 2])
    with col_run:
        if st.button("START TRANSLATION"):
            if input_srt and active_keys:
                st.session_state.current_hash = hashlib.md5(input_srt.encode()).hexdigest()
                st.session_state.is_running = True
                st.session_state.translated_chunks = {}
                
    console_placeholder = st.empty()
    preview_placeholder = st.empty()

    if st.session_state.is_running:
        # 1. شیکاری سەرەتایی
        if not st.session_state.master_context:
            log("Analyzing story context...", "cyan")
            ctx_prompt = f"Summarize the characters and tone of this movie: {input_srt[:5000]}"
            st.session_state.master_context = call_gemini_api(ctx_prompt, random.choice(active_keys), model_name)
        
        # 2. پارچەکردن (١٥ دێڕ)
        blocks = re.split(r'\n\n+', input_srt.strip())
        parsed = []
        for b in blocks:
            lines = b.split('\n')
            if len(lines) >= 3:
                parsed.append({'id': lines[0], 'time': lines[1], 'text': '\n'.join(lines[2:])})
        
        chunks = [parsed[i:i+15] for i in range(0, len(parsed), 15)]
        
        for i, chunk in enumerate(chunks):
            if i not in st.session_state.translated_chunks:
                log(f"Translating chunk {i+1}/{len(chunks)}...")
                result = translate_chunk(chunk, st.session_state.master_context, active_keys, model_name)
                
                if result:
                    # گۆڕینی ئینگلیزی بۆ کوردی لەناو پارچەکەدا
                    for item in chunk:
                        if item['id'] in result:
                            item['text'] = result[item['id']]
                    st.session_state.translated_chunks[i] = chunk
                    log(f"Chunk {i+1} Success ✅", "lime")
                else:
                    log(f"Chunk {i+1} Failed ❌ (Google rejected the request)", "red")
                    # هێشتنەوەی ئینگلیزییەکە تەنها بۆ ئەوەی بەرنامەکە نەوەستێت
                    st.session_state.translated_chunks[i] = chunk
                
                # Update UI
                console_placeholder.markdown(f"<div class='console'>{'<br>'.join(st.session_state.console_logs)}</div>", unsafe_allow_html=True)
                
                all_items = []
                for k in sorted(st.session_state.translated_chunks.keys()):
                    all_items.extend(st.session_state.translated_chunks[k])
                
                preview_text = "\n\n".join([f"{x['id']}\n{x['time']}\n{x['text']}" for x in all_items])
                preview_placeholder.markdown(f"<div class='preview'>{preview_text[-1000:].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
                
        st.session_state.final_srt = "\n\n".join([f"{x['id']}\n{x['time']}\n{x['text']}" for x in all_items])
        st.session_state.is_running = False
        st.success("Translation finished!")

with tab2:
    if st.session_state.final_srt:
        st.download_button("Download SRT", st.session_state.final_srt, "Final_Kurdish.srt")
        st.text_area("Final Content", st.session_state.final_srt, height=400)
