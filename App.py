import streamlit as st
import google.generativeai as genai
from groq import Groq
import tempfile
import time

# --- دیزاین ---
st.set_page_config(page_title="AI Video Translator FREE", layout="wide")
st.markdown("<style>textarea { direction: ltr; text-align: left; background: #111; color: #0f9; }</style>", unsafe_allow_html=True)

# --- سایدبار بۆ کلیلەکان ---
with st.sidebar:
    st.title("🔑 سێرڤەرە بەلاشەکان")
    gemini_key = st.text_input("Google API Key:", type="password")
    groq_key = st.text_input("Groq API Key:", type="password")
    video_file = st.file_uploader("🎬 ڤیدیۆی کورت باربکە:", type=["mp4", "mov", "avi"])

st.title("🎬 وەرگێڕی ٥-ئەفسەری (بینەری ڤیدیۆ - بەلاش)")

input_srt = st.text_area("📥 دەقی ئینگلیزی (SRT) لێرە دابنێ:", height=200)

if st.button("🚀 دەستپێکردنی پرۆسەی ژێربینین"):
    if not gemini_key or not groq_key or not input_srt:
        st.error("تکایە کلیلەکان و دەقەکە پڕ بکەرەوە.")
    else:
        try:
            genai.configure(api_key=gemini_key)
            gem_model = genai.GenerativeModel('gemini-1.5-flash')
            groq_client = Groq(api_key=groq_key)

            # بریکاری ١ و ٢ (Gemini): وەرگێڕان و کلتوور
            with st.status("🕵️ بریکاری ١ و ٢: وەرگێڕان...") as s:
                t1 = gem_model.generate_content(f"Translate to natural Kurdish: {input_srt}").text
                s.update(label="وەرگێڕان تەواو بوو", state="complete")

            # بریکاری ٣ و ٤ (Groq - Llama): ڕێزمان و فۆرمات
            with st.status("✍️ بریکاری ٣ و ٤: ڕێزمان و SRT...") as s:
                res = groq_client.chat.completions.create(
                    model="llama-3.3-70b-specdec",
                    messages=[{"role": "user", "content": f"Fix Kurdish grammar and SRT format: {t1}"}]
                )
                t3 = res.choices[0].message.content
                s.update(label="ڕێزمان ڕێکخرا", state="complete")

            # بریکاری ٥ (Gemini - Video Observer): پێداچوونەوە بە ڤیدیۆ
            if video_file:
                with st.status("👁️ بریکاری ٥: سەیری ڤیدیۆ دەکات و دەقەکە ڕادەگرێت...") as s:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                        tmp.write(video_file.read())
                        video_path = tmp.name
                    
                    # بارکردنی ڤیدیۆ بۆ سێرڤەری گووگڵ (بەلاش)
                    g_file = genai.upload_file(path=video_path)
                    while g_file.state.name == "PROCESSING":
                        time.sleep(2)
                        g_file = genai.get_file(g_file.name)
                    
                    # شیکردنەوەی کۆتایی بەپێی دیمەن
                    response = gem_model.generate_content([g_file, f"Watch this and fix this Kurdish SRT based on character emotions and lip-sync: {t3}"])
                    final_srt = response.text
                    s.update(label="پێداچوونەوەی ڤیدیۆ کۆتایی هات", state="complete")
            else:
                final_srt = t3
                st.warning("ڤیدیۆ نییە، تەنها بە دەق پێداچوونەوە کرا.")

            st.subheader("🎯 ئەنجامی کۆتایی:")
            st.code(final_srt, language="srt")
            
        except Exception as e:
            st.error(f"هەڵەیەک ڕوویدا: {e}")
