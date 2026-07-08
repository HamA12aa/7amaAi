import streamlit as st
import google.generativeai as genai
import time
import re
import random

# ==========================================
# 1. UI SETUP & BEAUTIFUL CSS (Hybrid Style)
# ==========================================
st.set_page_config(page_title="AI Movie Director PRO | V9.0", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;800&display=swap');
    html, body, [data-testid="stSidebar"], .stMarkdown { font-family: 'Vazirmatn', sans-serif; }
    .main-title { text-align: center; font-weight: 800; color: #ff4b4b; margin-bottom: 5px; }
    .agent-box { background: #0e1117; color: #00ffcc; padding: 15px; border-radius: 10px; font-family: monospace; direction: ltr; margin-bottom: 10px; border-left: 5px solid #00ffcc; }
    .stTextArea textarea { direction: ltr !important; font-family: monospace; background-color: #0e1117; color: #00ffcc;}
    .kurdish-preview { direction: rtl; text-align: right; background-color: #1e1e1e; padding: 15px; border-radius: 10px; border-right: 5px solid #ff4b4b; color: #ffffff;}
    div[data-baseweb="tab-list"] { justify-content: center; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; background-color: #ff4b4b; color: white; font-weight: bold; border: none;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. BULLETPROOF SRT PARSER (XML BASED)
# ==========================================
def parse_srt(srt_string):
    srt_string = srt_string.replace('\r\n', '\n').strip()
    blocks = re.split(r'\n\n+', srt_string)
    parsed = []
    for block in blocks:
        lines = block.split('\n')
        if len(lines) >= 3:
            idx = lines[0].strip()
            time_str = lines[1].strip()
            text = '\n'.join(lines[2:]).strip()
            parsed.append({'id': idx, 'time': time_str, 'text': text})
    return parsed

def build_srt(parsed_list):
    return '\n\n'.join([f"{item['id']}\n{item['time']}\n{item['text']}" for item in parsed_list])

# ==========================================
# 3. AGENT LOGIC (XML + Auto-Selected Model)
# ==========================================
def translate_chunk_with_agents(chunk, active_keys, glossary, visual_container, selected_model):
    xml_input = ""
    for item in chunk:
        clean_text = item['text'].replace('<', '').replace('>', '')
        xml_input += f'<sub id="{item["id"]}">{clean_text}</sub>\n'

    prompt = f"""You are an expert movie subtitle translator. 
Translate the English text inside the XML tags to standard Central Kurdish (Sorani).
DO NOT translate the XML tags themselves. KEEP the exact same XML structure.

Rules:
1. Translate ONLY to Sorani Kurdish.
2. Keep the meaning cinematic and natural.
3. Glossary: {glossary}

Input:
{xml_input}

Output MUST be exactly in this format:
<sub id="1">وەرگێڕانەکە لێرە...</sub>
"""

    attempts = 0
    max_attempts = len(active_keys) * 3

    while attempts < max_attempts:
        current_key = random.choice(active_keys)
        try:
            visual_container.markdown(f"<div class='agent-box'>⚙️ [Agent]: Connecting (Key: ***{current_key[-4:]}) | Model: <b>{selected_model}</b></div>", unsafe_allow_html=True)
            
            genai.configure(api_key=current_key)
            model = genai.GenerativeModel(selected_model, generation_config={"temperature": 0.2})
            
            visual_container.markdown(f"<div class='agent-box'>🧠 [Agent]: Translating to Kurdish Sorani...</div>", unsafe_allow_html=True)
            
            response = model.generate_content(prompt)
            clean_response = response.text.replace('```xml', '').replace('```', '').strip()
            
            matches = re.findall(r'<sub id="(\d+)"\s*>(.*?)</sub>', clean_response, re.DOTALL | re.IGNORECASE)
            
            if matches:
                result_map = {m[0].strip(): m[1].strip() for m in matches}
                visual_container.markdown(f"<div class='agent-box'>✅ [Agent]: Extraction successful!</div>", unsafe_allow_html=True)
                return result_map
            else:
                visual_container.warning("⚠️ مۆدێلەکە فۆرماتەکەی تێکدا، دووبارە هەوڵدەدەینەوە...")
                time.sleep(1)
                
        except Exception as e:
            err_str = str(e)
            if "429" in err_str:
                visual_container.error(f"🔴 Limit 429 Reached! Switching keys...")
                time.sleep(2)
            else:
                visual_container.error(f"❌ Error: {err_str[:80]}")
                time.sleep(1)
        attempts += 1
        
    return None

# ==========================================
# 4. MAIN UI & AUTO-FETCHING MODELS
# ==========================================
st.markdown("<h1 class='main-title'>🎬 AI Movie Director PRO (V9.0)</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #808080;'>تێکەڵەی کۆدە کۆنەکەت بۆ دۆزینەوەی مۆدێلەکان و سیستەمی ٤ کلیلی نوێ</p>", unsafe_allow_html=True)

with st.sidebar:
    st.header("🔑 کلیلی API (Google)")
    api_inputs = [
        st.text_input("Slot 1", type="password"),
        st.text_input("Slot 2", type="password"),
        st.text_input("Slot 3", type="password"),
        st.text_input("Slot 4", type="password")
    ]
    active_keys = [k.strip() for k in api_inputs if k.strip()]
    
    st.markdown("---")
    st.header("🤖 مۆدێلەکان (ئۆتۆماتیکی)")
    
    gemini_model_name = None
    if active_keys:
        try:
            # بەکارهێنانی کۆدە کۆنەکەت بۆ دۆزینەوەی مۆدێلە کارپێکراوەکان
            genai.configure(api_key=active_keys[0])
            available_models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name.replace('models/', ''))
            
            if available_models:
                gemini_model_name = st.selectbox("مۆدێلێک هەڵبژێرە:", available_models)
                st.success("مۆدێلەکان بە سەرکەوتوویی دۆزرانەوە! ✅")
        except Exception as e:
            st.error("⚠️ کێشە هەیە لە کلیلەکەت یان ئینتەرنێت.")
    else:
        st.info("سەرەتا کلیلەکان دابنێ بۆ بینینی مۆدێلەکان.")
        
    st.markdown("---")
    glossary = st.text_area("📚 فەرهەنگی ناوەکان", placeholder="Batman -> پیاوی شەمشەمەکوێرە")

tab1, tab2, tab3 = st.tabs(["📥 ١. دانانی SRT", "⚙️ ٢. پڕۆسە (Live)", "✅ ٣. بینین و داگرتن"])

with tab1:
    input_srt = st.text_area("کۆدی SRT لێرە دابنێ:", height=300)
    start_btn = st.button("🚀 دەستپێکردنی وەرگێڕان")

if "final_srt" not in st.session_state:
    st.session_state.final_srt = ""
if "is_translating" not in st.session_state:
    st.session_state.is_translating = False

if start_btn:
    if not input_srt:
        st.warning("تکایە سەرەتا دەقی SRT دابنێ.")
    elif not active_keys:
        st.error("تکایە لانی کەم یەک کلیلی API دابنێ.")
    elif not gemini_model_name:
        st.error("هیچ مۆدێلێک هەڵنەبژێردراوە. تکایە کلیلێکی دروست دابنێ.")
    else:
        st.session_state.is_translating = True
        st.session_state.final_srt = ""

if getattr(st.session_state, 'is_translating', False):
    with tab2:
        st.info(f"پڕۆسەی وەرگێڕان بە مۆدێلی '{gemini_model_name}' دەستی پێکرد...")
        
        parsed_data = parse_srt(input_srt)
        total_blocks = len(parsed_data)
        chunk_size = 10 
        
        translated_final = []
        progress_bar = st.progress(0)
        
        agent_status_box = st.empty()
        live_preview_box = st.empty()
        
        for i in range(0, total_blocks, chunk_size):
            chunk = parsed_data[i : i + chunk_size]
            
            with agent_status_box.container():
                st.markdown(f"**پارچەی {i+1} بۆ {min(i+chunk_size, total_blocks)}**")
                
                result_map = translate_chunk_with_agents(chunk, active_keys, glossary, st.empty(), gemini_model_name)
                
                if result_map:
                    for item in chunk:
                        new_item = item.copy()
                        item_id = str(item['id'])
                        
                        if item_id in result_map and result_map[item_id]:
                            new_item['text'] = result_map[item_id]
                        else:
                            st.warning(f"⚠️ دێڕی {item_id} نەگەڕایەوە.")
                            
                        translated_final.append(new_item)
                else:
                    st.error(f"❌ ئەم بەشە شکستی هێنا.")
                    translated_final.extend(chunk)
            
            current_srt = build_srt(translated_final)
            live_preview_box.markdown(f"<div class='kurdish-preview'>{current_srt[-600:].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
            progress_bar.progress(min((i + chunk_size) / total_blocks, 1.0))
            time.sleep(1)
            
        st.session_state.final_srt = build_srt(translated_final)
        st.session_state.is_translating = False
        st.success("✅ وەرگێڕان تەواو بوو! بڕۆ بۆ تابی سێیەم.")

with tab3:
    if st.session_state.final_srt:
        st.balloons()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<h3 style='direction: rtl;'>👁️ پێشبینینی کوردی</h3>", unsafe_allow_html=True)
            st.markdown(f"<div class='kurdish-preview' style='height: 400px; overflow-y: auto;'>{st.session_state.final_srt.replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
        with col2:
            st.markdown("<h3 style='direction: rtl;'>📝 کۆدی SRT</h3>", unsafe_allow_html=True)
            st.text_area("", st.session_state.final_srt, height=400, label_visibility="collapsed")
        
        st.download_button("📥 داگرتنی فایلی کۆتایی (.srt)", data=st.session_state.final_srt, file_name="Translated_Subtitle.srt")
    else:
        st.info("هێشتا وەرگێڕان نەکراوە.")
