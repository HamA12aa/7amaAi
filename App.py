import streamlit as st
import google.generativeai as genai
import time
import re
import random
import tempfile
import os

# ==========================================
# 1. UI SETUP & BEAUTIFUL CSS
# ==========================================
st.set_page_config(page_title="AI Movie Director PRO | V10.1 Masterpiece", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;800&display=swap');
    html, body, [data-testid="stSidebar"], .stMarkdown { font-family: 'Vazirmatn', sans-serif; }
    .main-title { text-align: center; font-weight: 800; color: #ff4b4b; margin-bottom: 5px; }
    .sub-title { text-align: center; color: #808080; margin-bottom: 30px; font-size: 1.1rem; }
    .agent-box { background: #0e1117; color: #00ffcc; padding: 15px; border-radius: 10px; font-family: monospace; direction: ltr; margin-bottom: 10px; border-left: 5px solid #00ffcc; }
    .thought-box { background: #1a1a24; color: #d4d4d8; padding: 10px; border-radius: 8px; font-size: 0.9em; margin-bottom: 10px; border-left: 3px solid #ff4b4b; direction: ltr;}
    .stTextArea textarea { direction: ltr !important; font-family: monospace; background-color: #0e1117; color: #00ffcc;}
    .kurdish-preview { direction: rtl; text-align: right; background-color: #1e1e1e; padding: 15px; border-radius: 10px; border-right: 5px solid #ff4b4b; color: #ffffff;}
    div[data-baseweb="tab-list"] { justify-content: center; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; background-color: #ff4b4b; color: white; font-weight: bold; border: none;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SRT PARSER
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
# 3. AGENT 1: STORY & CONTEXT ANALYZER (Fixed limits)
# ==========================================
def analyze_master_context(active_keys, model_name, srt_text, glossary, video_file=None):
    prompt = f"""You are Agent 1 (The Analyst). Read this Anime subtitle file.
Your job is to generate a 'Master Context Bible' for the translation team.
Include:
1. Story Summary (What is happening in this scene/episode?)
2. Character Analysis (Who is speaking, what are their emotions and tones?)
3. Translation Notes (Important context, idioms, or Japanese cultural notes).
Glossary: {glossary}

Subtitles:
{srt_text[:10000]} 
"""
    
    attempts = 0
    max_attempts = len(active_keys) * 2

    # سیستەمی گۆڕینی کلیلەکان بۆ بریکاری ١ زیاد کرا
    while attempts < max_attempts:
        current_key = random.choice(active_keys)
        genai.configure(api_key=current_key)
        model = genai.GenerativeModel(model_name)
        contents = [prompt]
        
        try:
            if video_file is not None:
                with st.spinner(f"⏳ بریکاری ١ خەریکی ڤیدیۆکەیە (بە بەکارهێنانی کلیل: ***{current_key[-4:]})..."):
                    video_file.seek(0) # گەڕاندنەوەی ڤیدیۆکە بۆ سەرەتا لە ئەگەری دووبارەبوونەوە
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                        tmp.write(video_file.read())
                        v_path = tmp.name
                    
                    g_file = genai.upload_file(path=v_path)
                    while g_file.state.name == "PROCESSING":
                        time.sleep(2)
                        g_file = genai.get_file(g_file.name)
                    contents.insert(0, g_file)
                    
            with st.spinner(f"🕵️ بریکاری ١: شیکردنەوەی چیرۆک (کلیل: ***{current_key[-4:]})..."):
                response = model.generate_content(contents)
                return response.text
                
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "ResourceExhausted" in err_str:
                time.sleep(2) # کلیلەکە لیمیت بووە، دەچێتە سەر یەکێکی تر
            else:
                time.sleep(1)
        attempts += 1
        
    return "⚠️ بریکاری ١ نەیتوانی چیرۆکەکە بخوێنێتەوە بەهۆی لیمیتی کلیلەکان. بەڵام وەرگێڕانەکە بەردەوام دەبێت..."

# ==========================================
# 4. MULTI-AGENT TRANSLATION PROCESS (Agents 2, 3, 4)
# ==========================================
def translate_chunk_with_agents(chunk, active_keys, master_context, visual_container, selected_model):
    xml_input = ""
    for item in chunk:
        clean_text = item['text'].replace('<', '').replace('>', '')
        xml_input += f'<sub id="{item["id"]}">{clean_text}</sub>\n'

    prompt = f"""You are an elite team of Anime Translators translating English to Central Kurdish (Sorani).
Master Context & Story Bible (From Agent 1):
{master_context}

CRITICAL RULES FOR ALL AGENTS:
1. NEVER SHORTEN OR SUMMARIZE THE SENTENCES. Translate every single detail and nuance.
2. The length of the Kurdish translation must reflect the length and exact meaning of the original text.
3. Match the intense emotions, Japanese anime vibes, and character personalities.

Input XML Chunk:
{xml_input}

EXECUTE THE FOLLOWING PROCESS:
Step 1: [Agent 2 - Suggester] Analyze the precise meaning of the lines based on the Context.
Step 2: [Agent 3 - Translator] Draft the full Kurdish translation. DO NOT SHORTEN IT.
Step 3: [Agent 4 - Director] Final review for perfect flow, tone, and formatting.

You MUST format your exact output like this:
<agent2_thoughts> (Analysis goes here) </agent2_thoughts>
<agent3_draft> (Draft goes here) </agent3_draft>
<agent4_final>
<sub id="X">final kurdish text</sub>
</agent4_final>
"""

    attempts = 0
    max_attempts = len(active_keys) * 3

    while attempts < max_attempts:
        current_key = random.choice(active_keys)
        try:
            visual_container.markdown(f"<div class='agent-box'>⚙️ Connecting to <b>{selected_model}</b> (Key ***{current_key[-4:]})</div>", unsafe_allow_html=True)
            
            genai.configure(api_key=current_key)
            model = genai.GenerativeModel(selected_model, generation_config={"temperature": 0.3})
            
            response = model.generate_content(prompt)
            response_text = response.text
            
            a2_thoughts = re.search(r'<agent2_thoughts>(.*?)</agent2_thoughts>', response_text, re.DOTALL)
            a3_draft = re.search(r'<agent3_draft>(.*?)</agent3_draft>', response_text, re.DOTALL)
            
            if a2_thoughts and a3_draft:
                visual_container.markdown(f"<div class='thought-box'><b>🕵️ Agent 2 (Suggester):</b> {a2_thoughts.group(1)[:150]}...<br><b>✍️ Agent 3 (Translator):</b> Draft generated safely without shortening.</div>", unsafe_allow_html=True)

            matches = re.findall(r'<sub id="(\d+)"\s*>(.*?)</sub>', response_text, re.DOTALL | re.IGNORECASE)
            
            if matches:
                result_map = {m[0].strip(): m[1].strip() for m in matches}
                visual_container.markdown(f"<div class='agent-box'>🎬 [Agent 4 - Director]: Final review approved! Text injected.</div>", unsafe_allow_html=True)
                return result_map
            else:
                visual_container.warning("⚠️ مۆدێلەکە فۆرماتەکەی تێکدا، دووبارە هەوڵدەدەینەوە...")
                time.sleep(1)
                
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "ResourceExhausted" in err_str:
                visual_container.error(f"🔴 Limit 429! Switching keys...")
                time.sleep(2)
            else:
                visual_container.error(f"❌ Error: {err_str[:80]}")
                time.sleep(1)
        attempts += 1
        
    return None

# ==========================================
# 5. MAIN UI & AUTO-FETCHING MODELS
# ==========================================
st.markdown("<h1 class='main-title'>🎬 AI Movie Director PRO (V10.1 - Masterpiece)</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>سیستەمی ٤-بریکاری زیرەک بۆ وەرگێڕانی ئەنیمی بەبێ کورتکردنەوەی ڕستەکان!</p>", unsafe_allow_html=True)

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
    st.header("🤖 مۆدێلەکان")
    
    gemini_model_name = None
    if active_keys:
        try:
            genai.configure(api_key=active_keys[0])
            available_models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name.replace('models/', ''))
            
            if available_models:
                gemini_model_name = st.selectbox("مۆدێلێک هەڵبژێرە:", available_models)
                st.success("مۆدێلەکان دۆزرانەوە ✅")
        except Exception:
            st.error("⚠️ کێشە لە کلیلەکەتدا هەیە.")
    else:
        st.info("سەرەتا کلیلەکان دابنێ.")
        
    st.markdown("---")
    glossary = st.text_area("📚 فەرهەنگی ناوەکان", placeholder="Ninja -> نینجا\nHokage -> هۆکای")
    uploaded_video = st.file_uploader("🎥 ڤیدیۆی ئەنیمی (ئارەزوومەندانە بۆ بریکاری ١)", type=['mp4'])

tab1, tab2, tab3 = st.tabs(["📥 ١. دانانی SRT", "⚙️ ٢. پڕۆسەی بریکارەکان", "✅ ٣. بینین و داگرتن"])

with tab1:
    input_srt = st.text_area("کۆدی SRT لێرە دابنێ:", height=300)
    start_btn = st.button("🚀 دەستپێکردنی وەرگێڕانی زیرەک")

if "final_srt" not in st.session_state:
    st.session_state.final_srt = ""
if "is_translating" not in st.session_state:
    st.session_state.is_translating = False
if "master_context" not in st.session_state:
    st.session_state.master_context = ""

if start_btn:
    if not input_srt:
        st.warning("تکایە سەرەتا دەقی SRT دابنێ.")
    elif not active_keys:
        st.error("تکایە لانی کەم یەک کلیلی API دابنێ.")
    elif not gemini_model_name:
        st.error("هیچ مۆدێلێک هەڵنەبژێردراوە.")
    else:
        st.session_state.is_translating = True
        st.session_state.final_srt = ""
        st.session_state.master_context = ""

if getattr(st.session_state, 'is_translating', False):
    with tab2:
        # هەنگاوی یەکەم: دروستکردنی فایلی تێبینییەکان لەلایەن بریکاری ١ (گۆڕدرا بۆ ئەوەی هەموو کلیلەکان بەکاربێنێت)
        if not st.session_state.master_context:
            st.session_state.master_context = analyze_master_context(active_keys, gemini_model_name, input_srt, glossary, uploaded_video)
            st.success("✅ بریکاری ١ کۆتایی بە شیکردنەوەی چیرۆکەکە هێنا!")
            with st.expander("👁️ بینینی تێبینییەکانی بریکاری ١ (Master Context)"):
                st.write(st.session_state.master_context)

        st.info(f"پڕۆسەی وەرگێڕان بە هەماهەنگی بریکارەکانی (٢، ٣، ٤) دەستی پێکرد...")
        
        parsed_data = parse_srt(input_srt)
        total_blocks = len(parsed_data)
        chunk_size = 8 
        
        translated_final = []
        progress_bar = st.progress(0)
        
        agent_status_box = st.empty()
        live_preview_box = st.empty()
        
        for i in range(0, total_blocks, chunk_size):
            chunk = parsed_data[i : i + chunk_size]
            
            with agent_status_box.container():
                st.markdown(f"**پارچەی {i+1} بۆ {min(i+chunk_size, total_blocks)}**")
                
                result_map = translate_chunk_with_agents(chunk, active_keys, st.session_state.master_context, st.empty(), gemini_model_name)
                
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
        
        st.download_button("📥 داگرتنی فایلی کۆتایی (.srt)", data=st.session_state.final_srt, file_name="Translated_Anime.srt")
    else:
        st.info("هێشتا وەرگێڕان نەکراوە.")
