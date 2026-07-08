import streamlit as st
import google.generativeai as genai
import time
import re
import json
import random

# ==========================================
# 1. UI SETUP & BEAUTIFUL CSS
# ==========================================
st.set_page_config(page_title="AI Movie Director PRO | V6.2", layout="wide", page_icon="🎬")

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
# 2. BULLETPROOF SRT PARSER & BUILDER
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

def extract_json_from_text(text):
    """پاککەرەوەیەکی زۆر بەهێز بۆ ئەوەی بە زۆر JSONـەکە دەربهێنێت"""
    try:
        # لادانی هەموو وشە و ماڕکداونێکی زیادە
        clean_text = text.replace('```json', '').replace('```', '').strip()
        # دۆزینەوەی سەرەتا و کۆتایی کەوانەکان
        start_idx = clean_text.find('[')
        end_idx = clean_text.rfind(']') + 1
        
        if start_idx != -1 and end_idx != -1:
            json_str = clean_text[start_idx:end_idx]
            return json.loads(json_str)
    except Exception as e:
        pass
    return None

# ==========================================
# 3. AGENT LOGIC & LOAD BALANCER
# ==========================================
def translate_chunk_with_agents(chunk, active_keys, glossary, visual_container, selected_model):
    if not active_keys:
        raise Exception("کلیلەکان بەتاڵن!")

    input_data = [{"id": item['id'], "english_text": item['text']} for item in chunk]
    json_input = json.dumps(input_data, ensure_ascii=False, indent=2)

    prompt = f"""
    You are an elite cinematic translator. Translate the English subtitles into natural Central Kurdish (Sorani).
    Glossary: {glossary}
    
    You MUST output ONLY a valid JSON array. DO NOT keep the text in English. Translate 'english_text' to Sorani and put it in 'kurdish_text'.
    
    Example output:
    [
      {{"id": "1", "kurdish_text": "سڵاو دنیا"}},
      {{"id": "2", "kurdish_text": "وەرگێڕانەکە بۆ کوردی"}}
    ]
    
    Input JSON to translate:
    {json_input}
    """

    attempts = 0
    while attempts < len(active_keys) * 3:  # هەوڵدانی زیاتر (٣ ئەوەندەی کلیلەکان)
        current_key = random.choice(active_keys)
        try:
            visual_container.markdown(f"<div class='agent-box'>⚙️ [Load Balancer]: Connecting with Key ***{current_key[-4:]}...</div>", unsafe_allow_html=True)
            
            genai.configure(api_key=current_key)
            
            # ناچارکردنی مۆدێلەکە کە تەنها JSON بداتەوە ئەگەر پشتگیری بکات
            try:
                model = genai.GenerativeModel(selected_model, generation_config={"temperature": 0.2, "response_mime_type": "application/json"})
            except:
                # ئەگەر وەشانەکەی کۆن بوو، بەبێ ئەو تایبەتمەندییە کاری پێدەکەین
                model = genai.GenerativeModel(selected_model, generation_config={"temperature": 0.2})
            
            visual_container.markdown(f"<div class='agent-box'>🧠 [Linguist]: Translating text to Kurdish Sorani...</div>", unsafe_allow_html=True)
            
            response = model.generate_content(prompt)
            result_json = extract_json_from_text(response.text)
            
            if result_json:
                visual_container.markdown(f"<div class='agent-box'>✂️ [Editor]: Translation successfully formatted and injected!</div>", unsafe_allow_html=True)
                return result_json
            else:
                visual_container.warning("⚠️ مۆدێلەکە وەڵامەکەی تێکدا، دووبارە هەوڵدەداتەوە...")
                time.sleep(1)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str:
                visual_container.error(f"🔴 Limit 429 Reached! Switching keys...")
                time.sleep(2)
            elif "404" in err_str:
                visual_container.error(f"🔴 Error 404: مۆدێلی {selected_model} نەدۆزرایەوە!")
                return None 
            else:
                visual_container.error(f"❌ Error: {err_str[:80]}")
                time.sleep(1)
        attempts += 1
        
    return None

# ==========================================
# 4. MAIN UI LAYOUT
# ==========================================
st.markdown("<h1 class='main-title'>🎬 AI Movie Director PRO (V6.2)</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>وەرگێڕانی سینەمایی - وەشانی دژە-گلیچ و دڵنیاکەرەوە</p>", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ ڕێکخستنەکان")
    ai_model = st.selectbox("🤖 مۆدێلی زیرەکی دەستکرد:", 
                            ["gemini-1.5-flash-latest", "gemini-1.5-pro-latest", "gemini-1.5-flash", "gemini-pro"],
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
                
                json_result = translate_chunk_with_agents(chunk, active_keys, glossary, st.empty(), ai_model)
                
                if json_result:
                    # گۆڕینی داتا بە شێوەیەکی سەلامەت
                    result_map = {str(item.get('id', '')): item.get('kurdish_text', '') for item in json_result}
                    
                    for item in chunk:
                        new_item = item.copy()
                        if str(new_item['id']) in result_map and result_map[str(new_item['id'])]:
                            new_item['text'] = result_map[str(new_item['id'])]
                        else:
                            st.warning(f"⚠️ دێڕی {new_item['id']} وەرنەگێڕدرا، جارێکی تر تاقی دەکەینەوە...")
                        translated_final.append(new_item)
                else:
                    st.error(f"❌ ئەم بەشە شکستی هێنا لە وەرگێڕان. دەقەکە بە ئینگلیزی دەمێنێتەوە.")
                    translated_final.extend(chunk)
            
            current_srt = build_srt(translated_final)
            live_preview_box.markdown(f"<div class='kurdish-preview'>{current_srt[-500:].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
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
        
        st.download_button("📥 داگرتنی فایلی کۆتایی (.srt)", data=st.session_state.final_srt, file_name="Translated_Kurdish.srt", use_container_width=True)
    else:
        st.info("هێشتا هیچ فایلێک وەرنەگێڕدراوە.")
