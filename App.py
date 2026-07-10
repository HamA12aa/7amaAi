import streamlit as st
import google.generativeai as genai
from groq import Groq
import tempfile
import time
import os
from concurrent.futures import ThreadPoolExecutor
from moviepy.editor import VideoFileClip

# ==========================================
# 1. STUDIO UI & CSS (Ultra Rich Design)
# ==========================================
st.set_page_config(page_title="AI Director Studio | Ultra V4", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;800&display=swap');
    html, body, [data-testid="stSidebar"], .stMarkdown { font-family: 'Vazirmatn', sans-serif; direction: rtl; }
    
    .main-title { text-align: center; font-weight: 900; background: -webkit-linear-gradient(45deg, #ff0055, #00f2fe); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px; font-size: 3.5rem;}
    .sub-title { text-align: center; color: #a0a0a0; margin-bottom: 30px; font-size: 1.2rem; }
    
    .agent-header { padding: 15px; border-radius: 10px; color: white; text-align: center; font-size: 1.4rem; font-weight: bold; margin-bottom: 15px;}
    .bg-story { background: linear-gradient(90deg, #1e3c72, #2a5298); box-shadow: 0 4px 15px rgba(42, 82, 152, 0.5);}
    .bg-visual { background: linear-gradient(90deg, #870000, #190a05); box-shadow: 0 4px 15px rgba(135, 0, 0, 0.5);}
    
    .result-box { background: #0d0d0d; padding: 25px; border-radius: 12px; border: 1px solid #333; color: #ddd; direction: rtl; text-align: right; overflow-y: auto; font-size: 1.1em; line-height: 1.9;}
    
    .stTextArea textarea { direction: ltr !important; font-family: 'Courier New', monospace; background-color: #050505; color: #00ffcc; border: 1px solid #444; border-radius: 8px;}
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%); color: #000; font-size: 1.1em; font-weight: bold; border: none; transition: 0.3s;}
    .stButton>button:hover { transform: scale(1.02); }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. AUDIO EXTRACTION & GROQ (Whisper)
# ==========================================
def extract_and_transcribe_audio(video_path, groq_key):
    try:
        # جیاکردنەوەی دەنگ لە ڤیدیۆ
        clip = VideoFileClip(video_path)
        audio_path = video_path.replace(".mp4", ".mp3")
        clip.audio.write_audiofile(audio_path, logger=None)
        clip.close()

        # ناردن بۆ Groq بۆ گوێگرتن
        client = Groq(api_key=groq_key)
        with open(audio_path, "rb") as file:
            translation = client.audio.translations.create(
                file=(audio_path, file.read()),
                model="whisper-large-v3",
                response_format="text"
            )
        
        os.remove(audio_path)
        return translation # ئەمە دەقە ئینگلیزییەکەیە کە ڕاستەوخۆ لە دەنگە ژاپۆنییەکەوە وەرگیراوە
    except Exception as e:
        return f"Audio extraction failed: {str(e)}"

# ==========================================
# 3. VIDEO OPTIMIZER (Compressor & Splitter)
# ==========================================
def process_video(video_path):
    clip = VideoFileClip(video_path)
    duration = clip.duration
    
    # بچووککردنەوەی کواڵێتی بۆ 480p بۆ خێرایی
    clip_resized = clip.resize(height=480)
    
    part1_path = video_path.replace(".mp4", "_part1.mp4")
    part2_path = video_path.replace(".mp4", "_part2.mp4")
    
    # دابەشکردن (١٢ خولەکی یەکەم و ئەوەی ماوە)
    split_time = min(12 * 60, duration)
    
    clip_resized.subclip(0, split_time).write_videofile(part1_path, codec="libx264", audio_codec="aac", bitrate="500k", logger=None)
    
    if duration > split_time:
        clip_resized.subclip(split_time, duration).write_videofile(part2_path, codec="libx264", audio_codec="aac", bitrate="500k", logger=None)
    
    clip.close()
    clip_resized.close()
    
    return part1_path, part2_path if duration > split_time else None

# ==========================================
# 4. AGENT 1: MASTER LORE ARCHITECT (Text)
# ==========================================
def run_agent1(keys, srt_text):
    prompt = f"""You are the Master Lore Architect.
Analyze this SRT. DO NOT TRANSLATE IT. Output in Kurdish Sorani.
CRITICAL RULE: DO NOT analyze or translate opening/ending theme songs or lyrics!

1. 📖 کڕۆکی چیرۆک
2. 🎭 شیکاری کەسایەتییەکان
3. 🔍 هێما شاراوەکان
4. 📜 ڕێنمایی بۆ وەرگێڕ

SRT Text: {srt_text[:40000]}"""
    
    for key in keys:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-1.5-pro")
            return model.generate_content(prompt).text
        except: continue
    return "❌ کێشە لە بریکاری یەکەم."

# ==========================================
# 5. AGENT 2: VISUAL & AUDIO DETECTIVE
# ==========================================
def inspect_video_part(video_file_path, srt_text, audio_transcript, keys):
    for key in keys:
        try:
            genai.configure(api_key=key)
            uploaded_file = genai.upload_file(path=video_file_path)
            
            while uploaded_file.state.name == "PROCESSING":
                time.sleep(2)
                uploaded_file = genai.get_file(uploaded_file.name)
                
            prompt = f"""You are the Ultimate Video Inspector. 
CRITICAL RULE: IGNORE ALL SONGS/LYRICS. Focus on dialogue.

I will give you the English SRT and the actual AUDIO transcript (translated to English by Whisper).
Watch the video, compare the SRT with the audio transcript and visual context.

If the English SRT localized poorly or missed the original meaning, report it in exactly this format in Kurdish Sorani:

---
⚠️ **هەڵە لە دێڕی ژمارە [Number]**
*   **ئینگلیزییەکە (SRT):** "[What the SRT says]"
*   **دەنگی ئەسڵی/ژاپۆنییەکە (Audio):** "[What the audio actually means]"
*   **ڕاستییەکە بەپێی دیمەن:** "[The correct translation based on video+audio]"
*   **هۆکار:** "[Why the SRT is wrong]"
---

SRT Text: {srt_text[:20000]}
Actual Audio Transcript from Groq: {audio_transcript}
"""
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content([prompt, uploaded_file])
            genai.delete_file(uploaded_file.name)
            return response.text
        except Exception as e:
            return f"Error: {e}"
    return "Key error."

def run_agent2(keys, video_path, srt_text, audio_transcript):
    part1, part2 = process_video(video_path)
    
    res1 = f"### 🎬 بەشی یەکەم (٠ تا ١٢ خولەک)\n\n" + inspect_video_part(part1, srt_text, audio_transcript, keys)
    res2 = ""
    if part2:
        res2 = f"\n\n### 🎬 بەشی دووەم (١٢ خولەک تا کۆتایی)\n\n" + inspect_video_part(part2, srt_text, audio_transcript, keys)
        os.remove(part2)
        
    os.remove(part1)
    return res1 + res2

# ==========================================
# 6. MAIN APP LOGIC
# ==========================================
st.markdown("<h1 class='main-title'>AI Director Studio 🎬 Ultra V4</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>سیستەمی پێشکەوتوو: شیکاری دەق + بەراوردکردنی دەنگ بە ڤیدیۆ + کارکردنی هاوکات</p>", unsafe_allow_html=True)

with st.sidebar:
    st.header("🔑 کلیلەکان و ڕێکخستن")
    gemini_keys = [st.text_input(f"Gemini Key {i+1}", type="password") for i in range(2)]
    active_g_keys = [k for k in gemini_keys if k]
    
    st.markdown("---")
    groq_key = st.text_input("Groq API Key (بۆ بیستنی دەنگ):", type="password")
    
    st.markdown("---")
    st.success("✔️ سیستەمی بچووککردنەوەی ڤیدیۆ چالاکە")
    st.success("✔️ پشتگوێخستنی گۆرانییەکان چالاکە")
    st.success("✔️ دابەشکردنی ١٢ خولەکی چالاکە")

col1, col2 = st.columns(2)
with col1: srt_input = st.text_area("📄 دەقی ئینگلیزی (SRT) دابنێ:", height=200)
with col2: video_input = st.file_uploader("🎥 ڤیدیۆکە دابنێ:", type=["mp4", "mkv"])

if st.button("🚀 دەستپێکردنی ستۆدیۆ (کارکردنی هاوکات)"):
    if not active_g_keys or not groq_key or not srt_input or not video_input:
        st.error("تکایە هەموو کلیلەکان و فایلەکان دابنێ!")
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            tmp.write(video_input.read())
            tmp_video_path = tmp.name

        st.info("⏳ سیستەمەکە دەستی پێکرد... تکایە چاوەڕێبە (ڤیدیۆکە بچووک دەکرێتەوە و دەنگەکەی جیا دەکرێتەوە)")

        # دەرهێنانی دەنگ سەرەتا بۆ ئەوەی بیدەین بە بریکاری دووەم
        with st.spinner("🎧 دەرهێنانی دەنگ و ناردنی بۆ Groq Whisper..."):
            audio_text = extract_and_transcribe_audio(tmp_video_path, groq_key)

        st.success("✅ دەنگەکە وەرگێڕدرا! ئێستا بریکارەکان پێکەوە کار دەکەن...")

        # کارپێکردنی هاوکات (Parallel Execution)
        with ThreadPoolExecutor() as executor:
            future_agent1 = executor.submit(run_agent1, active_g_keys, srt_input)
            future_agent2 = executor.submit(run_agent2, active_g_keys, tmp_video_path, srt_input, audio_text)

            with st.spinner("⚙️ بریکارەکان خەریکی شیکاری و بینینی ڤیدیۆکەن لە یەک کاتدا..."):
                result_agent1 = future_agent1.result()
                result_agent2 = future_agent2.result()

        os.remove(tmp_video_path)

        # پیشاندانی ئەنجامەکان بە دوو بەشی جیا و دوگمەی سەیڤ
        st.markdown("---")
        
        tab1, tab2 = st.tabs(["🕵️ بریکاری یەکەم (شیکاری چیرۆک)", "🎥 بریکاری دووەم (ڕاستکردنەوەی ڤیدیۆ)"])
        
        with tab1:
            st.markdown("<div class='agent-header bg-story'>🕵️ بریکاری یەکەم: شیکاری قووڵی چیرۆک</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='result-box'>{result_agent1}</div>", unsafe_allow_html=True)
            st.download_button("📥 داگرتنی شیکاری چیرۆک (TXT)", result_agent1, "Agent1_Story.txt", key="dl_a1")

        with tab2:
            st.markdown("<div class='agent-header bg-visual'>🎥 بریکاری دووەم: لێکۆڵەری ڤیدیۆ و دەنگ</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='result-box'>{result_agent2}</div>", unsafe_allow_html=True)
            st.download_button("📥 داگرتنی هەڵەکانی ڤیدیۆ (TXT)", result_agent2, "Agent2_Errors.txt", key="dl_a2")

        # پیشاندانی دەقەکەی Groq بۆ دڵنیایی
        with st.expander("🎧 بینینی ئەو دەقەی Groq لە دەنگەکەوە دەریهێناوە (بۆ زانیاری خۆت)"):
            st.text_area("", audio_text, height=200)
