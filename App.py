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

    /* باکسەکانی دەق بە ئینگلیزی بمێننەوە بۆ ئەوەی تێک نەچن */
    .stTextArea textarea {
        direction: ltr !important;
        text-align: left !important;
        font-family: monospace !important;
        background-color: #0e1117 !important;
        color: #00ffcc !important;
    }

    /* بەشی ئەنجام بە کوردی و ڕاست بۆ چەپ */
    .kurdish-result {
        direction: rtl;
        text-align: right;
        background-color: #1a1c24;
        padding: 20px;
        border-radius: 10px;
        border-right: 5px solid #ff4b4b;
        color: white;
    }

    /* دوگمەکان */
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

# --- 3. سایدبار (بەبێ گلیچ) ---
with st.sidebar:
    st.title("🛠️ ڕێکخستنی سیستم")
    gemini_key = st.text_input("🔑 Google API Key:", type="password")
    groq_key = st.text_input("🔑 Groq API Key:", type="password")
    
    st.markdown("---")
    # ئەگەر فلاش کاری نەکرد، لێرە مۆدێلەکە بگۆڕە
    gemini_model_name = st.selectbox("🤖 مۆدێلی Gemini:", 
                                     ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-1.5-pro"])
    
    genre = st.selectbox("🎭 جۆری وەرگێڕان:", ["ئەنیمێ", "ئاکشن", "دراما", "کۆمیدی"])
    st.info("ئەم سیستمە ٥ بریکاری زیرەک بەکاردەهێنێت بۆ وەرگێڕان.")

# --- 4. ناوەڕۆکی سەرەکی ---
st.markdown("<h2 style='text-align: center;'>🎬 وەرگێڕی زیرەکی ٥-ئەفسەری</h2>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📥 ئینگلیزی (SRT)")
    input_text = st.text_area("دەقەکە لێرە دابنێ", height=400, label_visibility="collapsed")

with col2:
    st.markdown("### 📤 وەرگێڕانی کوردی")
    output_placeholder = st.empty()
    output_placeholder.info("چاوەڕێی دەستپێکردنم...")

# --- 5. لۆژیکی کارکردن ---
if st.button("🚀 دەستپێکردنی پرۆسەی وەرگێڕان"):
    if not gemini_key or not groq_key:
        st.error("⚠️ تکایە هەردوو کلیلەکە لە سایدبار داخڵ بکە.")
    elif not input_text:
        st.warning("⚠️ دەقێکی ئینگلیزی دابنێ.")
    else:
        try:
            # ڕێکخستنی Gemini
            genai.configure(api_key=gemini_key)
            model_gemini = genai.GenerativeModel(gemini_model_name)
            
            # ڕێکخستنی Groq
            client_groq = Groq(api_key=groq_key)

            # بریکاری ١: Gemini (وەرگێڕان)
            with st.status("🕵️ بریکاری ١: خەریکی وەرگێڕانە...") as s:
                r1 = model_gemini.generate_content(f"Translate this SRT to Kurdish Sorani: {input_text}")
                t1 = r1.text
                s.update(label="قۆناغی ١ تەواو", state="complete")

            # بریکاری ٢: Gemini (سیاق و ئەنیمێ)
            with st.status("🎭 بریکاری ٢: ڕێکخستنی شێوازی قسەکردن...") as s:
                r2 = model_gemini.generate_content(f"Make this Kurdish text sound like natural {genre} dialogue: {t1}")
                t2 = r2.text
                s.update(label="قۆناغی ٢ تەواو", state="complete")

            # بریکاری ٣: Llama (ڕێزمان)
            with st.status("✍️ بریکاری ٣: ڕێزمانی کوردی (Llama)...") as s:
                r3 = client_groq.chat.completions.create(
                    model="llama-3.3-70b-specdec",
                    messages=[{"role": "user", "content": f"Fix the Kurdish grammar: {t2}"}]
                )
                t3 = r3.choices[0].message.content
                s.update(label="قۆناغی ٣ تەواو", state="complete")

            # بریکاری ٤: Llama (فۆرماتی SRT)
            with st.status("📏 بریکاری ٤: فۆرماتکردنی ژێرنووس...") as s:
                r4 = client_groq.chat.completions.create(
                    model="llama-3.3-70b-specdec",
                    messages=[{"role": "user", "content": f"Keep SRT format and keep lines short: {t3}"}]
                )
                t4 = r4.choices[0].message.content
                s.update(label="قۆناغی ٤ تەواو", state="complete")

            # بریکاری ٥: Gemini (پیاچوونەوەی کۆتایی)
            with st.status("🎬 بریکاری ٥: پیاچوونەوەی دەرهێنەر...") as s:
                r5 = model_gemini.generate_content(f"Final check. Output ONLY the Kurdish SRT: {t4}")
                final_result = r5.text
                s.update(label="هەموو قۆناغەکان تەواو بوون!", state="complete")

            # پیشاندانی ئەنجام
            output_placeholder.code(final_result, language="srt")
            st.balloons()

        except Exception as e:
            st.error(f"❌ هەڵەیەک ڕوویدا: {str(e)}")
            st.info("ئامۆژگاری: ئەگەر هەڵەی 404ت بینی، لە سایدبار 'gemini-1.5-flash-latest' هەڵبژێره.")
