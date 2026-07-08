import streamlit as st
import google.generativeai as genai
import time
import re
import json
import random

# ==========================================
# 1. UI SETUP & BEAUTIFUL CSS
# ==========================================
st.set_page_config(page_title="AI Movie Director PRO | V6.0 Ultimate", layout="wide", page_icon="🎬")

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
    """بۆ دڵنیابوون لەوەی ئەگەر AI تێکستی زیادەی نووسی، تەنها بەشە JSONـەکە دەربهێنین"""
    try:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except:
        pass
    return None

# ==========================================
# 3. AGENT LOGIC & LOAD BALANCER
# ==========================================
def translate_chunk_with_agents(chunk, active_keys, glossary, visual_container):
    if not active_keys:
        raise Exception("کلیلەکان بەتاڵن!")

    # ئامادەکردنی دەقەکە
    input_data = [{"id": item['id'], "english_text": item['text']} for item in chunk]
    json_input = json.dumps(input_data, ensure_ascii=False, indent=2)

    prompt = f"""
    You are 'AI Movie Director PRO'. Translate the english subtitles to natural cinematic Central Kurdish (Sorani).
    Glossary: {glossary}
    
    IMPORTANT: You MUST reply ONLY with a valid JSON array. No extra text, no markdown block quotes.
    Format exactly like this:
    [
      {{"id": "1", "kurdish_text": "سڵاو دنیا"}},
      {{"id": "2", "kurdish_text": "وەرگێڕانەکە لێرە دەبێت"}}
    ]
    
    Input Subtitles:
    {json_input}
    """

    attempts = 0
    while attempts < len(active_keys) * 2:
        current_key = random.choice(active_keys)
        try:
            # 👁️ نیشاندانی کاری بریکاری ٤ (Load Balancer)
            visual_container.markdown(f"<div class='agent-box'>⚙️ [Agent 4 - Load Balancer]: Connecting to slot with key ending in {current_key[-4:]}...</div>", unsafe_allow_html=True)
            
            genai.configure(api_key=current_key)
            model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"temperature": 0.3}) # تێمپریچەری کەم بۆ وردی
            
            # 👁️ نیشاندانی کاری بریکاری ١، ٢ و ٥
            visual_container.markdown(f"<div class='agent-box'>🧠 [Agent 1 & 2 - Linguist/Scriptwriter]: Translating context and adjusting cinematic tone...</div>", unsafe_allow_html=True)
            
            response = model.generate_content(prompt)
            result_json = extract_json_from_text(response.text)
            
            if result_json:
                # 👁️ نیشاندانی کاری بریکاری ٣
                visual_container.markdown(f"<div class='agent-box'>✂️ [Agent 3 - Editor]: Verified JSON format and preserved SRT timestamps perfectly.</div>", unsafe_allow_html=True)
                return result_json
            else:
                visual_container.warning("⚠️ بریکاری سەرنوسەر نەیتوانی فۆرماتەکە بخوێنێتەوە، دووبارە هەوڵدەداتەوە...")
        except Exception as e:
            if "429" in str(e):
                visual_container.error(f"🔴 [Agent 4]: Slot Limit Reached (429)! Switching slots...")
                time.sleep(2)
            else:
                visual_container.error(f"❌ Error: {str(e)[:50]}")
        attempts += 1
        
    return None

# ==========================================
# 4. MAIN UI LAYOUT
# ==========================================
st.markdown("<h1 class='main-title'>🎬 AI Movie Director PRO (V6 Ultimate)</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>وەرگێڕانی سینەمایی بە هەماهەنگی ٥ بریکاری زیرەکی دەستکرد</p>", unsafe_allow_html=True)

# سایدبار
with st.sidebar:
    st.header("🔑 کلیلی API (Slots)")
    api_inputs = [
        st.text_input("Slot 1 (Gemini)", type="password"),
        st.text_input("Slot 2 (Gemini)", type="password"),
        st.text_input("Slot 3 (Gemini)", type="password"),
        st.text_input("Slot 4 (Gemini)", type="password")
    ]
    active_keys = [k.strip() for k in api_inputs if k.strip()]
    
    st.markdown("---")
    glossary = st.text_area("📚 فەرهەنگی ناوەکان", placeholder="Batman -> پیاوی شەمشەمەکوێرە\nJoker -> جۆکەر")
    st.success(f"ئێستا {len(active_keys)} کلیل چالاکە ✅")

