import streamlit as st
import google.generativeai as genai
from groq import Groq

# --- ڕێکخستنی سەرەتایی ---
st.set_page_config(page_title="AI 5-Agents Translator", layout="wide")

# دیزاین
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;700&display=swap');
    * { font-family: 'Vazirmatn', sans-serif; direction: rtl; }
    .stApp { background-color: #0e1117; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎬 سیستەمی وەرگێڕانی ٥-ئەفسەری (Gemini + Llama)")

# --- لای تەنیشت بۆ کلیلەکان ---
st.sidebar.header("🔑 کلیلەکان داخڵ بکە")
gemini_key = st.sidebar.text_input("Google API Key:", type="password")
groq_key = st.sidebar.text_input("Groq API Key:", type="password")
genre = st.sidebar.selectbox("🎭 جۆری فیلم:", ["ئەنیمێ", "ئاکشن", "دراما", "کۆمیدی"])

# --- بەشی سەرەکی ---
col1, col2 = st.columns(2)

with col1:
    input_text = st.text_area("📥 دەقی ئینگلیزی (SRT):", height=350)

with col2:
    st.write("📤 ئەنجامی وەرگێڕان:")
    output_placeholder = st.empty()
    output_placeholder.info("چاوەڕێی دەق و کلیلەکانم...")

# --- لۆژیکی وەرگێڕان ---
if st.button("🚀 دەستپێکردنی وەرگێڕان"):
    if not gemini_key or not groq_key:
        st.error("⚠️ تکایە هەردوو کلیلەکە لە لای چەپ دابنێ!")
    elif not input_text:
        st.warning("⚠️ دەقێک بنووسە!")
    else:
        try:
            # ئامادەکردنی مۆدێلەکان
            genai.configure(api_key=gemini_key)
            gem_model = genai.GenerativeModel('gemini-2.0-flash-exp')
            groq_client = Groq(api_key=groq_key)

            # بریکاری ١ (Gemini): وەرگێڕی سەرەکی
            with st.status("🕵️ بریکاری ١ خەریکی وەرگێڕانە...") as s:
                p1 = f"Translate this movie dialogue to Kurdish Sorani: {input_text}"
                r1 = gem_model.generate_content(p1)
                t1 = r1.text
                s.update(label="قۆناغی ١ تەواو", state="complete")

            # بریکاری ٢ (Gemini): گونجاندنی کلتووری
            with st.status("🎭 بریکاری ٢ خەریکی ڕێکخستنی کلتوورییە...") as s:
                p2 = f"Make this Kurdish translation sound natural for a {genre} movie/anime: {t1}"
                r2 = gem_model.generate_content(p2)
                t2 = r2.text
                s.update(label="قۆناغی ٢ تەواو", state="complete")

            # بریکاری ٣ (Llama 3.1): ڕێزمان
            with st.status("✍️ بریکاری ٣ خەریکی چاککردنی ڕێزمانە...") as s:
                r3 = groq_client.chat.completions.create(
                    model="llama-3.1-70b-versatile",
                    messages=[{"role": "user", "content": f"Fix the Kurdish Sorani grammar for this text: {t2}"}]
                )
                t3 = r3.choices[0].message.content
                s.update(label="قۆناغی ٣ تەواو", state="complete")

            # بریکاری ٤ (Llama 3.1): فۆرماتکردنی ژێرنووس
            with st.status("📏 بریکاری ٤ خەریکی کورتکردنەوەی ڕستەکانە...") as s:
                r4 = groq_client.chat.completions.create(
                    model="llama-3.1-70b-versatile",
                    messages=[{"role": "user", "content": f"Keep the SRT format and make Kurdish lines short: {t3}"}]
                )
                t4 = r4.choices[0].message.content
                s.update(label="قۆناغی ٤ تەواو", state="complete")

            # بریکاری ٥ (Gemini): پیاچوونەوەی کۆتایی
            with st.status("🎬 بریکاری ٥ خەریکی پیاچوونەوەی کۆتاییە...") as s:
                p5 = f"Final check! Combine all and output ONLY the final SRT in Kurdish: {t4}"
                r5 = gem_model.generate_content(p5)
                final_result = r5.text
                s.update(label="هەموو قۆناغەکان تەواو بوون!", state="complete")

            output_placeholder.code(final_result, language="srt")
            st.success("✅ وەرگێڕان بە سەرکەوتوویی کۆتایی هات!")

        except Exception as e:
            st.error(f"❌ هەڵەیەک ڕوویدا: {e}")
