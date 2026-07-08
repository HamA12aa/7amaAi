import streamlit as st
import google.generativeai as genai
import time
import re
import random
import tempfile
import sqlite3
import json
import hashlib

# ==========================================
# 0. DATABASE MANAGER (ANTI-REFRESH ULTIMATE FIX)
# ==========================================
# ئەم بەشە ڕێگری دەکات لە سڕینەوەی داتا، تەنانەت ئەگەر بڕاوسەرەکەش دابخەیت!
def init_db():
    conn = sqlite3.connect('studio_pro_database.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS projects
                 (srt_hash TEXT PRIMARY KEY, 
                  last_input TEXT, 
                  master_context TEXT, 
                  translated_chunks TEXT, 
                  reviewed_chunks TEXT)''')
    conn.commit()
    return conn

def get_srt_hash(srt_text):
    return hashlib.md5(srt_text.encode('utf-8')).hexdigest()

def save_state_to_db(conn, srt_hash, last_input, master_context, trans_chunks, rev_chunks):
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO projects 
                 (srt_hash, last_input, master_context, translated_chunks, reviewed_chunks) 
                 VALUES (?, ?, ?, ?, ?)''', 
              (srt_hash, last_input, master_context, json.dumps(trans_chunks), json.dumps(rev_chunks)))
    conn.commit()

def load_state_from_db(conn, srt_hash):
    c = conn.cursor()
    c.execute("SELECT * FROM projects WHERE srt_hash=?", (srt_hash,))
    row = c.fetchone()
    if row:
        return {
            'last_input': row[1],
            'master_context': row[2],
            'translated_chunks': json.loads(row[3]) if row[3] else {},
            'reviewed_chunks': json.loads(row[4]) if row[4] else {}
        }
    return None

# جێگیرکردنی داتابەیس
db_conn = init_db()