# دابەشکردنی لاپەڕەکە بۆ ٣ تاب (بۆ جوانی و ڕێکوپێکی)
tab1, tab2, tab3 = st.tabs(["📥 ١. دانانی فایلی SRT", "⚙️ ٢. پڕۆسەی بریکارەکان (Live)", "✅ ٣. پێشبینین و داگرتن"])

with tab1:
    input_srt = st.text_area("کۆدی SRT لێرە دابنێ (Paste):", height=400, placeholder="1\n00:00:01,000 --> 00:00:04,000\nHello World!")
    start_btn = st.button("🚀 دەستپێکردنی وەرگێڕان", use_container_width=True)

# گۆڕاوەکان (State)
if "final_srt" not in st.session_state:
    st.session_state.final_srt = ""
if "is_translating" not in st.session_state:
    st.session_state.is_translating = False

if start_btn:
    if not input_srt:
        st.error("تکایە سەرەتا دەقی SRT دابنێ لە تابی یەکەم.")
    elif not active_keys:
        st.error("تکایە لانی کەم یەک کلیلی API لە سایدبارەکە دابنێ.")
    else:
        st.session_state.is_translating = True
        st.session_state.final_srt = ""

# پڕۆسەی وەرگێڕان
if getattr(st.session_state, 'is_translating', False):
    with tab2:
        st.info("پڕۆسەی وەرگێڕان دەستی پێکرد، تکایە لێرە مەڕۆ تا تەواو دەبێت...")
        
        parsed_data = parse_srt(input_srt)
        total_blocks = len(parsed_data)
        chunk_size = 8 # پارچەی بچووک بۆ دڵنیایی 100% کە نەوەستێت
        
        translated_final = []
        progress_bar = st.progress(0)
        
        # دروستکردنی شوێنی تایبەت بۆ بینینی کاری بریکارەکان
        agent_status_box = st.empty()
        live_preview_box = st.empty()
        
        for i in range(0, total_blocks, chunk_size):
            chunk = parsed_data[i : i + chunk_size]
            
            with agent_status_box.container():
                st.markdown(f"**پارچەی {i+1} بۆ {min(i+chunk_size, total_blocks)} لە کۆی {total_blocks}**")
                
                # ناردن بۆ مۆدێل
                json_result = translate_chunk_with_agents(chunk, active_keys, glossary, st.empty())
                
                if json_result:
                    # تێکەڵکردنەوەی وەرگێڕانەکە لەگەڵ کاتەکان
                    result_map = {str(item['id']): item['kurdish_text'] for item in json_result if 'id' in item and 'kurdish_text' in item}
                    
                    for item in chunk:
                        new_item = item.copy()
                        if new_item['id'] in result_map:
                            new_item['text'] = result_map[new_item['id']]
                        translated_final.append(new_item)
                else:
                    st.error(f"⚠️ کێشە لە وەرگێڕانی ئەم بەشەدا هەبوو، دەقە ئینگلیزییەکە وەک خۆی هێڵرایەوە.")
                    translated_final.extend(chunk)
            
            # نوێکردنەوەی پێشاندانی ڕاستەوخۆ (Live Preview)
            current_srt = build_srt(translated_final)
            live_preview_box.markdown(f"<div class='kurdish-preview'>{current_srt[-500:].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
            
            progress_bar.progress(min((i + chunk_size) / total_blocks, 1.0))
            time.sleep(1) # پشووی بچووک
            
        st.session_state.final_srt = build_srt(translated_final)
        st.session_state.is_translating = False
        st.success("✅ وەرگێڕان بەتەواوی کۆتایی هات! بڕۆ بۆ تابی سێیەم (٣. پێشبینین و داگرتن).")

# بینینی کۆتایی و داگرتن
with tab3:
    if st.session_state.final_srt:
        st.balloons()
        st.success("بەرهەمەکە ئامادەیە بۆ بینین و داگرتن!")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 👁️ پێشبینینی کوردی (Preview)")
            st.markdown(f"<div class='kurdish-preview' style='height: 400px; overflow-y: auto;'>{st.session_state.final_srt.replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("### 📝 کۆدی SRT")
            st.text_area("", st.session_state.final_srt, height=400)
        
        st.download_button(
            label="📥 داگرتنی فایلی کۆتایی (.srt)", 
            data=st.session_state.final_srt, 
            file_name="Hollywood_Translated.srt",
            use_container_width=True
        )
    else:
        st.info("هێشتا هیچ فایلێک وەرنەگێڕدراوە. لە تابی یەکەمەوە دەست پێ بکە.")
