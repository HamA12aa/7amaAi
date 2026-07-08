import streamlit as st
import requests
import time
import re
import json
import random

# ==========================================
# 1. UI SETUP & BEAUTIFUL CSS
# ==========================================
st.set_page_config(page_title="AI Movie Director PRO | V8.0", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;800&display=swap');
    * { font-family: 'Vazirmatn', sans-serif; }
    .main-title { text-align: center; font-weight: 800; color: #E50914; margin-bottom: 5px; }
    .sub-title { text-align: center; color: #808080; margin-bottom: 30px; font-size: 1.2rem; }
    .agent-box { background: #1E1E1E; color: #00FF00; padding: 15px; border-radius: 10px; font-family: monospace; direction: ltr; margin-bottom: 10px; border-left: 5px solid #00FF00; }
    .stTextArea textarea { direction: ltr !important; font-family: monospace; background-color: #2b2b2b; color: white;}
    .kurdish-preview { direction: rtl; text-align: right; background-color: #1e1e1e; padding: 15px; border-radius: 10px; border-right: 5px solid #E50914; color: #ffffff;}
    div[data-baseweb="tab-list"] { justify-content: center; }
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
# 3. DIRECT REST API LOGIC (BYPASSES 404 ERROR)
# ==========================================
def translate_chunk_direct(chunk, active_keys, glossary, visual_container, selected_model):
    if not active_keys:
        raise Exception("کلیلەکان بەتاڵن!")

    # ئامادەکردنی دەقەکە بە شێوازی XML
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
    
    # ئامادەکردنی داتا بۆ ناردنی ڕاستەوخۆ
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2}
    }
    headers = {'Content-Type': 'application/json'}

    fallback_models = [selected_model, "gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
    models_to_try = []
    for m in fallback_models:
        if m not in models_to_try:
            models_to_try.append(m)

    current_model_index = 0
    attempts = 0
    max_attempts = len(active_keys) * 4

    while attempts < max_attempts:
        current_key = random.choice(active_keys)
        current_model = models_to_try[current_model_index]
        
        # دروستکردنی لینکی ڕاستەوخۆی API
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={current_key}"
        
        try:
            visual_container.markdown(f"<div class='agent-box'>⚙️ [Agent]: Connecting Directly (Key: ***{current_key[-4:]}) | Model: <b>{current_model}</b></div>", unsafe_allow_html=True)
            visual_container.markdown(f"<div class='agent-box'>🧠 [Agent]: Bypassing SDK & Translating...</div>", unsafe_allow_html=True)
            
            # ناردنی داواکارییەکە بەبێ بەکارهێنانی کتێبخانەی گووگڵ
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                res_json = response.json()
                try:
                    response_text = res_json['candidates'][0]['content']['parts'][0]['text']
                    clean_response = response_text.replace('```xml', '').replace('```', '').strip()
                    
                    matches = re.findall(r'<sub id="(\d+)"\s*>(.*?)</sub>', clean_response, re.DOTALL | re.IGNORECASE)
                    
                    if matches:
                        result_map = {m[0].strip(): m[1].strip() for m in matches}
                        visual_container.markdown(f"<div class='agent-box'>✅ [Agent]: Extraction successful!</div>", unsafe_allow_html=True)
                        return result_map
                    else:
                        visual_container.warning("⚠️ مۆدێلەکە فۆرماتەکەی تێکدا، دووبارە هەوڵدەدەینەوە...")
                        time.sleep(1)
                except Exception as parse_e:
                    visual_container.warning(f"⚠️ کێشە لە خوێندنەوەی وەڵامەکە: {parse_e}")
                    time.sleep(1)
                    
            elif response.status_code == 429:
                visual_container.error(f"🔴 Limit 429 Reached! Switching keys...")
                time.sleep(2)
            elif response.status_code == 404:
                visual_container.error(f"🔴 Error 404: مۆدێلی {current_model} نەدۆزرایەوە لە سێرڤەرەکانی گووگڵ. گەڕان بەدوای مۆدێلێکی تردا...")
                current_model_index += 1
                if current_model_index >= len(models_to_try):
                    return None
                time.sleep(1)
            else:
                visual_container.error(f"❌ Error {response.status_code}: {response.text[:100]}")
                time.sleep(2)
                
        except Exception as e:
            visual_container.error(f"❌ Error: {str(e)[:80]}")
            time.sleep(2)
            
        attempts += 1
        
    return None

# ==========================================
# 4. MAIN UI LAYOUT
# ==========================================
st.markdown("<h1 class='main-title'>🎬 AI Movie Director PRO (V8.0)</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>وەشانی ٨ - ڕێکخراو بە سیستەمی Direct API Request (چارەسەری کۆتایی هەڵەی 404)</p>", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ ڕێکخستنەکان")
    ai_model = st.selectbox("🤖 مۆدێلی زیرەکی دەستکرد:", 
                            ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"],
                            index=0)
    
    st.markdown("---")
    st.header("🔑 کلیلی API")
    api_inputs = [
        st.text_input("Slot 1", type="password"),
        st.text_input("Slot 2", type="password"),
        st.text_input("Slot 3", type="password"),
        st.text_input("Slot 4", type="password")
    ]
    active_keys = [k.strip() for k in api_inputs if k.strip()]
    
    st.markdown("---")
    glossary = st.text_area("📚 فەرهەنگی ناوەکان", placeholder="Batman -> پیاوی شەمشەمەکوێرە")
    st.success(f"{len(active_keys)} کلیل چالاکە ✅")

tab1, tab2, tab3 = st.tabs(["📥 ١. دانانی SRT", "⚙️ ٢. پڕۆسە (Live)", "✅ ٣. بینین و داگرتن"])

with tab1:
    input_srt = st.text_area("کۆدی SRT لێرە دابنێ:", height=300)
    start_btn = st.button("🚀 دەستپێکردنی وەرگێڕان", use_container_width=True)

if "final_srt" not in st.session_state:
    st.session_state.final_srt = ""
if "is_translating" not in st.session_state:
    st.session_state.is_translating = False

if start_btn:
    if not input_srt:
        st.error("تکایە سەرەتا دەقی SRT دابنێ.")
    elif not active_keys:
        st.error("تکایە لانی کەم یەک کلیلی API دابنێ.")
    else:
        st.session_state.is_translating = True
        st.session_state.final_srt = ""

if getattr(st.session_state, 'is_translating', False):
    with tab2:
        st.info("پڕۆسەی وەرگێڕان دەستی پێکرد، تکایە لێرە مەڕۆ تا تەواو دەبێت...")
        
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
                st.markdown(f"**پارچەی {i+1} بۆ {min(i+chunk_size, total_blocks)} لە کۆی {total_blocks}**")
                
                result_map = translate_chunk_direct(chunk, active_keys, glossary, st.empty(), ai_model)
                
                if result_map:
                    for item in chunk:
                        new_item = item.copy()
                        item_id = str(item['id'])
                        
                        if item_id in result_map and result_map[item_id]:
                            new_item['text'] = result_map[item_id]
                        else:
                            st.warning(f"⚠️ دێڕی {item_id} نەگەڕایەوە، دەقە ئینگلیزییەکە هێڵرایەوە.")
                            
                        translated_final.append(new_item)
                else:
                    st.error(f"❌ ئەم بەشە شکستی هێنا. دەقەکە بە ئینگلیزی دەمێنێتەوە.")
                    translated_final.extend(chunk)
            
            current_srt = build_srt(translated_final)
            live_preview_box.markdown(f"<div class='kurdish-preview'>{current_srt[-600:].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
            progress_bar.progress(min((i + chunk_size) / total_blocks, 1.0))
            time.sleep(1)
            
        st.session_state.final_srt = build_srt(translated_final)
        st.session_state.is_translating = False
        st.success("✅ وەرگێڕان کۆتایی هات! بڕۆ بۆ تابی سێیەم.")

with tab3:
    if st.session_state.final_srt:
        st.balloons()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 👁️ پێشبینینی کوردی")
            st.markdown(f"<div class='kurdish-preview' style='height: 400px; overflow-y: auto;'>{st.session_state.final_srt.replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
        with col2:
            st.markdown("### 📝 کۆدی SRT")
            st.text_area("", st.session_state.final_srt, height=400)
        
        st.download_button("📥 داگرتنی فایلی کۆتایی (.srt)", data=st.session_state.final_srt, file_name="Translated_Movie.srt", use_container_width=True)
    else:
        st.info("هێشتا هیچ فایلێک وەرنەگێڕدراوە.")
