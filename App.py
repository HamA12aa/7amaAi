import streamlit as st
import google.generativeai as genai
from groq import Groq

# --- 1. ڕێکخستنی لاپەڕە ---
st.set_page_config(page_title="AI 5-Agents Subtitler", layout="wide")

# --- 2. چارەسەری دیزاین و گلیچی سایدبار (CSS) ---
st.markdown("""
    <style>
    /* تەنها بەشە ناوەخنییەکان بکە بە کوردی نەک هەموو سایتەکە تا سایدبار تێک نەچێت */
    .rtl-container {
        direction: rtl;
        text-align: right;
        font-family: 'Tahoma', sans-serif;
    }
    .stTextArea textarea {
        direction: ltr !important;
        text-align: left !important;
        background-color: #1a1a1a !important;
        color: #00ffcc !important;
    }
    /* چاککردنی ستایلی دوگمە */
    .stButton>button {
        width: 100%;
        background-color: #ff4b4b;
        color: white;
        border-radius: 10px;
        height: 3em;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. سایدبار (بەبێ گلیچ) ---
with st.sidebar:
    st.title("🔑 ڕێکخستنی کلیلەکان")
    gemini_key = st.text_input("Google API Key:", type="password")
    groq_key = st.text_input("Groq API Key:", type="password")
    st.markdown("---")
    genre = st.selectbox("🎭 جۆری فیلم/ئەنیمێ:", ["ئەنیمێ", "ئاکشن", "دراما", "کۆمیدی"])
    st.info("تێبینی: مۆدێلی Gemini 1.5 Flash بەکاردێت بۆ جێگیری سیستمەکە.")

# --- 4. بەشی سەرەکی ---
st.markdown('<div class="rtl-container"><h1>🎬 وەرگێڕی ٥-ئەفسەری (وەشانی جێگیر)</h1></div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="rtl-container"><h3>📥 دەقی ئینگلیزی (SRT)</h3></div>', unsafe_allow_html=True)
    input_text = st.text_area("", height=400, help="فایلی SRT لێرە کۆپی بکە")

with col2:
    st.markdown('<div class="rtl-container"><h3>📤 ئەنجامی کۆتایی</h3></div>', unsafe_allow_html=True)
    output_area = st.empty()
    output_area.info("چاوەڕێی وەرگێڕانم...")

# --- 5. لۆژیکی وەرگێڕان ---
if st.button("🚀 دەستپێکردنی وەرگێڕانی جادوویی"):
    if not gemini_key or not groq_key:
        st.error("⚠️ تکایە هەردوو کلیلەکە لە سایدبار داخڵ بکە.")
    elif not input_text:
        st.warning("⚠️ تکایە دەقێکی ئینگلیزی دابنێ.")
    else:
        try:
            # ڕێکخستنی مۆدێلەکان
            genai.configure(api_key=gemini_key)
            # بەکارهێنانی 1.5 Flash چونکە زۆر جێگیرترە
            gem_model = genai.GenerativeModel('gemini-1.5-flash')
            groq_client = Groq(api_key=groq_key)

            # --- دەستپێکردنی بریکارەکان ---
            
            # بریکاری ١: Gemini (وەرگێڕ)
            with st.status("🕵️ بریکاری ١: وەرگێڕان...") as s:
                p1 = f"Translate this movie dialogue to Kurdish Sorani: {input_text}"
                r1 = gem_model.generate_content(p1)
                t1 = r1.text
                s.update(label="قۆناغی ١ تەواو", state="complete")

            # بریکاری ٢: Gemini (سیاق)
            with st.status("🎭 بریکاری ٢: ڕێکخستنی سیاق...") as s:
                p2 = f"Make this Kurdish text sound like natural {genre} dialogue: {t1}"
                r2 = gem_model.generate_content(p2)
                t2 = r2.text
                s.update(label="قۆناغی ٢ تەواو", state="complete")

            # بریکاری ٣: Llama (ڕێزمان)
            with st.status("✍️ بریکاری ٣: ڕێزمانی کوردی...") as s:
                r3 = groq_client.chat.completions.create(
                    model="llama-3.3-70b-specdec", # وەشانی جێگیر و نوێی لاما لەسەر Groq
                    messages=[{"role": "user", "content": f"Fix the Kurdish grammar: {t2}"}]
                )
                t3 = r3.choices[0].message.content
                s.update(label="قۆناغی ٣ تەواو", state="complete")

            # بریکاری ٤: Llama (فۆرمات)
            with st.status("📏 بریکاری ٤: فۆرماتی SRT...") as s:
                r4 = groq_client.chat.completions.create(
                    model="llama-3.3-70b-specdec",
                    messages=[{"role": "user", "content": f"Keep SRT format and shorten lines: {t3}"}]
                )
                t4 = r4.choices[0].message.content
                s.update(label="قۆناغی ٤ تەواو", state="complete")

            # بریکاری ٥: Gemini (پیاچوونەوە)
            with st.status("🎬 بریکاری ٥: پیاچوونەوە...") as s:
                p5 = f"Final Polish. Output ONLY the translated SRT in Kurdish: {t4}"
                r5 = gem_model.generate_content(p5)
                final_result = r5.text
                s.update(label="هەموو قۆناغەکان تەواو بوون!", state="complete")

            # پیشاندانی ئەنجام
            output_area.code(final_result, language="srt")
            st.balloons()

        except Exception as e:
            st.error(f"❌ هەڵەیەک ڕوویدا: {e}")
            st.info("تێبینی: ئەگەر هەڵەی 'Not Found'ت دایەوە، دڵنیابە کە کلیلی APIـەکەت دروستە.")

st.markdown('</div>', unsafe_allow_html=True)
