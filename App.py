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
    </style>
""", unsafe_allow_html=True)

def chunk_srt(text, size=30):
    blocks = re.split(r'\n\s*\n', text.strip())
    return ['\n\n'.join(blocks[i:i+size]) for i in range(0, len(blocks), size)]

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def call_groq(client, prompt):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content

# --- سایدبار ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3172/3172576.png", width=100)
    st.title("⚙️ ڕێکخستنی پڕۆفیشناڵ")
    
    # تکایە دڵنیابە لە کلیلەکەی گووگڵ، پێویستە بە AIzaSy دەست پێ بکات
    gemini_key = st.text_input("🔑 Google Gemini Key (بە AIza دەست پێ دەکات):", value="", type="password")
    groq_key = st.text_input("🔑 Groq Key (Llama):", value="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", type="password")
    
    st.markdown("---")
    glossary = st.text_area("📚 فەرهەنگی تایبەت (نموونە: John = جۆن)")
    
    st.markdown("---")
    video_file = st.file_uploader("🎬 بارکردنی ڤیدیۆ (بۆ بریکاری ٥ بە Gemini):", type=["mp4"])

# --- ڕووکاری سەرەکی ---
st.markdown("<h1 style='text-align: center;'>🎬 وەرگێڕی سینەمایی ٥-ئەفسەری (Ultra Fast)</h1>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.markdown("<h3 class='kurdish-font'>📥 دەقی ئینگلیزی (SRT)</h3>", unsafe_allow_html=True)
    input_srt = st.text_area("", height=400, label_visibility="collapsed")

with col2:
    st.markdown("<h3 class='kurdish-font'>📤 ئەنجامی کۆتایی</h3>", unsafe_allow_html=True)
    output_placeholder = st.empty()
    output_placeholder.info("چاوەڕێی دەستپێکردنم...")

# --- لۆژیکی سەرەکی ---
if st.button("🚀 دەستپێکردنی پڕۆسەی خێرا (Ultra Fast)"):
    if not input_srt:
        st.warning("⚠️ تکایە سەرەتا دەقی ژێرنووسەکە دابنێ.")
    else:
        try:
            client_groq = Groq(api_key=groq_key)
            
            chunks = chunk_srt(input_srt, size=30)
            total_chunks = len(chunks)
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            final_srt_pieces = []

            # قۆناغی ١: وەرگێڕان بە خێرایی Groq
            for idx, chunk in enumerate(chunks):
                status_text.markdown(f"**⚡ بە خێرایی Groq وەرگێڕان دەکرێت... پارچەی {idx+1} لە {total_chunks}**")
                
                prompt_groq = f"""You are a professional movie subtitle translator. Translate this English SRT to perfect natural Kurdish Sorani.
Rules:
1. Do NOT change the timestamps or subtitle numbers.
2. Use this glossary if names appear: {glossary}
3. The translation must sound like a real cinematic Kurdish movie.
4. ONLY output the SRT format. No extra text.

SRT to translate:
{chunk}"""
                
                translated_chunk = call_groq(client_groq, prompt_groq)
                final_srt_pieces.append(translated_chunk)
                progress_bar.progress((idx + 1) / total_chunks)
                time.sleep(1)

            combined_srt = "\n\n".join(final_srt_pieces)
            final_result = combined_srt # ئەنجامەکە پارێزراو دەبێت ئەگەر گێمنایش کار نەکات

            # قۆناغی ٢: گێمنای (ئەگەر ڤیدیۆ هەبێت)
            if video_file:
                try:
                    if not gemini_key:
                        st.warning("⚠️ کلیلەکەی گێمنایت نەداوە! بۆیە بەبێ بینینی ڤیدیۆکە تەنها وەرگێڕانەکەی گرۆقت پێ دەدەم.")
                    else:
                        genai.configure(api_key=gemini_key)
                        model_gemini = genai.GenerativeModel("gemini-1.5-flash")
                        
                        with st.spinner("👁️ بریکاری ٥ (Gemini Vision): خەریکی شیکاری ڤیدیۆکەیە بۆ هاوکاتکردن..."):
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                                tmp.write(video_file.read())
                                temp_path = tmp.name
                            
                            g_file = genai.upload_file(path=temp_path)
                            while g_file.state.name == "PROCESSING":
                                time.sleep(2)
                                g_file = genai.get_file(g_file.name)
                            
                            prompt_5 = f"Watch this video. Here is the translated Kurdish SRT. Fix the subtitles slightly so they perfectly match the visual context and emotions on the screen. Output ONLY the final valid SRT format without any markdown blocks:\n\n{combined_srt}"
                            
                            r5 = model_gemini.generate_content([g_file, prompt_5])
                            final_result = r5.text
                            os.remove(temp_path)
                            st.success("✅ ڤیدیۆکەش بە سەرکەوتوویی بینرا و ژێرنووسەکە گونجێندرا!")
                
                except Exception as gemini_error:
                    st.error("⚠️ کێشەیەک لە کلیلەکەی گێمنای هەبوو (لەوانەیە هەڵە بێت یان بەسەرچووبێت)، بۆیە نەیتوانی ڤیدیۆکە بخوێنێتەوە.")
                    st.success("بەهەرحاڵ خەمت نەبێت! کارەکەی گرۆقم بۆ پاراستویت و نەمفەوتاند.")
                    # final_result هەر وەک خۆی دەمێنێتەوە کە بە گرۆق کراوە

            # نیشاندانی ئەنجام لە هەموو حاڵەتێکدا!
            output_placeholder.code(final_result, language="srt")
            if not video_file or "gemini_error" in locals():
                status_text.success("🎉 پڕۆسەی وەرگێڕان بە گرۆق بە سەرکەوتوویی کۆتایی هات!")
            
            st.balloons()
            
            st.download_button(
                label="📥 داگرتنی فایلی SRT",
                data=final_result,
                file_name="ultra_fast_movie.srt",
                mime="text/plain"
            )

        except Exception as e:
            st.error(f"❌ هەڵەیەک لە گرۆق یان سیستەمەکە ڕوویدا: {str(e)}")
