import streamlit as st
import google.generativeai as genai
import tempfile
import time
import os
import re
import random

# --- ١. ڕێکخستنی لاپەڕە ---
st.set_page_config(page_title="AI Movie Director PRO | 4-Slot Edition", layout="wide", page_icon="🎥")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;700&display=swap');
    * { font-family: 'Vazirmatn', sans-serif; }
    .kurdish-font { direction: rtl; text-align: right; }
    .stButton>button { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; font-weight: bold; border-radius: 10px; height: 3.5em; border: none; width: 100%; }
    .slot-label { color: #f39c12; font-weight: bold; margin-bottom: -10px; }
    </style>
""", unsafe_allow_html=True)

# --- ٢. فەنکشنەکانی شیکردنەوەی دەق ---
def parse_srt(srt_string):
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
    return '\n\n'.join([f"{item['id']}\n{item['time']}\n{item['text']}" for item in parsed_list])

# --- ٣. سیستەمی ئاڵوگۆڕی ٤ کلیلەکە ---
def call_gemini_safe(prompt, keys):
    valid_keys = [k for k in keys if k.strip()]
    if not valid_keys:
        raise Exception("تکایە کلیلەکان لە سڵۆتەکاندا دابنێ!")
    
    random.shuffle(valid_keys)
    last_err = ""
    
    # تاقیکردنەوەی چەند فۆرماتێکی ناوی مۆدێل بۆ ڕێگری لە 404
    model_names = ["gemini-1.5-flash", "models/gemini-1.5-flash", "gemini-1.5-flash-latest"]
    
    for key in valid_keys:
        for m_name in model_names:
            try:
                genai.configure(api_key=key.strip())
                model = genai.GenerativeModel(model_name=m_name)
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                last_err = str(e)
                if "404" in last_err:
                    continue # ئەگەر 404 بوو مۆدێلی دوواتر تاقی بکەرەوە
                else:
                    break # ئەگەر هەڵەیەکی تر بوو بڕۆ سەر کلیلی دوواتر
    
    raise Exception(f"⚠️ کێشە لە کلیلەکاندا هەیە: {last_err}")

# --- ٤. سایدبار ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/8/8a/Google_Gemini_logo.svg", width=100)
    st.title("🎬 بەڕێوبەری کلیلەکان")
    
    st.markdown("<p class='slot-label'>Slot 1</p>", unsafe_allow_html=True)
    key1 = st.text_input("", type="password", key="k1", placeholder="AIzaSy...")
    
    st.markdown("<p class='slot-label'>Slot 2</p>", unsafe_allow_html=True)
    key2 = st.text_input("", type="password", key="k2", placeholder="AIzaSy...")
    
    st.markdown("<p class='slot-label'>Slot 3</p>", unsafe_allow_html=True)
    key3 = st.text_input("", type="password", key="k3", placeholder="AIzaSy...")
    
    st.markdown("<p class='slot-label'>Slot 4</p>", unsafe_allow_html=True)
    key4 = st.text_input("", type="password", key="k4", placeholder="AIzaSy...")
    
    st.markdown("---")
    glossary = st.text_area("📚 فەرهەنگی ناوی کارەکتەرەکان", placeholder="John = جۆن")
    video_file = st.file_uploader("🎬 بارکردنی ڤیدیۆ:", type=["mp4"])

# --- ٥. ڕووکاری سەرەکی ---
st.markdown("<h1 style='text-align: center;'>🎥 وەرگێڕی ٤-سڵۆتی بلیمەت</h1>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.markdown("<h3 class='kurdish-font'>📥 دەقی ئینگلیزی</h3>", unsafe_allow_html=True)
    input_srt = st.text_area("", height=450, label_visibility="collapsed")

with col2:
    st.markdown("<h3 class='kurdish-font'>📤 وەرگێڕانی ڕاستەوخۆ</h3>", unsafe_allow_html=True)
    live_box = st.empty()
    live_box.info("چاوەڕێی کلیلەکان و دەقەکەم...")

# --- ٦. لۆژیکی کارپێکردن ---
if st.button("🚀 دەستپێکردنی وەرگێڕان"):
    active_keys = [key1, key2, key3, key4]
    
    if not any(active_keys):
        st.error("⚠️ تکایە لانی کەم یەک کلیل دابنێ.")
    elif not input_srt:
        st.warning("⚠️ دەقی ژێرنووسەکە دابنێ.")
    else:
        try:
            parsed_data = parse_srt(input_srt)
            chunk_size = 20
            chunks = [parsed_data[i:i+chunk_size] for i in range(0, len(parsed_data), chunk_size)]
            
            progress = st.progress(0)
            status = st.empty()
            translated_data = []
            
            for idx, chunk in enumerate(chunks):
                status.markdown(f"**⚡ وەرگێڕانی پارچەی {idx+1} لە {len(chunks)}...**")
                
                prompt_text = ""
                for item in chunk:
                    prompt_text += f"[{item['id']}]\n{item['text']}\n\n"
                
                master_prompt = f"""You are a professional movie translator. Translate the text below to natural Kurdish Sorani.
Rules:
1. Format: [ID] followed by translated Kurdish text.
2. Glossary: {glossary}
3. Maintain the IDs. ONLY output IDs and translations. No chat.

Input:
{prompt_text}"""
                
                translated_chunk = call_gemini_safe(master_prompt, active_keys)
                
                matches = re.findall(r'\[(\d+)\]\n(.*?)(?=\n\[\d+\]|\Z)', translated_chunk + '\n', re.DOTALL)
                result_map = {m[0]: m[1].strip() for m in matches}
                
                for item in chunk:
                    new_item = item.copy()
                    if item['id'] in result_map:
                        new_item['text'] = result_map[item['id']]
                    translated_data.append(new_item)
                
                current_srt = build_srt(translated_data)
                live_box.code(current_srt, language="srt")
                progress.progress((idx + 1) / len(chunks))
                
                # ئەگەر تەنها یەک کلیل هەبێت کەمێک پشوو بدە بۆ پاراستنی Rate Limit
                if len([k for k in active_keys if k.strip()]) == 1:
                    time.sleep(3)
                else:
                    time.sleep(0.5)

            final_srt = current_srt

            if video_file:
                status.info("👁️ دەرهێنەری ڤیدیۆ: خەریکی هاوکاتکردنی دیمەنەکانە...")
                # بەکارهێنانی یەکێک لە کلیلەکان بۆ ڤیدیۆ
                genai.configure(api_key=[k for k in active_keys if k.strip()][0])
                model_v = genai.GenerativeModel("gemini-1.5-flash")
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                    tmp.write(video_file.read())
                    v_path = tmp.name
                
                g_file = genai.upload_file(path=v_path)
                while g_file.state.name == "PROCESSING":
                    time.sleep(2)
                    g_file = genai.get_file(g_file.name)
                
                prompt_v = f"Watch the video and adjust this Kurdish SRT text to match scenes perfectly. ONLY output final SRT:\n\n{final_srt}"
                res_v = model_v.generate_content([g_file, prompt_v])
                final_srt = res_v.text.replace("```srt", "").replace("```", "").strip()
                os.remove(v_path)
                live_box.code(final_srt, language="srt")

            status.success("🎉 وەرگێڕان تەواو بوو!")
            st.balloons()
            st.download_button("📥 داگرتنی فایلی SRT", data=final_srt, file_name="translated.srt")

        except Exception as e:
            st.error(f"❌ هەڵەیەک ڕوویدا: {str(e)}")
