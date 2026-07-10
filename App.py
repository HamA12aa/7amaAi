import streamlit as st
import google.generativeai as genai
from groq import Groq
import tempfile
import time
import os

# ==========================================
# 1. UI & CSS (جێگیر و خێرا)
# ==========================================
st.set_page_config(page_title="AI Director Studio | Stable V5", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;800&display=swap');
    html, body, [data-testid="stSidebar"], .stMarkdown { font-family: 'Vazirmatn', sans-serif; direction: rtl; }
    
    .main-title { text-align: center; font-weight: 800; background: -webkit-linear-gradient(45deg, #ff0055, #ffaa00); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px; font-size: 3rem;}
    .sub-title { text-align: center; color: #a0a0a0; margin-bottom: 30px; font-size: 1.2rem; }
    
    .agent-header { padding: 15px; border-radius: 10px; color: white; text-align: center; font-size: 1.3rem; font-weight: bold; margin-bottom: 15px;}
    .bg-story { background: linear-gradient(90deg, #1e3c72, #2a5298); }
    .bg-visual { background: linear-gradient(90deg, #870000, #190a05); }
    
    .result-box { background: #111; padding: 25px; border-radius: 12px; border: 1px solid #333; color: #ddd; direction: rtl; text-align: right; overflow-y: auto; font-size: 1.1em; line-height: 1.8;}
    
    .stTextArea textarea { direction: ltr !important; font-family: 'Courier New', monospace; background-color: #0a0a0a; color: #00ffcc; border: 1px solid #333;}
    .stButton>button { width: 100%; border-radius: 10px; height: 3.8em; background: linear-gradient(90deg, #ff0055 0%, #ffaa00 100%); color: white; font-size: 1.1em; font-weight: bold; border: none; transition: 0.3s;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. فەنکشنی دەرهێنانی دەنگ (Groq Whisper)
# ==========================================
def extract_and_transcribe(video_path, groq_key):
    try:
        from moviepy.editor import VideoFileClip
        clip = VideoFileClip(video_path)
        audio_path = video_path.replace(".mp4", ".mp3")
        clip.audio.write_audiofile(audio_path, logger=None)
        clip.close()

        client = Groq(api_key=groq_key)
        with open(audio_path, "rb") as file:
            trans = client.audio.translations.create(
                file=(audio_path, file.read()),
                model="whisper-large-v3",
                response_format="text"
            )
        
        if os.path.exists(audio_path):
            os.remove(audio_path)
        return trans.text
    except Exception as e:
        return f"کێشە لە دەرهێنانی دەنگ: {str(e)}"

# ==========================================
# 3. بریکاری یەکەم: شیکاری دەق (Agent 1)
# ==========================================
def run_agent1(keys, model_name, srt_text):
    prompt = f"""You are 'Agent 1: The Master Lore Architect'.
Your task is to analyze this SRT file in **Kurdish (Sorani)**.
DO NOT TRANSLATE IT. IGNORE ALL SONGS AND LYRICS completely.

Provide:
1. 📖 **کڕۆکی چیرۆک:** (What is truly happening)
2. 🎭 **شیکاری دەروونی کەسایەتییەکان:** (Their hidden motivations)
3. 🔍 **هێما و شاراوەکان:** (Cultural context)
4. 📜 **دەستووری وەرگێڕان:** (Rules for the translator)

SRT Text:
{srt_text[:40000]}"""
    
    for key in keys:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(model_name)
            return model.generate_content(prompt).text
        except Exception as e: 
            continue
    return "❌ کێشە لە بریکاری یەکەم ڕوویدا. دڵنیابە لە کلیلەکان و مۆدێلەکە."

# ==========================================
# 4. بریکاری دووەم: لێکۆڵەری ڤیدیۆ (Agent 2)
# ==========================================
def run_agent2(keys, model_name, video_path, srt_text, audio_transcript):
    for key in keys:
        try:
            genai.configure(api_key=key)
            uploaded_file = genai.upload_file(path=video_path)
            
            while uploaded_file.state.name == "PROCESSING":
                time.sleep(3)
                uploaded_file = genai.get_file(uploaded_file.name)
            
            prompt = f"""You are 'Agent 2: The Visual & Context Inspector'.
CRITICAL RULE: IGNORE ALL SONGS/LYRICS. Focus on dialogue.

Watch the video, compare the English SRT with the actual AUDIO transcript.
Find lines where the English text is wrong, localized poorly, or doesn't match the character's action.

Format your output in **Kurdish Sorani** exactly like this:
---
⚠️ **هەڵە لە دێڕی ژمارە [ژمارە]**
*   **ئینگلیزییەکە (SRT):** "[English Text]"
*   **دەنگی ئەسڵی (Audio):** "[What the audio actually means]"
*   **ڕاستییەکە بەپێی دیمەن:** "[Correct Kurdish meaning]"
*   **هۆکار:** "[Why it is wrong]"
---

SRT Text: {srt_text[:20000]}
Actual Audio Transcript from Groq: {audio_transcript}
"""
            model = genai.GenerativeModel(model_name)
            response = model.generate_content([prompt, uploaded_file])
            genai.delete_file(uploaded_file.name)
            return response.text
        except Exception as e:
            return f"❌ کێشە لە بریکاری دووەم: {str(e)}"
    return "❌ کێشەی کلیل لە بریکاری دووەم."

# ==========================================
# 5. ڕووکاری سەرەکی (Main UI)
# ==========================================
st.markdown("<h1 class='main-title'>AI Director Studio 🎥 V5</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>سیستەمی جێگیر و بێ کێشە بۆ شیکاری و دۆزینەوەی هەڵەکان</p>", unsafe_allow_html=True)

with st.sidebar:
    st.header("🔑 کلیلەکان")
    gemini_keys = [st.text_input(f"Gemini Key {i+1}", type="password") for i in range(2)]
    active_g_keys = [k.strip() for k in gemini_keys if k.strip()]
    
    st.markdown("---")
    groq_key = st.text_input("Groq API Key (بۆ دەنگ):", type="password").strip()
    
    st.markdown("---")
    st.header("⚙️ هەڵبژاردنی مۆدێلەکان")
    available_models = []
    
    # هێنانەخوارەوەی ناوە دروستەکان بەپێی کلیلەکەت بۆ ڕێگری لە ئێرۆری 404
    if active_g_keys:
        try:
            genai.configure(api_key=active_g_keys[0])
            available_models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        except:
            st.error("کێشە لە کلیلەکانی Gemini هەیە، ناتوانرێت مۆدێلەکان بخوێنرێتەوە.")
    
    if available_models:
        agent1_model = st.selectbox("بریکاری ١ (شیکاری دەق - هەوڵدە Pro بێت):", available_models, index=0)
        agent2_model = st.selectbox("بریکاری ٢ (سەیرکردنی ڤیدیۆ - هەوڵدە Flash بێت):", available_models, index=len(available_models)-1 if len(available_models)>1 else 0)
    else:
        agent1_model, agent2_model = None, None
        st.warning("تکایە کلیلی Gemini دابنێ بۆ بینینی مۆدێلەکان.")

col1, col2 = st.columns(2)
with col1:
    input_srt = st.text_area("📄 دەقی ئینگلیزی (SRT) لێرە دابنێ:", height=200)
with col2:
    uploaded_video = st.file_uploader("🎬 ڤیدیۆکە لێرە دابنێ (MP4):", type=["mp4", "mkv"])

if st.button("🚀 دەستپێکردنی ستۆدیۆ (بە هەنگاو)"):
    if not active_g_keys or not groq_key or not input_srt or not uploaded_video:
        st.warning("تکایە هەموو کلیلەکان و فایلەکان بە دروستی داخڵ بکە.")
    elif not agent1_model or not agent2_model:
        st.error("تکایە دڵنیابە کە مۆدێلەکانت هەڵبژاردووە لە لای ڕاست.")
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            tmp_file.write(uploaded_video.read())
            tmp_video_path = tmp_file.name

        status_box = st.empty()
        
        # هەنگاوی ١: دەرهێنانی دەنگ
        status_box.info("🎧 هەنگاوی ١: خەریکی جیاکردنەوەی دەنگ و ناردنی بۆ Groq...")
        audio_text = extract_and_transcribe(tmp_video_path, groq_key)
        
        # هەنگاوی ٢: بریکاری یەکەم
        status_box.info(f"🕵️ هەنگاوی ٢: بریکاری یەکەم خەریکی دروستکردنی چیرۆکەکەیە بە مۆدێلی {agent1_model}...")
        agent1_result = run_agent1(active_g_keys, agent1_model, input_srt)
        
        # هەنگاوی ٣: بریکاری دووەم
        status_box.info(f"🎥 هەنگاوی ٣: بریکاری دووەم ڤیدیۆکە دەبینێت بە مۆدێلی {agent2_model}... (چاوەڕێبە)")
        agent2_result = run_agent2(active_g_keys, agent2_model, tmp_video_path, input_srt, audio_text)
        
        status_box.empty()
        if os.path.exists(tmp_video_path):
            os.remove(tmp_video_path)
            
        st.success("✅ هەموو کارەکان بە سەرکەوتوویی تەواو بوون!")
        
        # نیشاندانی ئەنجامەکان لە دوو تابی جیا
        tab1, tab2, tab3 = st.tabs(["🕵️ شیکاری چیرۆک (Agent 1)", "🎥 هەڵەی ڤیدیۆ (Agent 2)", "🎧 دەقی گوێلێگیراو (Groq)"])
        
        with tab1:
            st.markdown("<div class='agent-header bg-story'>شیکاری قووڵی چیرۆک</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='result-box'>{agent1_result}</div>", unsafe_allow_html=True)
            st.download_button("📥 سەیڤکردنی شیکاری", agent1_result, "Agent1_Story.txt")
            
        with tab2:
            st.markdown("<div class='agent-header bg-visual'>لێکۆڵینەوەی ڤیدیۆ و هەڵەکان</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='result-box'>{agent2_result}</div>", unsafe_allow_html=True)
            st.download_button("📥 سەیڤکردنی هەڵەکان", agent2_result, "Agent2_Errors.txt")
            
        with tab3:
            st.markdown("ئەمە ئەو دەقەیە کە زیرەکی دەستکردی Groq لە ناو دەنگی ڤیدیۆکەوە دەریهێناوە:")
            st.text_area("", audio_text, height=300)
