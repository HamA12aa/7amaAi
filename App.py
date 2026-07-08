import streamlit as st
import google.generativeai as genai
from groq import Groq
import tempfile
import time
import os

# --- 1. ڕێکخستنی لاپەڕە و دیزاین ---
st.set_page_config(page_title="AI Movie Director PRO", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;700&display=swap');
    * { font-family: 'Vazirmatn', sans-serif; }
    .stTextArea textarea { direction: ltr !important; text-align: left !important; background-color: #0e1117; color: #00ffcc; font-family: monospace; }
    .kurdish-font { direction: rtl; text-align: right; }
    .stButton>button { width: 100%; background: linear-gradient(90deg, #ff4b2b, #ff416c); color: white; font-weight: bold; border: none; height: 3.5em; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. سایدبار و دۆزینەوەی مۆدێل (بۆ ڕێگری لە 404) ---
with st.sidebar:
    st.title("⚙️ ڕێکخستنی سێرڤەرەکان")
    gemini_key = st.text_input("🔑 Google Gemini Key:", type="password")
    groq_key = st.text_input("🔑 Groq Key (Llama):", type="password")
    st.markdown("---")
    
    selected_gemini = "gemini-1.5-flash" # Default
    if gemini_key:
        try:
            genai.configure(api_key=gemini_key)
            models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            selected_gemini = st.selectbox("🤖 مۆدێلی کارای گووگڵ:", models)
        except:
            st.warning("کلیلەکە داخڵ بکە بۆ بینینی مۆدێلەکان")

    video_file = st.file_uploader("🎬 بارکردنی ڤیدیۆ (بۆ پێداچوونەوە):", type=["mp4", "mov", "avi"])
    st.info("بریکاری ٥ سەیری ڤیدیۆکە دەکات و وەرگێڕانەکە ڕاست دەکاتەوە.")

# --- 3. ڕووکاری سەرەکی ---
st.markdown("<h1 style='text-align: center;'>🎬 وەرگێڕی ٥-ئەفسەری (Video AI)</h1>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.markdown("<h3 class='kurdish-font'>📥 دەقی ئینگلیزی (SRT)</h3>", unsafe_allow_html=True)
    input_srt = st.text_area("", height=400, label_visibility="collapsed")

with col2:
    st.markdown("<h3 class='kurdish-font'>📤 وەرگێڕانی کوردی</h3>", unsafe_allow_html=True)
    output_placeholder = st.empty()
    output_placeholder.info("چاوەڕێی دەستپێکردنم...")

# --- 4. فەنکشنی سەرەکی وەرگێڕان ---
if st.button("🚀 دەستپێکردنی پڕۆسەی وەرگێڕان و شیکاری ڤیدیۆ"):
    if not gemini_key or not groq_key or not input_srt:
        st.error("⚠️ تکایە هەموو کلیلەکان و دەقەکە ئامادە بکە.")
    else:
        try:
            # ئامادەکردنی مۆدێلەکان
            genai.configure(api_key=gemini_key)
            model_gemini = genai.GenerativeModel(selected_gemini)
            client_groq = Groq(api_key=groq_key)

            # --- دەستپێکردنی ٥ بریکارەکە ---
            
            # بریکاری ١: Gemini (وەرگێڕان)
            with st.status("🕵️ بریکاری ١: وەرگێڕانی واتا...") as s:
                r1 = model_gemini.generate_content(f"Translate this SRT to Kurdish Sorani: {input_srt}")
                t1 = r1.text
                s.update(label="قۆناغی ١ تەواو", state="complete")

            # بریکاری ٢: Gemini (سیاق و کلتوور)
            with st.status("🎭 بریکاری ٢: گونجاندنی سینەمایی...") as s:
                r2 = model_gemini.generate_content(f"Make this Kurdish text sound like a natural movie dialogue (Sorani): {t1}")
                t2 = r2.text
                s.update(label="قۆناغی ٢ تەواو", state="complete")

            # بریکاری ٣: Llama (ڕێزمان)
            with st.status("✍️ بریکاری ٣: ڕێزمانی کوردی (Llama)...") as s:
                r3 = client_groq.chat.completions.create(
                    model="llama-3.3-70b-specdec",
                    messages=[{"role": "user", "content": f"Fix the Kurdish grammar and sentence flow: {t2}"}]
                )
                t3 = r3.choices[0].message.content
                s.update(label="قۆناغی ٣ تەواو", state="complete")

            # بریکاری ٤: Llama (پاراستنی SRT)
            with st.status("📏 بریکاری ٤: ڕێکخستنی فۆرماتی ژێرنووس...") as s:
                r4 = client_groq.chat.completions.create(
                    model="llama-3.3-70b-specdec",
                    messages=[{"role": "user", "content": f"Keep the SRT timestamps exactly as they are. Shorten lines for screen: {t3}"}]
                )
                t4 = r4.choices[0].message.content
                s.update(label="قۆناغی ٤ تەواو", state="complete")

            # بریکاری ٥: Gemini (Director - Video Analysis)
            final_result = t4
            if video_file:
                with st.status("👁️ بریکاری ٥ (دەرهێنەر): خەریکی بینینی ڤیدیۆکەیە...") as s:
                    # پاشەکەوتکردنی کاتی ڤیدیۆکە
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                        tmp.write(video_file.read())
                        temp_path = tmp.name
                    
                    # بارکردن بۆ سێرڤەری گووگڵ
                    g_file = genai.upload_file(path=temp_path)
                    while g_file.state.name == "PROCESSING":
                        time.sleep(2)
                        g_file = genai.get_file(g_file.name)
                    
                    # شیکاری کۆتایی بەپێی دیمەن
                    r5 = model_gemini.generate_content([g_file, f"Watch the video and adjust this Kurdish SRT to match the actor's emotions and lips: {t4}"])
                    final_result = r5.text
                    s.update(label="پێداچوونەوەی ڤیدیۆ تەواو بوو!", state="complete")
                    os.remove(temp_path)

            # پیشاندانی ئەنجام
            output_placeholder.code(final_result, language="srt")
            st.balloons()

        except Exception as e:
            st.error(f"❌ هەڵەیەک ڕوویدا: {str(e)}")
            st.info("ئامۆژگاری: دڵنیابە کلیلەکانت ڕاستن و مۆدێلێکی دروست لە سایدبار هەڵبژێرە.")
