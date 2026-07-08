import streamlit as st
import google.generativeai as genai
from groq import Groq

# --- ڕێکخستنی لاپەڕە ---
st.set_page_config(page_title="AI Movie Agents 5.0", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;700&display=swap');
    * { font-family: 'Vazirmatn', sans-serif; direction: rtl; }
    .stApp { background-color: #0b0c10; color: #66fcf1; }
    .stTextArea textarea { background-color: #1f2833 !important; color: #45a29e !important; direction: ltr !important; }
    .agent-status { border-right: 4px solid #66fcf1; padding-right: 15px; margin-bottom: 10px; color: #c5c6c7; }
    </style>
""", unsafe_allow_html=True)

# --- لای تەنیشت بۆ کلیلەکان ---
with st.sidebar:
    st.title("🔑 کلیلی سێرڤەرەکان")
    gemini_key = st.text_input("Google API Key:", type="password")
    groq_key = st.text_input("Groq API Key (Llama 3.1):", type="password")
    st.markdown("---")
    genre = st.selectbox("🎭 جۆری فیلم:", ["ئەنیمێ", "ئاکشن", "دراما", "کۆمیدی"])

# --- فەنکشنەکانی بریکارەکان ---
def run_agents(eng_text):
    # 1. Gemini - Translator
    genai.configure(api_key=gemini_key)
    gem_model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    # 2. Groq - Llama 3.1
    client = Groq(api_key=groq_key)

    # قۆناغی ١ (Gemini): وەرگێڕان
    with st.status("🕵️ بریکاری ١: خەریکی وەرگێڕانی ماناکەیە...") as s:
        res1 = gem_model.generate_content(f"Translate this movie dialogue to Kurdish Sorani. Focus on meaning: {eng_text}")
        trans1 = res1.text
        s.update(label="✅ وەرگێڕان تەواو بوو", state="complete")

    # قۆناغی ٢ (Gemini): شێوازی قسەکردن
    with st.status("🎭 بریکاری ٢: خەریکی گونجاندنی کلتوورییە...") as s:
        res2 = gem_model.generate_content(f"Adapt this Kurdish text to sound like a natural {genre}. Use cool Kurdish slang: {trans1}")
        trans2 = res2.text
        s.update(label="✅ شێوازی قسەکردن ڕێکخرا", state="complete")

    # قۆناغی ٣ (Llama 3.1 via Groq): ڕێزمان
    with st.status("✍️ بریکاری ٣: خەریکی ڕاستکردنەوەی ڕێزمانە...") as s:
        res3 = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": f"Fix the Kurdish Sorani grammar and verb tenses in this text: {trans2}"}]
        )
        trans3 = res3.choices[0].message.content
        s.update(label="✅ ڕێزمان چاککرا", state="complete")

    # قۆناغی ٤ (Llama 3.1 via Groq): فۆرماتی SRT
    with st.status("📏 بریکاری ٤: خەریکی ڕێکخستنی درێژی ڕستەکانە...") as s:
        res4 = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": f"Make sure these Kurdish lines are short enough for subtitles. Keep the SRT format perfectly: {trans3}"}]
        )
        trans4 = res4.choices[0].message.content
        s.update(label="✅ فۆرمات ڕێکخرا", state="complete")

    # قۆناغی ٥ (Gemini): پیاچوونەوەی کۆتایی
    with st.status("🎬 بریکاری ٥: پیاچوونەوەی کۆتایی دەرهێنەر...") as s:
        res5 = gem_model.generate_content(f"Compare original English with this Kurdish. Fix any final errors and output ONLY the final SRT: \nEnglish: {eng_text}\nKurdish: {trans4}")
        final_out = res5.text
        s.update(label="✅ هەموو قۆناغەکان تەواو بوون!", state="complete")
        
    return final_out

# --- ڕووکاری سایتەکە ---
st.header("🎬 وەرگێڕی ٥-ئەفسەرەکە (Gemini 2.0 + Llama 3.1)")

col1, col2 = st.columns(2)

with col1:
    input_srt = st.text_area("📥 دەقی ئینگلیزی لێرە دابنێ:", height=400)

with col2:
    if st.button("🚀 دەستپێکردنی وەرگێڕانی جادوویی"):
        if gemini_key and groq_key and input_srt:
            result = run_agents(input_srt)
            st.code(result, language="srt")
        else:
            st.error("تکایە هەردوو کلیلەکە و دەقەکە داخڵ بکە!")
