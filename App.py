import streamlit as st
import google.generativeai as genai
from groq import Groq

# --- 1. ڕێکخستنی لاپەڕە ---
st.set_page_config(page_title="AI Subtitle Pro 5", layout="wide", page_icon="🎬")

# --- 2. چارەسەری دیزاین (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;700&display=swap');
    
    html, body, [data-testid="stSidebar"], .stMarkdown {
        font-family: 'Vazirmatn', sans-serif;
    }

    .stTextArea textarea {
        direction: ltr !important;
        text-align: left !important;
        font-family: monospace !important;
        background-color: #0e1117 !important;
        color: #00ffcc !important;
    }

    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        background-color: #ff4b4b;
        color: white;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. سایدبار و دۆزینەوەی مۆدێلەکان (ئۆتۆماتیکی) ---
with st.sidebar:
    st.title("🛠️ ڕێکخستنی سیستم")
    gemini_key = st.text_input("🔑 Google API Key:", type="password")
    groq_key = st.text_input("🔑 Groq API Key:", type="password")
    
    st.markdown("---")
    gemini_model_name = None
    
    # *** گەڕانی ئۆتۆماتیکی بەدوای مۆدێلە کارپێکراوەکان ***
    if gemini_key:
        try:
            genai.configure(api_key=gemini_key)
            available_models = []
            # پرسیار لە گووگڵ دەکات بزانێت چ مۆدێلێک بەردەستە
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    # ناوی مۆدێلەکە خاوێن دەکاتەوە و دەیخاتە لیستەوە
                    available_models.append(m.name.replace('models/', ''))
            
            if available_models:
                gemini_model_name = st.selectbox("🤖 مۆدێلەکانی گووگڵ (کارپێکراو):", available_models)
        except Exception as e:
            st.error("⚠️ کلیلەکەت کێشەی هەیە یان ئینتەرنێت بڕاوە.")
    else:
        st.info("سەرەتا کلیلی گووگڵ دابنێ بۆ بینینی مۆدێلەکان.")
        
    genre = st.selectbox("🎭 جۆری وەرگێڕان:", ["ئەنیمێ", "ئاکشن", "دراما", "کۆمیدی"])

# --- 4. ناوەڕۆکی سەرەکی ---
st.markdown("<h2 style='text-align: center; direction: rtl;'>🎬 وەرگێڕی زیرەکی ٥-ئەفسەری</h2>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("<h3 style='direction: rtl;'>📥 ئینگلیزی (SRT)</h3>", unsafe_allow_html=True)
    input_text = st.text_area("دەقەکە لێرە دابنێ", height=400, label_visibility="collapsed")

with col2:
    st.markdown("<h3 style='direction: rtl;'>📤 وەرگێڕانی کوردی</h3>", unsafe_allow_html=True)
    output_placeholder = st.empty()
    output_placeholder.info("چاوەڕێی دەستپێکردنم...")

# --- 5. لۆژیکی کارکردن ---
if st.button("🚀 دەستپێکردنی پرۆسەی وەرگێڕان"):
    if not gemini_key or not groq_key:
        st.error("⚠️ تکایە هەردوو کلیلەکە لە سایدبار داخڵ بکە.")
    elif not gemini_model_name:
        st.error("⚠️ هیچ مۆدێلێکی گووگڵ نەدۆزرایەوە.")
    elif not input_text:
        st.warning("⚠️ دەقێکی ئینگلیزی دابنێ.")
    else:
        try:
            # ڕێکخستنی Gemini لەگەڵ ئەو مۆدێلەی لە لیستەکە هەڵبژێردراوە
            genai.configure(api_key=gemini_key)
            model_gemini = genai.GenerativeModel(gemini_model_name)
            
            # ڕێکخستنی Groq
            client_groq = Groq(api_key=groq_key)

            with st.status("🕵️ بریکاری ١: خەریکی وەرگێڕانە...") as s:
                r1 = model_gemini.generate_content(f"Translate this SRT to Kurdish Sorani: {input_text}")
                t1 = r1.text
                s.update(label="قۆناغی ١ تەواو", state="complete")

            with st.status("🎭 بریکاری ٢: ڕێکخستنی شێوازی قسەکردن...") as s:
                r2 = model_gemini.generate_content(f"Make this Kurdish text sound like natural {genre} dialogue: {t1}")
                t2 = r2.text
                s.update(label="قۆناغی ٢ تەواو", state="complete")

            with st.status("✍️ بریکاری ٣: ڕێزمانی کوردی (Llama)...") as s:
                r3 = client_groq.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": f"Fix the Kurdish grammar: {t2}"}]
                )
                t3 = r3.choices[0].message.content
                s.update(label="قۆناغی ٣ تەواو", state="complete")

            with st.status("📏 بریکاری ٤: فۆرماتکردنی ژێرنووس...") as s:
                r4 = client_groq.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": f"Keep SRT format exactly the same, keep numbers perfectly matched, and shorten text: {t3}"}]
                )
                t4 = r4.choices[0].message.content
                s.update(label="قۆناغی ٤ تەواو", state="complete")

            with st.status("🎬 بریکاری ٥: پیاچوونەوەی دەرهێنەر...") as s:
                r5 = model_gemini.generate_content(f"Final check. Output ONLY the perfect Kurdish SRT without any conversation: {t4}")
                final_result = r5.text
                s.update(label="هەموو قۆناغەکان تەواو بوون!", state="complete")

            output_placeholder.code(final_result, language="srt")
            st.balloons()

        except Exception as e:
            st.error(f"❌ هەڵەیەک ڕوویدا: {str(e)}")
