import streamlit as st
import google.generativeai as genai

# ==========================================
# 1. UI & CSS (دیزاینی ستۆدیۆی شیکاری)
# ==========================================
st.set_page_config(page_title="AI Story Analyzer | Agent 1", layout="wide", page_icon="🕵️")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;800&display=swap');
    html, body, [data-testid="stSidebar"], .stMarkdown { font-family: 'Vazirmatn', sans-serif; direction: rtl; }
    .main-title { text-align: center; font-weight: 800; background: -webkit-linear-gradient(45deg, #00ffcc, #0099ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 3rem;}
    .analysis-box { background: #111; padding: 25px; border-radius: 15px; border-right: 5px solid #00ffcc; color: #eee; line-height: 1.8; font-size: 1.1rem; }
    .stTextArea textarea { direction: ltr !important; background-color: #050505; color: #00ffcc; border: 1px solid #222; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. STORY ANALYZER FUNCTION (Agent 1)
# ==========================================
def analyze_story_agent(srt_text, api_key, model_name):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    # پرۆمپی تایبەت بە شیکردنەوەی قووڵ
    prompt = f"""
    You are 'Agent 1: The Story Analyzer'. I will provide you with a subtitle file (SRT).
    Your task is to provide a deep analysis of the content in Kurdish Sorani.
    
    Please include:
    1. **Summary:** What is this movie/episode about?
    2. **Characters:** Who are the main characters and what are their personalities based on the dialogue?
    3. **Tone & Atmosphere:** Is it dark, funny, romantic, or action-packed?
    4. **Key Themes:** What are the main topics discussed?
    5. **Cultural Notes:** Any specific idioms or cultural references found.
    6. **Translation Bible:** Tips for a translator on how to handle the tone of these specific characters.

    Subtitles:
    {srt_text[:15000]} 
    """
    
    try:
        with st.spinner("🕵️ بریکاری یەکەم خەریکی خوێندنەوە و شیکردنەوەیە..."):
            response = model.generate_content(prompt)
            return response.text
    except Exception as e:
        return f"هەڵەیەک ڕوویدا: {str(e)}"

# ==========================================
# 3. MAIN INTERFACE
# ==========================================
st.markdown("<h1 class='main-title'>AI Story Analyzer 🕵️</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888;'>بەشی شیکردنەوەی چیرۆک و زانیاری دەقی فیلم</p>", unsafe_allow_html=True)

with st.sidebar:
    st.header("🔑 ڕێکخستنی کلیل")
    api_key = st.text_input("Gemini API Key:", type="password")
    model_name = st.selectbox("مۆدێل:", ["gemini-1.5-pro", "gemini-1.5-flash"])
    st.info("تێبینی: مۆدێلی Pro باشترە بۆ شیکردنەوەی ورد.")

input_srt = st.text_area("دەقی SRT لێرە دابنێ:", height=300, placeholder="دەقی ژێرنووسەکە لێرە کۆپی بکە...")

if st.button("🔍 شیکردنەوەی چیرۆک"):
    if not api_key:
        st.error("تکایە سەرەتا API Key داخڵ بکە.")
    elif not input_srt:
        st.warning("تکایە دەقی SRT دابنێ.")
    else:
        result = analyze_story_agent(input_srt, api_key, model_name)
        
        st.markdown("### 📊 ئەنجامی شیکردنەوە:")
        st.markdown(f"<div class='analysis-box'>{result}</div>", unsafe_allow_html=True)
        
        # دوگمەیەک بۆ کۆپی کردنی شیکردنەوەکە
        st.download_button("📥 داگرتنی شیکردنەوەکە وەک دەق", result, "story_analysis.txt")

# ڕێنمایی
with st.expander("ℹ️ ئەم بەرنامەیە چی دەکات؟"):
    st.write("""
    - **هیچ وەرگێڕانێک ناکات.**
    - تەنها دەقی فیلمەکە دەخوێنێتەوە.
    - زانیاری وردت دەدێ لەسەر ئەوەی فیلمەکە باسی چییە.
    - یارمەتیت دەدات تێبگەیت کەسایەتییەکان کێن و چۆن قسە دەکەن.
    """)
