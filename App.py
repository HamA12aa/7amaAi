import streamlit as st
import google.generativeai as genai
import random

# ==========================================
# 1. PRO STUDIO UI & CSS (Story Analyzer)
# ==========================================
st.set_page_config(page_title="AI Story Analyzer PRO | V1", layout="wide", page_icon="🕵️")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;800&display=swap');
    html, body, [data-testid="stSidebar"], .stMarkdown { font-family: 'Vazirmatn', sans-serif; direction: rtl; }
    
    .main-title { text-align: center; font-weight: 800; background: -webkit-linear-gradient(45deg, #00ffcc, #0099ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px; font-size: 3rem;}
    .sub-title { text-align: center; color: #a0a0a0; margin-bottom: 30px; font-size: 1.2rem; }
    
    .status-box { background: rgba(14, 17, 23, 0.8); border: 1px solid #333; padding: 15px; border-radius: 12px; margin-bottom: 10px; border-right: 4px solid #00ffcc; color: #fff;}
    .analysis-box { background: #111; padding: 25px; border-radius: 12px; border-top: 4px solid #0099ff; color: #ddd; direction: rtl; text-align: right; overflow-y: auto; font-size: 1.1em; line-height: 1.8;}
    
    .stTextArea textarea { direction: ltr !important; font-family: 'Courier New', monospace; background-color: #0a0a0a; color: #00ffcc; border: 1px solid #333; border-radius: 8px;}
    .stTextArea textarea:focus { border-color: #00ffcc; box-shadow: 0 0 5px rgba(0, 255, 204, 0.5); }
    
    .stButton>button { width: 100%; border-radius: 10px; height: 3.8em; background: linear-gradient(90deg, #0099ff 0%, #00ffcc 100%); color: #111; font-size: 1.1em; font-weight: bold; border: none; transition: 0.3s;}
    .stButton>button:hover { opacity: 0.8; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. AGENT 1: STORY ANALYZER FUNCTION
# ==========================================
def analyze_master_context(active_keys, model_name, srt_text):
    prompt = f"""You are 'Agent 1: The Expert Story & Cinematic Analyzer'.
Your task is to analyze this subtitle file and output a highly detailed response in **Kurdish (Sorani)**.
DO NOT TRANSLATE the subtitles. Just analyze them and provide the following sections:

1. 🎬 **کورتەی چیرۆک (Story Summary):** What is happening in this text?
2. 👥 **کەسایەتییەکان (Character Profiles):** Who are the characters speaking, and what is their personality, relationship, and tone?
3. 🌌 **کەشوهەوا (Atmosphere & Tone):** Is it dark, funny, action, or romantic?
4. 💡 **تێبینییە کلتوورییەکان (Cultural & Key Notes):** Any important idioms, jokes, or hidden meanings.
5. 📖 **ئامۆژگاری بۆ وەرگێڕ (Translation Bible):** How should a translator approach this text to make it sound cinematic and natural?

Here are the Subtitles (analyze up to the first 40,000 characters):
{srt_text[:40000]}
"""
    
    # بەکارهێنانی کلیلەکان بە شێوازی پرۆفیشناڵ (وەک کۆدی یەکەم) بۆ ئەوەی هەرگیز دانەکوژێت
    for key in active_keys:
        genai.configure(api_key=key)
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            # ئەگەر کلیلێک کێشەی هەبوو، دەچێتە سەر کلیلێکی تر
            continue
            
    return f"❌ هەڵەیەک ڕوویدا. تکایە دڵنیا بەرەوە لە کلیلەکانت و هێڵی ئینتەرنێتەکەت."

# ==========================================
# 3. MAIN UI & LOGIC
# ==========================================
st.markdown("<h1 class='main-title'>AI Story Analyzer PRO 🕵️ V1</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>بریکاری یەکەم - شیکردنەوەی چیرۆک، کەسایەتی، و پێدانی زانیاری سینەمایی</p>", unsafe_allow_html=True)

with st.sidebar:
    st.header("🔑 کلیلەکان (API Keys)")
    # سیستەمی دانانی چەند کلیلێک بۆ ڕێگری لە پچڕان
    active_keys = [k.strip() for k in [st.text_input(f"Slot {i+1}", type="password") for i in range(3)] if k.strip()]
    
    st.markdown("---")
    gemini_model_name = None
    if active_keys:
        try:
            # هێنانەخوارەوەی ئۆتۆماتیکی ناوەکان بۆ ئەوەی کێشەی 404 دروست نەبێت
            genai.configure(api_key=active_keys[0])
            available_models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            gemini_model_name = st.selectbox("مۆدێل هەڵبژێرە:", available_models)
        except:
            st.error("کێشە لە کلیلەکەدا هەیە.")
    else:
        st.warning("تکایە لایەنی کەم یەک کلیل دابنێ بۆ ئەوەی مۆدێلەکان دەربکەون.")

# بەشی دانانی دەق
input_srt = st.text_area("دەقی پێشەکی فیلم یان SRT لێرە دابنێ:", height=300, placeholder="Paste your SRT or text here...")

# دوگمەی کارپێکردن
if st.button("🚀 دەستپێکردنی شیکردنەوەی چیرۆک"):
    if not active_keys:
        st.error("تکایە سەرەتا کلیلی API لە لای چەپ دابنێ.")
    elif not input_srt.strip():
        st.warning("تکایە دەقی SRT دابنێ.")
    elif not gemini_model_name:
        st.error("کێشە هەیە لە هەڵبژاردنی مۆدێلەکە.")
    else:
        status_box = st.empty()
        status_box.markdown(f"<div class='status-box'>🕵️ <b>بریکاری یەکەم:</b> خەریکی شیکردنەوەی چیرۆک و تێگەیشتنە لە دەقەکە... (تکایە چاوەڕێ بە)</div>", unsafe_allow_html=True)
        
        # ناردنی دەقەکە بۆ بزوێنەری شیکردنەوە
        result = analyze_master_context(active_keys, gemini_model_name, input_srt)
        
        status_box.empty()
        st.success("✅ شیکردنەوە بە سەرکەوتوویی تەواو بوو!")
        
        # نیشاندانی ئەنجام بە جوانی
        st.markdown("<h3 style='color: #00ffcc;'>📊 دەرەنجامی شیکردنەوە (Translation Bible):</h3>", unsafe_allow_html=True)
        st.markdown(f"<div class='analysis-box'>{result}</div>", unsafe_allow_html=True)
        
        st.download_button("📥 داگرتنی ئەنجام (TXT)", result, "Story_Analysis_Bible.txt")
