import streamlit as st
import google.generativeai as genai
import tempfile
import time
import os
import re
import random

# --- ١. ڕێکخستنی لاپەڕە و ستایل ---
st.set_page_config(page_title="AI Movie Director PRO | Full Edition", layout="wide", page_icon="🎥")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;700&display=swap');
    * { font-family: 'Vazirmatn', sans-serif; }
    .kurdish-font { direction: rtl; text-align: right; }
    .stButton>button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-weight: bold; border-radius: 10px; height: 3.5em; border: none; width: 100%; font-size: 16px; }
    .slot-label { color: #58a6ff; font-weight: bold; margin-bottom: -15px; font-size: 14px; }
    .status-box { padding: 12px; border-radius: 8px; background-color: #1c2128; color: #c9d1d9; border-left: 5px solid #2ea043; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- ٢. فەنکشنەکانی شیکردنەوەی SRT (بۆ پاراستنی تۆکن) ---
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

# --- ٣. سیستەمی ئاڵوگۆڕی ٤ کلیلەکە (Load Balancer) ---
def call_gemini_safe(prompt, keys):
    valid_keys = [k for k in keys if k.strip()]
    if not valid_keys:
        raise Exception("تکایە لانی کەم کلیلێک لە سڵۆتەکان دابنێ!")
    
    random.shuffle(valid_keys)
    last_err = ""
    
    # تاقیکردنەوەی ناوە جیاوازەکانی مۆدێل بۆ ڕێگری لە 404
    model_names = ["gemini-1.5-flash", "models/gemini-1.5-flash"]
    
    for key in valid_keys:
        for m_name in model_names:
            try:
                genai.configure(api_key=key.strip())
                model = genai.GenerativeModel(m_name)
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                last_err = str(e)
                if "404" in last_err:
                    continue # ئەگەر 404 بوو ناوی دووەم تاقی دەکاتەوە
                else:
                    break # ئەگەر هەڵەیەکی تر بوو (وەک لیمیت) دەچێتە سەر کلیلی دواتر
    
    raise Exception(f"⚠️ هەڵە لە کلیلەکان: {last_err}")

# --- ٤. سایدبار (٤ سڵۆتی جیاواز + فەرهەنگ + ڤیدیۆ) ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/8/8a/Google_Gemini_logo.svg", width=100)
    st.title("🎬 Directors Control")
    
    st.markdown("<p class='slot-label'>API Slot 1</p>", unsafe_allow_html=True)
    key1 = st.text_input("", type="password", key="s1")
    
    st.markdown("<p class='slot-label'>API Slot 2</p>", unsafe_allow_html=True)
    key2 = st.text_input("", type="password", key="s2")
    
    st.markdown("<p class='slot-label'>API Slot 3</p>", unsafe_allow_html=True)
    key3 = st.text_input("", type="password", key="s3")
    
    st.markdown("<p class='slot-label'>API Slot 4</p>", unsafe_allow_html=True)
    key4 = st.text_input("", type="password", key="s4")
    
    st.markdown("---")
    glossary = st.text_area("📚 فەرهەنگی تایبەت (Glossary)", placeholder="John = جۆن")
    video_file = st.file_uploader("🎬 بارکردنی ڤیدیۆ (بۆ بریکاری ٥):", type=["mp4", "mov"])

# --- ٥. ڕووکاری سەرەکی ---
st.markdown("<h1 style='text-align: center;'>🎥 وەرگێڕی سینەمایی ٥-ئەفسەری PRO</h1>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.markdown("<h3 class='kurdish-font'>📥 دەقی ئینگلیزی (SRT)</h3>", unsafe_allow_html=True)
    input_srt = st.text_area("", height=500, label_visibility="collapsed")

with col2:
    st.markdown("<h3 class='kurdish-font'>📤 ئەنجامی ڕاستەوخۆ (Live)</h3>", unsafe_allow_html=True)
    live_box = st.empty()
    live_box.info("ئامادەم بۆ وەرگێڕان...")

# --- ٦. لۆژیکی وەرگێڕان (تیمی هۆلیوود و ٥ بریکارەکە) ---
if st.button("🚀 دەستپێکردنی وەرگێڕانی 10x PRO"):
    active_keys = [key1, key2, key3, key4]
    
    if not any(active_keys):
        st.error("⚠️ تکایە لانی کەم یەک کلیل لە سڵۆتەکاندا دابنێ.")
    elif not input_srt:
        st.warning("⚠️ تکایە دەقی ژێرنووسەکە دابنێ.")
    else:
        try:
            parsed_data = parse_srt(input_srt)
            chunk_size = 20 # ٢٠ دێڕ ٢٠ دێڕ بۆ باشترین کوالێتی
            chunks = [parsed_data[i:i+chunk_size] for i in range(0, len(parsed_data), chunk_size)]
            
            progress = st.progress(0)
            status = st.empty()
            translated_data = []
            
            for idx, chunk in enumerate(chunks):
                status.markdown(f"<div class='status-box'>⚡ تیمی هۆلیوود لە کاردایە... پارچەی {idx+1} لە {len(chunks)}</div>", unsafe_allow_html=True)
                
                # ئامادەکردنی دەقی پارچەکە بەبێ کاتەکان
                prompt_text = ""
                for item in chunk:
                    prompt_text += f"[{item['id']}]\n{item['text']}\n\n"
                
                # بریکارەکانی ١، ٢، ٣، ٤ لە ناو یەک پڕۆمپتی زەبەلاحدا
                master_prompt = f"""You are an elite Hollywood Localization Team (Linguist, Writer, and Editor).
Task: Translate these subtitles to perfect natural Kurdish Sorani.
Rules:
1. Format: [ID] followed by translated text.
2. Use this glossary: {glossary}
3. Role 1 (Linguist): Ensure perfect English-to-Kurdish meaning.
4. Role 2 (Writer): Make it sound like a natural movie dialogue, not a literal translation.
5. Role 3 (Editor): Strict SRT-style structure maintenance.
ONLY output IDs and Kurdish text.

Subtitles:
{prompt_text}"""
                
                # بانگکردنی زیرەکی دەستکرد
                translated_chunk = call_gemini_safe(master_prompt, active_keys)
                
                # جیاکردنەوەی ئەنجامەکان و گەڕاندنەوەیان بۆ ناو کاتەکان
                matches = re.findall(r'\[(\d+)\]\n(.*?)(?=\n\[\d+\]|\Z)', translated_chunk + '\n', re.DOTALL)
                result_map = {m[0]: m[1].strip() for m in matches}
                
                for item in chunk:
                    new_item = item.copy()
                    if item['id'] in result_map:
                        new_item['text'] = result_map[item['id']]
                    translated_data.append(new_item)
                
                # پیشاندانی ڕاستەوخۆ (Live Stream)
                current_srt = build_srt(translated_data)
                live_box.code(current_srt, language="srt")
                progress.progress((idx + 1) / len(chunks))
                
                # ئەگەر تەنها یەک کلیل هەبێت، کەمێک وەستان بۆ Rate Limit
                if len([k for k in active_keys if k]) == 1:
                    time.sleep(3)
                else:
                    time.sleep(1)

            final_srt = current_srt

            # بریکاری ٥: دەرهێنەری ڤیدیۆ (Gemini Vision)
            if video_file:
                status.markdown("<div class='status-box' style='border-left-color: #f39c12;'>👁️ بریکاری ٥ (دەرهێنەر): سەیری ڤیدیۆکە دەکات بۆ هاوکاتکردنی کۆتایی...</div>", unsafe_allow_html=True)
                
                # بەکارهێنانی مۆدێلی Pro ئەگەر هەبێت، یان Flash بۆ بینینی ڤیدیۆ
                genai.configure(api_key=[k for k in active_keys if k][0])
                model_v = genai.GenerativeModel("gemini-1.5-flash")
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                    tmp.write(video_file.read())
                    v_path = tmp.name
                
                g_file = genai.upload_file(path=v_path)
                while g_file.state.name == "PROCESSING":
                    time.sleep(2)
                    g_file = genai.get_file(g_file.name)
                
                prompt_v = f"Watch this video and adjust this Kurdish SRT to match the actors emotions and lips perfectly. Output ONLY the SRT:\n\n{final_srt}"
                res_v = model_v.generate_content([g_file, prompt_v])
                final_srt = res_v.text.replace("```srt", "").replace("```", "").strip()
                os.remove(v_path)
                live_box.code(final_srt, language="srt")

            status.markdown("<div class='status-box' style='border-left-color: #3498db;'>🎉 وەرگێڕانی تیمی هۆلیوود تەواو بوو!</div>", unsafe_allow_html=True)
            st.balloons()
            st.download_button("📥 داگرتنی فایلی SRT", data=final_srt, file_name="translated_pro.srt")

        except Exception as e:
            st.error(f"❌ هەڵەیەک ڕوویدا: {str(e)}")
