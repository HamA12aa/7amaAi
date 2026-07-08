import streamlit as st
import google.generativeai as genai
import tempfile
import time
import os
import re
import random

# --- ١. ڕێکخستنی لاپەڕە ---
st.set_page_config(page_title="AI Movie Director PRO | V5.1", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;700&display=swap');
    * { font-family: 'Vazirmatn', sans-serif; direction: rtl; }
    .stTextArea textarea { direction: ltr !important; }
    .log-box { background-color: #f0f2f6; padding: 10px; border-radius: 5px; border-right: 5px solid #4b6cb7; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- ٢. فەنکشنە بنەڕەتییەکان ---
def parse_srt(srt_string):
    # پاککردنەوەی دەقەکە لە کارەکتەری زیادە
    srt_string = srt_string.replace('\r\n', '\n').strip()
    blocks = re.split(r'\n\n', srt_string)
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
    srt_output = ""
    for item in parsed_list:
        srt_output += f"{item['id']}\n{item['time']}\n{item['text']}\n\n"
    return srt_output.strip()

# --- ٣. لۆژیکی بانگکردنی AI ---
def call_gemini_pro(prompt, active_keys, log_placeholder):
    if not active_keys:
        st.error("تکایە لانی کەم یەک کلیلی API دابنێ.")
        return None

    attempts = 0
    while attempts < len(active_keys) * 2:
        current_key = random.choice(active_keys)
        try:
            genai.configure(api_key=current_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            log_placeholder.info(f"🔄 بەکارهێنانی کلیل: {current_key[:8]}***")
            response = model.generate_content(prompt)
            
            if response and response.text:
                return response.text
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg:
                log_placeholder.warning(f"⚠️ کلیلەکە لیمیت بووە، گۆڕین بۆ دانەیەکی تر...")
                time.sleep(2)
            else:
                log_placeholder.error(f"❌ کێشەی تەکنیکی: {err_msg[:50]}")
        
        attempts += 1
    return None

# --- ٤. سایدبار ---
with st.sidebar:
    st.title("⚙️ ڕێکخستنەکان")
    api_inputs = [
        st.text_input("Slot 1", type="password", key="k1"),
        st.text_input("Slot 2", type="password", key="k2"),
        st.text_input("Slot 3", type="password", key="k3"),
        st.text_input("Slot 4", type="password", key="k4")
    ]
    # پاڵاوتنی کلیلەکان تەنها ئەوانەی پڕکراونەتەوە
    active_keys = [k for k in api_inputs if k.strip()]
    
    st.markdown("---")
    glossary = st.text_area("📚 فەرهەنگی تایبەت", placeholder="بۆ نموونە: Batman -> پیاوی شەمشەمەکوێرە")
    video_file = st.file_uploader("🎥 بارکردنی ڤیدیۆ بۆ هاوکاتکردن (ئارەزوومەندانە)", type=["mp4", "mov", "avi"])

# --- ٥. ڕووکاری سەرەکی ---
st.header("🎬 وەرگێڕی فیلم AI Movie Director PRO")

col1, col2 = st.columns(2)
with col1:
    input_srt = st.text_area("📥 SRT ئینگلیزی لێرە دابنێ", height=400)
with col2:
    status_log = st.empty()
    live_preview = st.empty()

# --- ٦. پڕۆسەی وەرگێڕان ---
if st.button("🚀 دەستپێکردنی وەرگێڕانی سینەمایی"):
    if not input_srt:
        st.error("تکایە دەقی SRT دابنێ.")
    elif not active_keys:
        st.error("تکایە کلیلەکانی API لە سایدبارەکە دابنێ.")
    else:
        try:
            parsed_data = parse_srt(input_srt)
            total_blocks = len(parsed_data)
            chunk_size = 10  # قەبارەی هەر پارچەیەک بۆ پاراستنی کوالێتی
            
            translated_final = []
            progress_bar = st.progress(0)
            
            for i in range(0, total_blocks, chunk_size):
                chunk = parsed_data[i : i + chunk_size]
                
                # ئامادەکردنی دەق بۆ AI
                prompt_text = ""
                for item in chunk:
                    prompt_text += f"ID: {item['id']}\nTEXT: {item['text']}\n\n"
                
                master_prompt = f"""
                You are a professional movie translator (Linguist & Scriptwriter).
                Translate the following movie subtitles into Central Kurdish (Sorani).
                
                RULES:
                1. Preserve the ID for each line.
                2. Use natural, cinematic Sorani Kurdish.
                3. Glossary: {glossary}
                4. Output format MUST be:
                   ID: [number]
                   KURDISH: [translation]
                
                CONTENT:
                {prompt_text}
                """
                
                # بانگکردنی زیرەکی دەستکرد
                response_text = call_gemini_pro(master_prompt, active_keys, status_log)
                
                if response_text:
                    # پارس کردنی وەڵامەکە بە وردی
                    for item in chunk:
                        # دۆزینەوەی وەرگێڕانەکە بەپێی ID
                        pattern = rf"ID:\s*{item['id']}\nKURDISH:\s*(.*?)(?=ID:|\Z)"
                        match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
                        
                        new_item = item.copy()
                        if match:
                            new_item['text'] = match.group(1).strip()
                        else:
                            # ئەگەر AI هەڵەی کرد، دەقە ئەسڵییەکە بپارێزە
                            new_item['text'] = item['text'] 
                        
                        translated_final.append(new_item)
                
                # نوێکردنەوەی پێشاندان
                current_srt = build_srt(translated_final)
                live_preview.code(current_srt, language="srt")
                progress_bar.progress(min((i + chunk_size) / total_blocks, 1.0))
                
                time.sleep(1) # پشوو بۆ ڕێگری لە بلۆک بوون

            st.success("✅ وەرگێڕان بە سەرکەوتوویی تەواو بوو!")
            st.download_button("📥 داگرتنی فایلی کۆتایی", data=build_srt(translated_final), file_name="kurdish_subtitles.srt")

        except Exception as e:
            st.error(f"❌ کێشەیەک لە کاتی کارکردن ڕوویدا: {str(e)}")
