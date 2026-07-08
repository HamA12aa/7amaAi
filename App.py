import streamlit as st
import google.generativeai as genai
from groq import Groq
import tempfile
import time
import os
import re
from tenacity import retry, stop_after_attempt, wait_exponential

# --- ڕێکخستنی لاپەڕە ---
st.set_page_config(page_title="AI Movie Director PRO", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;700&display=swap');
    * { font-family: 'Vazirmatn', sans-serif; }
    .stTextArea textarea { direction: ltr !important; text-align: left !important; background-color: #0e1117; color: #00ffcc; font-family: monospace; }
    .kurdish-font { direction: rtl; text-align: right; }
    .stButton>button { background: linear-gradient(90deg, #ff4b2b, #ff416c); color: white; font-weight: bold; border-radius: 8px; transition: 0.3s; }
    .stButton>button:hover { transform: scale(1.02); }
    </style>
""", unsafe_allow_html=True)

# --- فەنکشنەکانی یارمەتیدەر ---
def chunk_srt(text, size=30):
    """پارچەکردنی فایلی گەورە بۆ ئەوەی AI کراش نەکات"""
    blocks = re.split(r'\n\s*\n', text.strip())
    return ['\n\n'.join(blocks[i:i+size]) for i in range(0, len(blocks), size)]

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def call_gemini(model, prompt):
    """سیستەمی تاقیکردنەوەی دووبارە بۆ گووگڵ"""
    return model.generate_content(prompt).text

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def call_groq(client, prompt):
    """سیستەمی تاقیکردنەوەی دووبارە بۆ گرۆق"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-specdec",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content

# --- سایدبار ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3172/3172576.png", width=100)
    st.title("⚙️ ڕێکخستنی پڕۆفیشناڵ")
    
    # کلیلەکان بە دیفۆڵت دانراون
    gemini_key = st.text_input("🔑 Google Gemini Key:", value="AQ.Ab8RN6LnLbL0tInTU8sCyRJcjjr9Qi8fhlxwsxYTXhRSG5Cypw", type="password")
    groq_key = st.text_input("🔑 Groq Key (Llama):", value="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", type="password")
    
    st.markdown("---")
    st.subheader("📚 فەرهەنگی تایبەت")
    glossary = st.text_area("ناوی کارەکتەرەکان لێرە بنووسە بۆ ئەوەی هەڵە وەرنەگێڕدرێن (نموونە: John = جۆن)")
    
    st.markdown("---")
    video_file = st.file_uploader("🎬 بارکردنی ڤیدیۆ (بۆ بریکاری ٥):", type=["mp4", "mov", "avi"])

# --- ڕووکاری سەرەکی ---
st.markdown("<h1 style='text-align: center;'>🎬 وەرگێڕی سینەمایی ٥-ئەفسەری (PRO Version)</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>بەهێزترین سیستەمی وەرگێڕانی ژێرنووس بە بەکارهێنانی Llama 3.3 و Gemini Vision</p>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.markdown("<h3 class='kurdish-font'>📥 دەقی ئینگلیزی (SRT)</h3>", unsafe_allow_html=True)
    input_srt = st.text_area("", height=400, label_visibility="collapsed", placeholder="1\n00:00:01,000 --> 00:00:04,000\nHello World!")

with col2:
    st.markdown("<h3 class='kurdish-font'>📤 ئەنجامی کۆتایی</h3>", unsafe_allow_html=True)
    output_placeholder = st.empty()
    output_placeholder.info("چاوەڕێی دەستپێکردنم...")

# --- لۆژیکی سەرەکی (پڕۆسێسکردن) ---
if st.button("🚀 دەستپێکردنی پڕۆسەی سینەمایی"):
    if not input_srt:
        st.warning("⚠️ تکایە سەرەتا دەقی ژێرنووسەکە دابنێ.")
    else:
        try:
            # ١. ڕێکخستنی API ـیەکان
            genai.configure(api_key=gemini_key)
            model_gemini = genai.GenerativeModel("gemini-1.5-flash")
            client_groq = Groq(api_key=groq_key)

            # ٢. پارچەکردنی دەقەکە (Smart Chunking)
            chunks = chunk_srt(input_srt, size=40) # هەر ٤٠ بلۆکێک دەکاتە یەک پارچە
            total_chunks = len(chunks)
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            final_srt_pieces = []

            # ٣. پڕۆسێسکردنی پارچەکان
            for idx, chunk in enumerate(chunks):
                status_text.markdown(f"**لە پڕۆسەدایە... پارچەی {idx+1} لە {total_chunks}** ⏳")
                
                # بریکاری ١: وەرگێڕانی واتا
                prompt_1 = f"""Translate this SRT to Kurdish Sorani.
Glossary: {glossary}
Rule: Keep the numbering and timestamps intact (e.g. 00:00:01,000 --> 00:00:04,000).
SRT: {chunk}"""
                t1 = call_gemini(model_gemini, prompt_1)

                # بریکاری ٢: سینەمایی کردن
                prompt_2 = f"Make this Kurdish dialogue natural and cinematic. Keep SRT formatting intact:\n{t1}"
                t2 = call_gemini(model_gemini, prompt_2)

                # بریکاری ٣ و ٤ (یەکخراون بۆ خێرایی): ڕێزمان و فۆرمات
                prompt_3_4 = f"""Fix any Kurdish grammatical errors and ensure the text sounds perfectly natural.
CRITICAL: You MUST output valid SRT format. Do not change the timestamps. Do not remove the empty lines between subtitles.
Text: {t2}"""
                t4 = call_groq(client_groq, prompt_3_4)
                
                final_srt_pieces.append(t4)
                progress_bar.progress((idx + 1) / total_chunks)
                
                # کەمێک وەستان بۆ ڕێگری لە بلۆکبوونی سێرڤەر (Rate Limit)
                time.sleep(2)

            # یەکخستنەوەی پارچەکان
            combined_srt = "\n\n".join(final_srt_pieces)

            # ٤. بریکاری ٥: دەرهێنەری ڤیدیۆ (ئەگەر ڤیدیۆ هەبێت)
            if video_file:
                with st.spinner("👁️ بریکاری ٥ (دەرهێنەر): خەریکی شیکاری ڤیدیۆ و هاوکاتکردنی ژێرنووسەکەیە..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                        tmp.write(video_file.read())
                        temp_path = tmp.name
                    
                    g_file = genai.upload_file(path=temp_path)
                    while g_file.state.name == "PROCESSING":
                        time.sleep(2)
                        g_file = genai.get_file(g_file.name)
                    
                    prompt_5 = f"Watch this video. Here is the translated Kurdish SRT. Adjust the dialogue slightly if needed to match the emotions and scenes in the video. output ONLY the final valid SRT format:\n\n{combined_srt}"
                    
                    final_result = call_gemini(model_gemini, [g_file, prompt_5])
                    os.remove(temp_path)
            else:
                final_result = combined_srt

            # ٥. نیشاندانی ئەنجام و دوگمەی داگرتن
            output_placeholder.code(final_result, language="srt")
            status_text.success("🎉 پڕۆسەکە بە سەرکەوتوویی کۆتایی هات!")
            st.balloons()

            # دوگمەی داگرتن (Download)
            st.download_button(
                label="📥 داگرتنی فایلی SRT",
                data=final_result,
                file_name="movie_translated.srt",
                mime="text/plain"
            )

        except Exception as e:
            st.error(f"❌ هەڵەیەک ڕوویدا. ڕەنگە کێشە لە ئینتەرنێت یان API هەبێت: {str(e)}")
            st.info("💡 تێبینی: سیستەمەکە هەوڵی خۆی دا، تکایە دڵنیابە کلیلەکان کار دەکەن و سنوری بەکارهێنانیان تێپەڕ نەکردووە.")
