import streamlit as st
import google.generativeai as genai
import time
import re
import random
import tempfile
import math

# ==========================================
# 1. PRO STUDIO UI & CSS (V12)
# ==========================================
st.set_page_config(page_title="AI Movie Studio PRO | V12", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;800&display=swap');
    html, body, [data-testid="stSidebar"], .stMarkdown { font-family: 'Vazirmatn', sans-serif; }
    
    .main-title { text-align: center; font-weight: 800; background: -webkit-linear-gradient(45deg, #ff4b4b, #ff904f); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px; font-size: 3rem;}
    .sub-title { text-align: center; color: #a0a0a0; margin-bottom: 30px; font-size: 1.2rem; }
    
    .status-box { background: rgba(14, 17, 23, 0.8); border: 1px solid #333; padding: 15px; border-radius: 12px; margin-bottom: 10px; border-right: 4px solid #00ffcc; color: #fff;}
    .live-preview-box { background: #111; padding: 20px; border-radius: 12px; border-top: 4px solid #ff4b4b; color: #ddd; direction: rtl; text-align: right; height: 350px; overflow-y: auto; font-size: 1.1em; line-height: 1.6;}
    
    .stTextArea textarea { direction: ltr !important; font-family: 'Courier New', monospace; background-color: #0a0a0a; color: #00ffcc; border: 1px solid #333; border-radius: 8px;}
    .stTextArea textarea:focus { border-color: #ff4b4b; box-shadow: 0 0 5px rgba(255, 75, 75, 0.5); }
    
    .stButton>button { width: 100%; border-radius: 10px; height: 3.8em; background: linear-gradient(90deg, #ff4b4b 0%, #d42222 100%); color: white; font-size: 1.1em; font-weight: bold; border: none; transition: 0.3s;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SESSION STATE (ANTI-CRASH)
# ==========================================
if "translated_chunks" not in st.session_state:
    st.session_state.translated_chunks = {}
if "reviewed_chunks" not in st.session_state:
    st.session_state.reviewed_chunks = {}
if "last_srt_input" not in st.session_state:
    st.session_state.last_srt_input = ""
if "master_context" not in st.session_state:
    st.session_state.master_context = ""
if "is_translating" not in st.session_state:
    st.session_state.is_translating = False
if "final_srt" not in st.session_state:
    st.session_state.final_srt = ""

# ==========================================
# 3. SRT PARSER & BUILDER (Agent 5: Subtitle Engineer)
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
# 4. AGENT 1: STORY ANALYZER
# ==========================================
def analyze_master_context(active_keys, model_name, srt_text, glossary, video_file=None):
    prompt = f"""Analyze this subtitle file. Create a Translation Bible (Tone, Cultural notes, Character dynamics).
Glossary: {glossary}
Subtitles: {srt_text[:10000]}"""
    
    for key in active_keys:
        genai.configure(api_key=key)
        try:
            model = genai.GenerativeModel(model_name)
            with st.spinner("🕵️ بریکاری ١: شیکردنەوەی چیرۆک..."):
                return model.generate_content(prompt).text
        except: continue
    return "Basic Context: Translate carefully."

# ==========================================
# 5. AGENTS 2 & 3: SUGGESTER + TRANSLATOR (Fast Pipeline)
# ==========================================
def translate_and_suggest_chunk(chunk, active_keys, master_context, visual_container, selected_model):
    xml_input = "".join([f'<sub id="{item["id"]}">{item["text"].replace("<","").replace(">","")}</sub>\n' for item in chunk])

    # پرۆمپتی یەکخراو بۆ بریکاری ٢ (پێشنیار) و ٣ (وەرگێڕان) بۆ ئەوەی خێرا بێت
    prompt = f"""You are Agent 2 (Suggester) and Agent 3 (Translator) working together.
Context: {master_context}

PROCESS:
1. For each line, mentally generate 3 Kurdish options (Literal, Natural, Anime-style).
2. Choose the absolute best one.
3. NEVER shorten the sentences.
4. ONLY output the final chosen translations in XML format. NO OTHER TEXT.

Input:
{xml_input}

Output format:
<sub id="1">Kurdish Translation</sub>
"""
    attempts = 0
    while attempts < len(active_keys) * 2:
        key = random.choice(active_keys)
        try:
            visual_container.markdown(f"<div class='status-box'>💡✍️ <b>بریکاری ٢ و ٣:</b> پێشنیارکردن و وەرگێڕانی ٣٠ دێڕ (کلیل: ***{key[-4:]})</div>", unsafe_allow_html=True)
            genai.configure(api_key=key)
            model = genai.GenerativeModel(selected_model, generation_config={"temperature": 0.3})
            
            response = model.generate_content(prompt)
            clean_res = response.text.replace('```xml', '').replace('```', '').strip()
            matches = re.findall(r'<sub id="(\d+)"\s*>(.*?)</sub>', clean_res, re.DOTALL)
            
            if matches: return {m[0].strip(): m[1].strip() for m in matches}
            time.sleep(1)
        except Exception as e:
            if "429" in str(e): time.sleep(2)
        attempts += 1
    return None

# ==========================================
# 6. AGENT 4: THE REVIEWER (50 Lines QC)
# ==========================================
def review_50_lines(chunk_50, active_keys, master_context, visual_container, selected_model):
    xml_input = "".join([f'<sub id="{item["id"]}">\nENG: {item["eng_text"]}\nKUR: {item["text"]}\n</sub>\n' for item in chunk_50])

    # پرۆمپتی پێداچوونەوەکاری ٥٠ دێڕی
    prompt = f"""You are Agent 4: The Final Reviewer & QA Director for an Anime Translation.
Master Context: {master_context}

Task: Review these 50 translated lines. 
1. Compare the Kurdish (KUR) to English (ENG).
2. Fix weird grammar, robotic literal translations, and ensure it sounds like natural cinematic Kurdish Sorani.
3. Keep the exact emotion of the anime.
4. Output ONLY the improved XML. DO NOT change the IDs.

Input:
{xml_input}

Output Format:
<sub id="1">Improved Kurdish Text</sub>
"""
    attempts = 0
    while attempts < len(active_keys) * 2:
        key = random.choice(active_keys)
        try:
            visual_container.markdown(f"<div class='status-box' style='border-right-color: #ff904f;'>🧐 <b>بریکاری ٤ (پێداچوونەوە):</b> چاکسازی و جوانکردنی ٥٠ دێڕ... (کلیل: ***{key[-4:]})</div>", unsafe_allow_html=True)
            genai.configure(api_key=key)
            model = genai.GenerativeModel(selected_model, generation_config={"temperature": 0.2})
            
            response = model.generate_content(prompt)
            clean_res = response.text.replace('```xml', '').replace('```', '').strip()
            matches = re.findall(r'<sub id="(\d+)"\s*>(.*?)</sub>', clean_res, re.DOTALL)
            
            if matches: return {m[0].strip(): m[1].strip() for m in matches}
            time.sleep(1)
        except Exception as e:
            if "429" in str(e): time.sleep(2)
        attempts += 1
    return None

# ==========================================
# 7. MAIN UI & LOGIC
# ==========================================
st.markdown("<h1 class='main-title'>AI Movie Studio PRO 🎬 V12</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>سیستەمی ٦ بریکار | پێشنیار + وەرگێڕان + پێداچوونەوەی ٥٠ دێڕی</p>", unsafe_allow_html=True)

with st.sidebar:
    st.header("🔑 کلیلەکان (Agent 6)")
    active_keys = [k.strip() for k in [st.text_input(f"Slot {i+1}", type="password") for i in range(4)] if k.strip()]
    
    st.markdown("---")
    gemini_model_name = None
    if active_keys:
        try:
            genai.configure(api_key=active_keys[0])
            gemini_model_name = st.selectbox("مۆدێل:", [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods])
        except: st.error("کێشەی کلیل.")

tab1, tab2, tab3 = st.tabs(["📥 ١. فایلی SRT", "⚙️ ٢. ستۆدیۆی ٦-بریکار", "✅ ٣. بەرهەمی کۆتایی"])

with tab1:
    input_srt = st.text_area("دەقی SRT لێرە دابنێ:", height=300)
    if st.button("🚀 دەستپێکردن"):
        if input_srt != st.session_state.last_srt_input:
            st.session_state.translated_chunks = {}
            st.session_state.reviewed_chunks = {}
            st.session_state.master_context = ""
            st.session_state.last_srt_input = input_srt
        st.session_state.is_translating = True

if st.session_state.is_translating:
    with tab2:
        if not st.session_state.master_context:
            st.session_state.master_context = analyze_master_context(active_keys, gemini_model_name, input_srt, "")
        
        parsed_data = parse_srt(input_srt)
        # 1. قۆناغی وەرگێڕان (٣٠ دێڕ)
        trans_chunks = [parsed_data[i:i+30] for i in range(0, len(parsed_data), 30)]
        
        st.markdown("### 🔄 قۆناغی یەکەم: پێشنیار و وەرگێڕان")
        status_box = st.empty()
        
        all_translated_items = []
        for i, chunk in enumerate(trans_chunks):
            if i not in st.session_state.translated_chunks:
                res = translate_and_suggest_chunk(chunk, active_keys, st.session_state.master_context, status_box, gemini_model_name)
                temp_chunk = []
                for item in chunk:
                    new_item = item.copy()
                    new_item['eng_text'] = item['text'] # پاراستنی ئینگلیزییەکە بۆ پێداچوونەوە
                    if res and str(item['id']) in res:
                        new_item['text'] = res[str(item['id'])]
                    temp_chunk.append(new_item)
                st.session_state.translated_chunks[i] = temp_chunk
            all_translated_items.extend(st.session_state.translated_chunks[i])
            
        status_box.empty()
        st.success("✅ وەرگێڕانی سەرەتایی تەواو بوو. دەستپێکردنی پێداچوونەوە...")

        # 2. قۆناغی پێداچوونەوە (٥٠ دێڕ) - Agent 4
        review_chunks = [all_translated_items[i:i+50] for i in range(0, len(all_translated_items), 50)]
        st.markdown("### 🧐 قۆناغی دووەم: پێداچوونەوەی سینەمایی (٥٠ دێڕ)")
        review_status = st.empty()
        preview_box = st.empty()
        
        final_reviewed_items = []
        current_preview = ""
        
        for i, chunk in enumerate(review_chunks):
            if i not in st.session_state.reviewed_chunks:
                res = review_50_lines(chunk, active_keys, st.session_state.master_context, review_status, gemini_model_name)
                reviewed_chunk = []
                for item in chunk:
                    new_item = item.copy()
                    if res and str(item['id']) in res:
                        new_item['text'] = res[str(item['id'])]
                    reviewed_chunk.append(new_item)
                st.session_state.reviewed_chunks[i] = reviewed_chunk
            
            final_reviewed_items.extend(st.session_state.reviewed_chunks[i])
            
            # Update Live Preview
            current_preview = build_srt(final_reviewed_items)
            preview_box.markdown(f"<div class='live-preview-box'>{current_preview[-1000:].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
            
        st.session_state.final_srt = build_srt(final_reviewed_items)
        st.session_state.is_translating = False
        review_status.success("🎉 هەموو قۆناغەکان بە سەرکەوتوویی تەواو بوون!")

with tab3:
    if st.session_state.final_srt:
        st.balloons()
        st.download_button("📥 داگرتنی فایلی کۆتایی (پێداچوونەوەکراو)", st.session_state.final_srt, "Studio_PRO_V12.srt")
        st.text_area("کۆدی کۆتایی:", st.session_state.final_srt, height=400)
