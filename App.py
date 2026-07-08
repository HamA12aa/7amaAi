import streamlit as st
import google.generativeai as genai
from groq import Groq
import tempfile
import time
import os
import re
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# --- ڕێکخستنی لاپەڕە ---
st.set_page_config(page_title="AI Movie Director PRO", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;700&display=swap');
    * { font-family: 'Vazirmatn', sans-serif; }
    .kurdish-font { direction: rtl; text-align: right; }
    .stButton>button { background: linear-gradient(90deg, #ff4b2b, #ff416c); color: white; font-weight: bold; border-radius: 8px; transition: 0.3s; }
    </style>
""", unsafe_allow_html=True)

# --- فەنکشنەکانی شیکردنەوەی ژێرنووس (Token Optimization) ---
def parse_srt(srt_string):
    """جیاکردنەوەی کاتەکان لە دەقەکە بۆ پاشەکەوتکردنی تۆکن"""
    blocks = re.split(r'\n\s*\n', srt_string.strip())
    parsed = []
    for block in blocks:
        lines = block.split('\n')
        if len(lines) >= 3:
            idx = lines[0].strip()
            time_str = lines[1].strip()
            text = '\n'.join(lines[2:]).strip()
            parsed.append({'id': idx, 'time': time_str, 'text': text})
    return parsed

def build_srt(parsed_list):
    """کۆکردنەوەی ژێرنووسەکە بە کاتەکانەوە وەک خۆی"""
    return '\n\n'.join([f"{item['id']}\n{item['time']}\n{item['text']}" for item in parsed_list])

# --- سیستەمی دووبارە هەوڵدانەوە ---
# لێرەدا ئەگەر کێشەی RateLimit دروست بوو، تا ٢٠ چرکە چاوەڕێ دەکات لەبری کراشکردن
@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=4, max=20))
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
    
    gemini_key = st.text_input("🔑 Google Gemini Key (بە AIza دەست پێ دەکات):", type="password")
    groq_key = st.text_input("🔑 Groq Key (Llama):", value="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", type="password")
    st.markdown("---")
    glossary = st.text_area("📚 فەرهەنگی تایبەت (نموونە: John = جۆن)")
    st.markdown("---")
    video_file = st.file_uploader("🎬 بارکردنی ڤیدیۆ (بۆ گێمنای):", type=["mp4"])

# --- ڕووکاری سەرەکی ---
st.markdown("<h1 style='text-align: center;'>🎬 وەرگێڕی سینەمایی ٥-ئەفسەری (Live Streaming)</h1>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.markdown("<h3 class='kurdish-font'>📥 دەقی ئینگلیزی (SRT)</h3>", unsafe_allow_html=True)
    input_srt = st.text_area("", height=500, label_visibility="collapsed")

with col2:
    st.markdown("<h3 class='kurdish-font'>📤 ئەنجامی ڕاستەوخۆ (Live)</h3>", unsafe_allow_html=True)
    # ئامادەکردنی بۆکسێک بۆ پیشاندانی ڕاستەوخۆ
    live_output = st.empty()
    live_output.info("چاوەڕێی دەستپێکردنم... ئەنجامەکان ڕاستەوخۆ لێرە دەردەکەون!")

# --- لۆژیکی سەرەکی ---
if st.button("🚀 دەستپێکردنی وەرگێڕانی ڕاستەوخۆ"):
    if not input_srt:
        st.warning("⚠️ تکایە سەرەتا دەقی ژێرنووسەکە دابنێ.")
    else:
        try:
            client_groq = Groq(api_key=groq_key)
            
            # ١. شیکردنەوەی فایلی SRT (جیاکردنەوەی کات لە دەق)
            parsed_srt = parse_srt(input_srt)
            
            # پارچەکردنی فایلەکە (٢٠ دێڕ ٢٠ دێڕ بۆ ئەوەی خێرا بێت و لیمیت تێنەپەڕێنێت)
            chunk_size = 20
            chunks = [parsed_srt[i:i+chunk_size] for i in range(0, len(parsed_srt), chunk_size)]
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            translated_parsed_srt = []
            
            # ٢. دەستپێکردنی پڕۆسەی ڕاستەوخۆ
            for idx, chunk in enumerate(chunks):
                status_text.markdown(f"**⏳ بریکارەکان خەریکن... پارچەی {idx+1} لە {len(chunks)}**")
                
                # دروستکردنی دەقێک بێ کات بۆ ئەوەی تۆکن کەم بخوات
                text_to_translate = ""
                for item in chunk:
                    text_to_translate += f"[{item['id']}]\n{item['text']}\n\n"
                
                prompt_groq = f"""You are a professional cinematic translator. Translate this to Kurdish Sorani.
Rules:
1. ONLY translate the text. Keep the exact format: [ID] followed by translated text on the next line.
2. Glossary: {glossary}

Input:
{text_to_translate}"""
                
                # وەرگرتنی وەرگێڕان
                translated_chunk_text = call_groq(client_groq, prompt_groq)
                
                # شیکردنەوەی ئەنجامەکەی گرۆق و گەڕاندنەوەی بۆ ناو کاتەکانی خۆی
                pattern = r'\[(\d+)\]\n(.*?)(?=\n\[\d+\]|\Z)'
                matches = re.findall(pattern, translated_chunk_text + '\n', re.DOTALL)
                
                # ئاپدەیتکردنی لیستەکەمان
                translated_dict = {m[0]: m[1].strip() for m in matches}
                
                for item in chunk:
                    new_item = item.copy()
                    if item['id'] in translated_dict:
                        new_item['text'] = translated_dict[item['id']]
                    translated_parsed_srt.append(new_item)
                
                # ٣. پیشاندانی ڕاستەوخۆ لەسەر شاشە! (Live Update)
                current_full_srt = build_srt(translated_parsed_srt)
                live_output.code(current_full_srt, language="srt")
                
                progress_bar.progress((idx + 1) / len(chunks))
                
                # پشوو دان بۆ ماوەی ٣ چرکە بۆ ئەوەی گرۆق RateLimit نەدات
                time.sleep(3)

            final_result = current_full_srt

            # ٤. گێمنای (تەنها ئەگەر ڤیدیۆ هەبێت، لێرەدا فایلی تەواوی پێدەدەین بە کاتەکانەوە)
            if video_file:
                try:
                    if not gemini_key:
                        st.warning("⚠️ کلیلەکەی گێمنایت نەداوە! بۆیە بەبێ بینینی ڤیدیۆکە تەنها وەرگێڕانەکەی گرۆقت پێ دەدەم.")
                    else:
                        genai.configure(api_key=gemini_key)
                        model_gemini = genai.GenerativeModel("gemini-1.5-flash")
                        
                        status_text.markdown("**👁️ بریکاری ٥ (Gemini): سەیرکردنی ڤیدیۆکە و هاوکاتکردن...**")
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                            tmp.write(video_file.read())
                            temp_path = tmp.name
                        
                        g_file = genai.upload_file(path=temp_path)
                        while g_file.state.name == "PROCESSING":
                            time.sleep(2)
                            g_file = genai.get_file(g_file.name)
                        
                        # پێدانی کۆدە تەواوەکە بە گێمنای
                        prompt_5 = f"Watch this video. Here is the translated Kurdish SRT. Adjust the subtitles slightly so they perfectly match the visual context and emotions on the screen. Output ONLY the final valid SRT format without any markdown blocks:\n\n{final_result}"
                        
                        r5 = model_gemini.generate_content([g_file, prompt_5])
                        final_result = r5.text
                        os.remove(temp_path)
                        live_output.code(final_result, language="srt")
                        st.success("✅ ڤیدیۆکەش بە سەرکەوتوویی بینرا و ژێرنووسەکە گونجێندرا!")
                
                except Exception as gemini_error:
                    st.error("⚠️ کێشەیەک لە کلیلەکەی گێمنای هەبوو. بەڵام کارەکەی گرۆقت پارێزراوە!")

            status_text.success("🎉 پڕۆسەی وەرگێڕانەکە تەواو بوو!")
            st.balloons()
            
            st.download_button(
                label="📥 داگرتنی فایلی SRT",
                data=final_result,
                file_name="pro_movie.srt",
                mime="text/plain"
            )

        except Exception as e:
            st.error(f"❌ هەڵەیەک ڕوویدا: {str(e)}")
            st.info("💡 کێشەکە پارێزراوە. ئەگەر RateLimit بوو، تکایە کەمێک چاوەڕێ بکە و دووبارە کلیک بکەرەوە.")
