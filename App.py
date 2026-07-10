import streamlit as st
import google.generativeai as genai
import tempfile
import time
import os

# ==========================================
# 1. PRO STUDIO UI & CSS (Dual Agent Studio)
# ==========================================
st.set_page_config(page_title="AI Director Studio | V2", layout="wide", page_icon="🎥")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;800&display=swap');
    html, body, [data-testid="stSidebar"], .stMarkdown { font-family: 'Vazirmatn', sans-serif; direction: rtl; }
    
    .main-title { text-align: center; font-weight: 800; background: -webkit-linear-gradient(45deg, #ff0055, #ffaa00); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px; font-size: 3rem;}
    .sub-title { text-align: center; color: #a0a0a0; margin-bottom: 30px; font-size: 1.2rem; }
    
    .agent1-box { background: #111; padding: 25px; border-radius: 12px; border-top: 4px solid #0099ff; color: #ddd; direction: rtl; text-align: right; overflow-y: auto; font-size: 1.1em; line-height: 1.8; margin-bottom: 20px;}
    .agent2-box { background: #1a0505; padding: 25px; border-radius: 12px; border-top: 4px solid #ff0055; color: #ddd; direction: rtl; text-align: right; overflow-y: auto; font-size: 1.1em; line-height: 1.8;}
    
    .status-text { color: #00ffcc; font-weight: bold; }
    .stTextArea textarea { direction: ltr !important; font-family: 'Courier New', monospace; background-color: #0a0a0a; color: #00ffcc; border: 1px solid #333;}
    .stButton>button { width: 100%; border-radius: 10px; height: 3.8em; background: linear-gradient(90deg, #ff0055 0%, #ffaa00 100%); color: white; font-size: 1.1em; font-weight: bold; border: none; transition: 0.3s;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. AGENT 1: STORY ARCHITECT (دەق تەنها)
# ==========================================
def run_agent1_story(active_keys, model_name, srt_text):
    prompt = f"""You are 'Agent 1: The Master Lore Architect & Cinematic Analyst'.
Your task is to read the provided English SRT file and produce a 100% accurate, flawless story analysis in **Kurdish (Sorani)**.
DO NOT TRANSLATE THE SRT. Your job is to extract the deepest meaning behind the words.

Provide your output beautifully formatted with these specific sections:
1. 📖 **کڕۆکی چیرۆکەکە (The Deep Core):** A 100% accurate explanation of what is truly happening in this scene/episode. Do not just summarize; explain the *why*.
2. 🎭 **شیکاری دەروونی کەسایەتییەکان (Psychological Character Profile):** Who is speaking? What are their hidden motivations, power dynamics, and exact tone?
3. 🔍 **هێما و شاراوەکان (Hidden Meanings & Lore):** Are there any idioms, sarcastic remarks, or cultural context that a normal translator would miss?
4. 📜 **دەستووری وەرگێڕان (The Translation Bible):** Absolute rules for the translator (e.g., "Make Character A sound arrogant, Make Character B sound scared").

Here is the SRT Text:
{srt_text[:50000]}
"""
    for key in active_keys:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(model_name)
            return model.generate_content(prompt).text
        except Exception: continue
    return "❌ کێشە لە بریکاری یەکەم ڕوویدا."

# ==========================================
# 3. AGENT 2: VISUAL DETECTIVE (دەق + ڤیدیۆ)
# ==========================================
def run_agent2_video_inspector(active_keys, model_name, srt_text, video_path):
    # هەنگاوی یەکەم: بەرزکردنەوەی ڤیدیۆکە بۆ سێرڤەری گووگڵ
    for key in active_keys:
        try:
            genai.configure(api_key=key)
            uploaded_file = genai.upload_file(path=video_path)
            
            # چاوەڕێکردن تا ڤیدیۆکە پرۆسێس دەبێت (زۆر گرنگە)
            while uploaded_file.state.name == "PROCESSING":
                time.sleep(3)
                uploaded_file = genai.get_file(uploaded_file.name)
            
            if uploaded_file.state.name == "FAILED":
                return "❌ گووگڵ نەیتوانی ڤیدیۆکە بخوێنێتەوە."

            # هەنگاوی دووەم: پرۆمپتی لێکۆڵەری ڤیدیۆ
            prompt = f"""You are 'Agent 2: The Visual & Context Inspector'. You are an expert anime/movie director.
English localizers often change the original meaning of dialogues. Your job is to watch the provided VIDEO and read the provided SRT TEXT simultaneously.
Find every single line where the English translation feels wrong, localized poorly, or does not match the character's facial expression, action, or the true visual context.

Output your findings in **Kurdish (Sorani)** exactly in this format for every error you find:

---
⚠️ **هەڵە لە دێڕی ژمارە [ژمارەی دێڕەکە] (Time: [کاتەکە])**
*   **دەقە ئینگلیزییەکە دەڵێت:** "[The current English text]"
*   **ڕاستییەکە بەپێی دیمەنەکە:** "[What it should actually mean based on the visual context]"
*   **هۆکار (بۆچی ئینگلیزییەکە هەڵەیە؟):** "[Detailed explanation of why the English text doesn't match the character's emotion/action in the video]"
---

Be extremely strict. If the English text is 100% perfect for a scene, say "هیچ هەڵەیەکی گەورە نەدۆزرایەوە".

Here is the SRT Text:
{srt_text[:50000]}
"""
            model = genai.GenerativeModel(model_name)
            response = model.generate_content([prompt, uploaded_file])
            
            # سڕینەوەی ڤیدیۆکە لە سێرڤەر بۆ پاراستنی جێگا
            genai.delete_file(uploaded_file.name)
            
            return response.text
        except Exception as e: 
            return f"❌ هەڵە لە بریکاری دووەم: {str(e)}"
    return "❌ کێشە لە کلیلەکان هەیە."

# ==========================================
# 4. MAIN UI & LOGIC
# ==========================================
st.markdown("<h1 class='main-title'>AI Director Studio 🎥 V2</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>سیستەمی دوو بریکار (شیکاری دەق + ڕاستکردنەوەی هەڵەی ئینگلیزی لەڕێگەی بینینی ڤیدیۆ)</p>", unsafe_allow_html=True)

with st.sidebar:
    st.header("🔑 کلیلەکان")
    active_keys = [k.strip() for k in [st.text_input(f"Slot {i+1}", type="password") for i in range(2)] if k.strip()]
    
    st.markdown("---")
    gemini_model_name = None
    if active_keys:
        try:
            genai.configure(api_key=active_keys[0])
            # تەنها ئەو مۆدێلانە دەهێنێت کە پشتیوانی بینین دەكەن
            available_models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            gemini_model_name = st.selectbox("مۆدێل (دەبێت Pro یان Flash بێت):", available_models)
        except: st.error("کێشە لە کلیلەکان.")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📝 ١. فایلی ژێرنووس (SRT)")
    input_srt = st.text_area("دەقی ئینگلیزی لێرە دابنێ:", height=250)

with col2:
    st.markdown("### 🎬 ٢. دیمەنی ڤیدیۆ (Clip)")
    uploaded_video = st.file_uploader("ڤیدیۆکە لێرە دابنێ (MP4, MKV):", type=["mp4", "mkv", "mov"])
    if uploaded_video:
        st.video(uploaded_video)

if st.button("🚀 کارپێکردنی هەردوو بریکار (شیکاری + بینینی ڤیدیۆ)"):
    if not active_keys:
        st.error("تکایە کلیلی API دابنێ.")
    elif not input_srt.strip():
        st.error("تکایە دەقی ژێرنووسەکە دابنێ.")
    elif not uploaded_video:
        st.error("تکایە ڤیدیۆکەش دابنێ بۆ ئەوەی بریکاری دووەم بتوانێت لێکۆڵینەوە بکات.")
    else:
        # هەڵگرتنی ڤیدیۆکە لە فایلێکی کاتی بۆ ئەوەی بیدەین بە Gemini
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            tmp_file.write(uploaded_video.read())
            tmp_video_path = tmp_file.name

        status_msg = st.empty()
        
        # --- کارپێکردنی بریکاری یەکەم ---
        status_msg.markdown("<h4 class='status-text'>🕵️ بریکاری یەکەم خەریکی دروستکردنی چیرۆکەکەیە...</h4>", unsafe_allow_html=True)
        agent1_result = run_agent1_story(active_keys, gemini_model_name, input_srt)
        
        # --- کارپێکردنی بریکاری دووەم ---
        status_msg.markdown("<h4 class='status-text'>🎥 بریکاری دووەم خەریکی سەیرکردنی ڤیدیۆکەیە بۆ دۆزینەوەی هەڵەی ئینگلیزی... (کەمێک کاتی دەوێت)</h4>", unsafe_allow_html=True)
        agent2_result = run_agent2_video_inspector(active_keys, gemini_model_name, input_srt, tmp_video_path)
        
        status_msg.empty()
        
        # سڕینەوەی فایلی ڤیدیۆ کاتییەکە لە کۆمپیوتەرەکەت
        os.remove(tmp_video_path)
        
        st.success("✅ هەردوو بریکارەکە کارەکانیان بە سەرکەوتوویی تەواو کرد!")
        
        st.markdown("## 🕵️ بریکاری یەکەم: شیکاری قووڵی چیرۆک (Text Analysis)")
        st.markdown(f"<div class='agent1-box'>{agent1_result}</div>", unsafe_allow_html=True)
        
        st.markdown("## 🎥 بریکاری دووەم: لێکۆڵەری ڤیدیۆ و دیمەن (Visual Error Detection)")
        st.markdown(f"<div class='agent2-box'>{agent2_result}</div>", unsafe_allow_html=True)