# ==========================================
# 1. PRO STUDIO UI & CSS (10x Better)
# ==========================================
st.set_page_config(page_title="AI Movie Studio PRO | V13 Ultimate", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;800&display=swap');
    html, body, [data-testid="stSidebar"], .stMarkdown { font-family: 'Vazirmatn', sans-serif; background-color: #0b0f19;}
    
    .main-title { text-align: center; font-weight: 800; background: linear-gradient(90deg, #ff4b4b, #ff904f, #ff4b4b); background-size: 200% auto; -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px; font-size: 3.5rem; animation: shine 3s linear infinite;}
    @keyframes shine { to { background-position: 200% center; } }
    
    .sub-title { text-align: center; color: #a0a0a0; margin-bottom: 30px; font-size: 1.2rem; letter-spacing: 1px;}
    
    .status-box { background: rgba(20, 25, 35, 0.9); border: 1px solid #333; padding: 18px; border-radius: 12px; margin-bottom: 15px; border-right: 5px solid #00ffcc; color: #fff; box-shadow: 0 4px 15px rgba(0, 255, 204, 0.1); transition: 0.3s;}
    .status-box:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0, 255, 204, 0.2); }
    
    .live-preview-box { background: linear-gradient(145deg, #11151c, #1a202c); padding: 25px; border-radius: 15px; border-top: 5px solid #ff4b4b; color: #e2e8f0; direction: rtl; text-align: right; height: 400px; overflow-y: auto; font-size: 1.15em; line-height: 1.8; box-shadow: inset 0 0 10px rgba(0,0,0,0.5);}
    
    .stTextArea textarea { direction: ltr !important; font-family: 'Courier New', monospace; background-color: #0d1117; color: #00ffcc; border: 1px solid #30363d; border-radius: 10px; padding: 15px;}
    .stTextArea textarea:focus { border-color: #ff4b4b; box-shadow: 0 0 10px rgba(255, 75, 75, 0.3); }
    
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background: linear-gradient(90deg, #ff4b4b 0%, #d42222 100%); color: white; font-size: 1.2em; font-weight: bold; border: none; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); text-transform: uppercase; letter-spacing: 1px;}
    .stButton>button:hover { transform: scale(1.03); box-shadow: 0 8px 25px rgba(255, 75, 75, 0.5); border: none;}
    
    .stProgress > div > div > div > div { background-image: linear-gradient(90deg, #00ffcc, #00b3ff); transition: width 0.5s ease; }
    
    .agent-badge { display: inline-block; padding: 5px 10px; border-radius: 20px; font-size: 0.8em; font-weight: bold; margin-bottom: 5px; background: #2d3748; color: #fff;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SRT PARSER & BUILDER (Agent 5)
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
# 3. AGENT 1: STORY ANALYZER (Video + Text intact)
# ==========================================
def analyze_master_context(active_keys, model_name, srt_text, glossary, video_file=None):
    prompt = f"""You are the Master Story Analyst (Agent 1).
Analyze this subtitle file and create a highly detailed Translation Bible.
Include: Story Summary, Character tone (Age, gender, aggression level), and Cultural notes.
Glossary of specific words to use: {glossary}
Subtitles snippet: {srt_text[:12000]}"""
    
    for current_key in active_keys:
        genai.configure(api_key=current_key)
        model = genai.GenerativeModel(model_name)
        contents = [prompt]
        try:
            if video_file:
                with st.spinner("⏳ بریکاری ١: خەریکی ناردنی ڤیدیۆکەیە بۆ شیکاریی قوڵ (تایم ئاوت: ١٢٠ چرکە)..."):
                    video_file.seek(0)
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                        tmp.write(video_file.read())
                        v_path = tmp.name
                    g_file = genai.upload_file(path=v_path)
                    
                    start_time = time.time()
                    while g_file.state.name == "PROCESSING":
                        if time.time() - start_time > 120:
                            st.warning("⚠️ ڤیدیۆکە زۆری خایاند، تەنها دەق بەکاردێنین.")
                            break
                        time.sleep(3)
                        g_file = genai.get_file(g_file.name)
                    if g_file.state.name == "ACTIVE":
                        contents.insert(0, g_file)
                        
            with st.spinner("🕵️ بریکاری ١: شیکردنەوەی چیرۆک و دروستکردنی کەسایەتییەکان..."):
                response = model.generate_content(contents)
                return response.text
        except Exception as e:
            continue
    return "⚠️ نەتوانرا چیرۆکەکە بەتەواوی شیکار بکرێت، بەڵام وەرگێڕانەکە بەردەوام دەبێت..."

# ==========================================
# 4. AGENTS 2, 3 & 7: SUGGESTER, TRANSLATOR, SPLITTER
# ==========================================
def translate_and_suggest_chunk(chunk, active_keys, master_context, visual_container, selected_model):
    xml_input = "".join([f'<sub id="{item["id"]}">{item["text"].replace("<","").replace(">","")}</sub>\n' for item in chunk])

    prompt = f"""You are Agent 2 (Suggester), Agent 3 (Translator), and Agent 7 (Splitter).
Master Context: {master_context}

PROCESS FOR EACH LINE:
1. Think of 3 Kurdish Sorani translations (Literal, Simple, Cinematic Anime).
2. Choose the absolute BEST cinematic one.
3. NO SHORTENING! Translate every single English word/feeling.
4. SPLIT LOGIC (Agent 7): If the Kurdish translation is very long (over 45 characters), split it into two lines using \n so it looks beautiful on the screen.
5. ONLY output XML.

Input:
{xml_input}

Output Format:
<sub id="1">Kurdish Text\nSecond line if long</sub>
"""
    attempts = 0
    while attempts < len(active_keys) * 3:
        key = random.choice(active_keys)
        try:
            visual_container.markdown(f"<div class='status-box'><span class='agent-badge'>Agent 2, 3 & 7</span><br>⚡ <b>قۆناغی ١:</b> پێشنیارکردن، وەرگێڕان، و ڕێکخستنی دێڕەکان (٣٠ دێڕ)... <br><small>🔑 کلیل: ***{key[-4:]}</small></div>", unsafe_allow_html=True)
            genai.configure(api_key=key)
            model = genai.GenerativeModel(selected_model, generation_config={"temperature": 0.25})
            
            response = model.generate_content(prompt)
            clean_res = response.text.replace('```xml', '').replace('```', '').strip()
            matches = re.findall(r'<sub id="(\d+)"\s*>(.*?)</sub>', clean_res, re.DOTALL | re.IGNORECASE)
            
            if matches: return {m[0].strip(): m[1].strip() for m in matches}
            time.sleep(1)
        except Exception as e:
            if "429" in str(e) or "ResourceExhausted" in str(e): time.sleep(2)
        attempts += 1
    return None

# ==========================================
# 5. AGENT 4: THE DIRECTOR (50 LINES QC REVIEWER)
# ==========================================
def review_50_lines(chunk_50, active_keys, master_context, visual_container, selected_model):
    xml_input = "".join([f'<sub id="{item["id"]}">\nENG: {item["eng_text"]}\nKUR: {item["text"]}\n</sub>\n' for item in chunk_50])

    prompt = f"""You are Agent 4: The Director & Final Reviewer for this Anime.
Master Context: {master_context}

Task: Review these 50 translated lines. 
1. Compare Kurdish (KUR) against the original English (ENG).
2. Fix robotic translations. Make sure it sounds 100% like natural, dramatic Kurdish Sorani.
3. ENSURE NO MEANING IS LOST. If the original has 2 sentences, Kurdish must have 2 sentences.
4. Output ONLY the improved XML. Do not change the IDs.

Input:
{xml_input}

Output Format ONLY:
<sub id="1">Improved Kurdish Text</sub>
"""
    attempts = 0
    while attempts < len(active_keys) * 3:
        key = random.choice(active_keys)
        try:
            visual_container.markdown(f"<div class='status-box' style='border-right-color: #ff904f;'><span class='agent-badge'>Agent 4</span><br>🧐 <b>قۆناغی ٢ (پێداچوونەوە):</b> شیکاری ٥٠ دێڕ بۆ دڵنیابوون لە هەمان هەستی ژاپۆنییەکە... <br><small>🔑 کلیل: ***{key[-4:]}</small></div>", unsafe_allow_html=True)
            genai.configure(api_key=key)
            model = genai.GenerativeModel(selected_model, generation_config={"temperature": 0.15})
            
            response = model.generate_content(prompt)
            clean_res = response.text.replace('```xml', '').replace('```', '').strip()
            matches = re.findall(r'<sub id="(\d+)"\s*>(.*?)</sub>', clean_res, re.DOTALL | re.IGNORECASE)
            
            if matches: return {m[0].strip(): m[1].strip() for m in matches}
            time.sleep(1)
        except Exception as e:
            if "429" in str(e) or "ResourceExhausted" in str(e): time.sleep(2)
        attempts += 1
    return None

# ==========================================
# 6. MAIN UI & STATE INITIALIZATION
# ==========================================
st.markdown("<h1 class='main-title'>AI Movie Studio PRO 🎬 V13</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>سیستەمی ٧ بریکار | داتابەیسی ناوخۆیی (Anti-Refresh) | شکاندنی دێڕی درێژ | پێداچوونەوەی ٥٠ دێڕی</p>", unsafe_allow_html=True)

# Initialization of Streamlit State
if "state_loaded" not in st.session_state:
    st.session_state.translated_chunks = {}
    st.session_state.reviewed_chunks = {}
    st.session_state.master_context = ""
    st.session_state.is_translating = False
    st.session_state.final_srt = ""
    st.session_state.current_hash = ""
    st.session_state.state_loaded = True

with st.sidebar:
    st.header("🔑 کلیلەکان (Agent 6: Load Balancer)")
    api_inputs = [st.text_input(f"Slot {i+1}", type="password") for i in range(4)]
    active_keys = [k.strip() for k in api_inputs if k.strip()]
    
    st.markdown("---")
    st.header("🤖 مۆدێلەکان")
    gemini_model_name = None
    if active_keys:
        try:
            genai.configure(api_key=active_keys[0])
            available_models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            if available_models: gemini_model_name = st.selectbox("مۆدێل:", available_models)
        except: st.error("⚠️ کێشەی کلیل.")
            
    st.markdown("---")
    glossary = st.text_area("📚 فەرهەنگ (Agent 1)", placeholder="وشە تایبەتەکان لێرە بنووسە...")
    uploaded_video = st.file_uploader("🎥 ڤیدیۆ (بۆ هەستی کارەکتەرەکان)", type=['mp4'])

tab1, tab2, tab3 = st.tabs(["📥 ١. فایلی SRT", "⚙️ ٢. ستۆدیۆی ٧-بریکار", "✅ ٣. بەرهەمی کۆتایی"])

with tab1:
    input_srt = st.text_area("دەقی SRT لێرە دابنێ:", height=300)
    start_btn = st.button("🚀 دەستپێکردن / بەردەوامبوون (Auto-Resume)")

if start_btn:
    if not input_srt or not active_keys or not gemini_model_name:
        st.error("کلیل و دەق و مۆدێل پێویستە!")
    else:
        new_hash = get_srt_hash(input_srt)
        
        # گەڕان بەدوای داتادا لەناو داتابەیس ئەگەر ڕیفرێش کرابێت
        db_data = load_state_from_db(db_conn, new_hash)
        
        if db_data:
            st.session_state.translated_chunks = {int(k): v for k, v in db_data['translated_chunks'].items()}
            st.session_state.reviewed_chunks = {int(k): v for k, v in db_data['reviewed_chunks'].items()}
            st.session_state.master_context = db_data['master_context']
            st.toast("🔄 داتا لە داتابەیسەوە هێنرایەوە! هیچت نەفەوتاوە.")
        elif new_hash != st.session_state.current_hash:
            st.session_state.translated_chunks = {}
            st.session_state.reviewed_chunks = {}
            st.session_state.master_context = ""
            
        st.session_state.current_hash = new_hash
        st.session_state.is_translating = True

# ==========================================
# 7. THE MAIN ENGINE (PIPELINE)
# ==========================================
if st.session_state.is_translating:
    with tab2:
        if not st.session_state.master_context:
            st.session_state.master_context = analyze_master_context(active_keys, gemini_model_name, input_srt, glossary, uploaded_video)
            save_state_to_db(db_conn, st.session_state.current_hash, input_srt, st.session_state.master_context, st.session_state.translated_chunks, st.session_state.reviewed_chunks)
            st.success("✅ چیرۆک شیکرایەوە و لە داتابەیس پاشەکەوت کرا.")

        parsed_data = parse_srt(input_srt)
        
        # --- PHASE 1: TRANSLATE (30 LINES) ---
        chunk_size_1 = 30
        trans_chunks = [parsed_data[i:i+chunk_size_1] for i in range(0, len(parsed_data), chunk_size_1)]
        
        st.markdown("### 🔄 قۆناغی یەکەم: وەرگێڕانی خێرا و شکاندنی دێڕەکان")
        prog_bar_1 = st.progress(0)
        status_box_1 = st.empty()
        
        all_translated_items = []
        for i, chunk in enumerate(trans_chunks):
            if i not in st.session_state.translated_chunks:
                res = translate_and_suggest_chunk(chunk, active_keys, st.session_state.master_context, status_box_1, gemini_model_name)
                temp_chunk = []
                for item in chunk:
                    new_item = item.copy()
                    new_item['eng_text'] = item['text'] # سەیڤکردنی ئینگلیزی بۆ قۆناغی ٢
                    if res and str(item['id']) in res:
                        new_item['text'] = res[str(item['id'])]
                    temp_chunk.append(new_item)
                st.session_state.translated_chunks[i] = temp_chunk
                # سەیڤکردن لە داتابەیس دوای هەر پارچەیەک
                save_state_to_db(db_conn, st.session_state.current_hash, input_srt, st.session_state.master_context, st.session_state.translated_chunks, st.session_state.reviewed_chunks)
            
            all_translated_items.extend(st.session_state.translated_chunks[i])
            prog_bar_1.progress((i + 1) / len(trans_chunks))
            
        status_box_1.empty()
        st.success("✅ قۆناغی یەکەم تەواو بوو! دەستپێکردنی قۆناغی دووەم (پێداچوونەوەی سینەمایی)...")

        # --- PHASE 2: REVIEW (50 LINES) ---
        chunk_size_2 = 50
        review_chunks = [all_translated_items[i:i+chunk_size_2] for i in range(0, len(all_translated_items), chunk_size_2)]
        
        st.markdown("### 🧐 قۆناغی دووەم: پێداچوونەوەی ٥٠ دێڕ بە ٥٠ دێڕ")
        prog_bar_2 = st.progress(0)
        review_status = st.empty()
        preview_box = st.empty()
        
        final_reviewed_items = []
        
        # پیشاندانی ئەوەی پێشتر کراوە
        current_preview = ""
        for k, v in sorted(st.session_state.reviewed_chunks.items()):
            current_preview += build_srt(v) + "\n\n"
        if current_preview:
            preview_box.markdown(f"<div class='live-preview-box'>{current_preview[-1500:].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
        
        for i, chunk in enumerate(review_chunks):
            if i not in st.session_state.reviewed_chunks:
                res = review_50_lines(chunk, active_keys, st.session_state.master_context, review_status, gemini_model_name)
                reviewed_chunk = []
                for item in chunk:
                    new_item = item.copy()
                    if res and str(item['id']) in res:
                        new_item['text'] = res[str(item['id'])]
                    # دڵنیابوون لەوەی eng_text دەسڕینەوە بۆ فایلی کۆتایی
                    if 'eng_text' in new_item:
                        del new_item['eng_text']
                    reviewed_chunk.append(new_item)
                st.session_state.reviewed_chunks[i] = reviewed_chunk
                
                # سەیڤکردن لە داتابەیس دوای هەر پێداچوونەوەیەک
                save_state_to_db(db_conn, st.session_state.current_hash, input_srt, st.session_state.master_context, st.session_state.translated_chunks, st.session_state.reviewed_chunks)
            
            final_reviewed_items.extend(st.session_state.reviewed_chunks[i])
            
            # Live Preview Update
            current_preview = build_srt(final_reviewed_items)
            preview_box.markdown(f"<div class='live-preview-box'>{current_preview[-1500:].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
            prog_bar_2.progress((i + 1) / len(review_chunks))
            
        st.session_state.final_srt = build_srt(final_reviewed_items)
        st.session_state.is_translating = False
        review_status.success("🎉 پیرۆزە! بەرهەمەکە ئامادەیە بە کوالێتی ١٠٠٪ سینەمایی.")

with tab3:
    if st.session_state.final_srt:
        st.balloons()
        st.download_button("📥 داگرتنی فایلی کۆتایی (پێداچوونەوەکراو - .srt)", st.session_state.final_srt, "Studio_PRO_V13_Ultimate.srt")
        st.markdown("<h3 style='direction: rtl;'>📝 کۆدی پەسەندکراو</h3>", unsafe_allow_html=True)
        st.text_area("", st.session_state.final_srt, height=450, label_visibility="collapsed")
    else:
        st.info("هێشتا پرۆسەکە تەواو نەبووە...")
