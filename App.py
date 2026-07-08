import streamlit as st
import google.generativeai as genai
import tempfile
import time
import os
import re
import random

# --- ١. ڕێکخستنی لاپەڕە ---
st.set_page_config(page_title="AI Movie Director PRO | Anti-Limit", layout="wide", page_icon="🎥")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;700&display=swap');
    * { font-family: 'Vazirmatn', sans-serif; }
    .kurdish-font { direction: rtl; text-align: right; }
    .stButton>button { background: linear-gradient(135deg, #4b6cb7 0%, #182848 100%); color: white; font-weight: bold; border-radius: 10px; height: 3.5em; border: none; width: 100%; }
    .slot-status { font-size: 0.8em; padding: 5px; border-radius: 5px; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- ٢. فەنکشنە بنەڕەتییەکان ---
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

# --- ٣. لۆژیکی سەرەکی بانگکردنی AI (بە سیستەمی ئاڵوگۆڕی خێرا) ---
def call_gemini_pro(prompt, all_keys):
    active_keys = [k for k in all_keys if k.strip()]
    if not active_keys:
        raise Exception("تکایە کلیلەکان دابنێ!")

    attempts = 0
    max_attempts = 10 # هەوڵدانەوەی زۆر بۆ دڵنیایی
    
    while attempts < max_attempts:
        # هەڵبژاردنی کلیلێک بە هەڕەمەکی بۆ دابەشکردنی لۆد
        current_key = random.choice(active_keys)
        try:
            genai.configure(api_key=current_key.strip())
            # جێگیرکردنی مۆدێلی فلاش ١.٥ کە لیمیتەکەی باشترە
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg:
                # ئەگەر لیمیت بوو، کەمێک بوەستە و کلیلێکی تر تاقی بکەرەوە
                st.warning(f"⚠️ یەکێک لە کلیلەکان لیمیت بوو، دەچێتە سەر کلیلێکی تر...")
                active_keys.remove(current_key) # کاتی لادانی کلیلە لیمیت بووەکە
                if not active_keys:
                    st.info("😴 هەموو کلیلەکان بۆ کاتێکی کەم لیمیت بوون، ١٠ چرکە دەوەستین...")
                    time.sleep(10)
                    active_keys = [k for k in all_keys if k.strip()] # دووبارە چالاککردنەوەی هەموویان
            else:
                # ئەگەر هەڵەیەکی تر بوو جگە لە لیمیت
                st.error(f"❌ هەڵەیەک لە کلیلدا هەیە: {err_msg[:100]}")
                active_keys.remove(current_key)
        
        attempts += 1
        time.sleep(1)
        
    raise Exception("نەیتوانی وەرگێڕان بکات، تکایە کەمێک چاوەڕێ بکە یان کلیلەکان بگۆڕە.")

# --- ٤. سایدبار ---
with st.sidebar:
    st.title("🎬 پڕۆژەی 7amaAi PRO")
    k1 = st.text_input("Slot 1", type="password", key="s1")
    k2 = st.text_input("Slot 2", type="password", key="s2")
    k3 = st.text_input("Slot 3", type="password", key="s3")
    k4 = st.text_input("Slot 4", type="password", key="s4")
    st.markdown("---")
    glossary = st.text_area("📚 فەرهەنگ", placeholder="ناو یان زاراوەکان...")
    video_file = st.file_uploader("🎥 ڤیدیۆ", type=["mp4"])

# --- ٥. ڕووکاری سەرەکی ---
st.markdown("<h1 style='text-align: center;'>🎥 وەرگێڕی تیمی هۆلیوود (Anti-Limit)</h1>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    input_srt = st.text_area("📥 SRT ئینگلیزی", height=450)
with col2:
    live_box = st.empty()
    live_box.info("ئەنجام لێرە دەردەکەوێت...")

# --- ٦. دەستپێکردنی کار ---
if st.button("🚀 دەستپێکردنی وەرگێڕانی بێ سنوور"):
    all_keys = [k1, k2, k3, k4]
    if not input_srt:
        st.warning("دەق دابنێ.")
    else:
        try:
            parsed = parse_srt(input_srt)
            chunk_size = 15 # بچوککردنەوەی قەبارە بۆ ئەوەی لیمیت نەبێت
            chunks = [parsed[i:i+chunk_size] for i in range(0, len(parsed), chunk_size)]
            
            translated_final = []
            progress = st.progress(0)
            
            for idx, chunk in enumerate(chunks):
                # دروستکردنی پڕۆمپتی بەهێز
                txt_chunk = ""
                for item in chunk:
                    txt_chunk += f"[{item['id']}]\n{item['text']}\n\n"
                
                master_prompt = f"""You are an elite movie translator. Translate to natural Kurdish Sorani.
Format: [ID]
Translated Text
Glossary: {glossary}
ONLY output IDs and Kurdish text.

Input:
{txt_chunk}"""
                
                # بانگکردنی زیرەکی دەستکرد
                res = call_gemini_pro(master_prompt, all_keys)
                
                # جیاکردنەوەی ئەنجامەکان
                matches = re.findall(r'\[(\d+)\]\n(.*?)(?=\n\[\d+\]|\Z)', res + '\n', re.DOTALL)
                res_map = {m[0]: m[1].strip() for m in matches}
                
                for item in chunk:
                    new_item = item.copy()
                    if item['id'] in res_map:
                        new_item['text'] = res_map[item['id']]
                    translated_final.append(new_item)
                
                # نمایش
                live_box.code(build_srt(translated_final), language="srt")
                progress.progress((idx + 1) / len(chunks))
                
                # پشوویەکی کەم بۆ ئەوەی گووگڵ هەست بە فشاری زۆر نەکات
                time.sleep(2)

            final_text = build_srt(translated_final)

            # هاوکاتکردنی ڤیدیۆ
            if video_file:
                st.info("👁️ دەرهێنەری کۆتایی خەریکی هاوکاتکردنە...")
                working_key = random.choice([k for k in all_keys if k.strip()])
                genai.configure(api_key=working_key)
                model_v = genai.GenerativeModel('gemini-1.5-flash')
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                    tmp.write(video_file.read())
                    v_path = tmp.name
                
                g_file = genai.upload_file(path=v_path)
                while g_file.state.name == "PROCESSING":
                    time.sleep(2)
                    g_file = genai.get_file(g_file.name)
                
                v_prompt = f"Sync these Kurdish subtitles with the video scene perfectly. ONLY output final SRT:\n\n{final_text}"
                v_res = model_v.generate_content([g_file, v_prompt])
                final_text = v_res.text.replace("```srt", "").replace("```", "").strip()
                live_box.code(final_text, language="srt")

            st.success("🎉 تەواو بوو!")
            st.download_button("📥 داگرتنی SRT", data=final_text, file_name="translated.srt")

        except Exception as e:
            st.error(f"❌ هەڵە: {str(e)}")
