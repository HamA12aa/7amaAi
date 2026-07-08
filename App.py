import streamlit as st
import google.generativeai as genai
import tempfile
import time
import os
import re
import random

# --- ١. ڕێکخستنی لاپەڕە و دیزاینی پڕۆفیشناڵ ---
st.set_page_config(page_title="AI Movie Director PRO | 10x Edition", layout="wide", page_icon="🎥")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;700&display=swap');
    * { font-family: 'Vazirmatn', sans-serif; }
    .stTextArea textarea { direction: ltr !important; text-align: left !important; background-color: #0d1117; color: #58a6ff; font-family: monospace; border: 1px solid #30363d; }
    .kurdish-font { direction: rtl; text-align: right; }
    .stButton>button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-weight: bold; border-radius: 10px; height: 3em; font-size: 18px; transition: 0.3s; border: none; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.3); }
    .status-box { padding: 10px; border-radius: 8px; background-color: #1c2128; color: #c9d1d9; border-left: 5px solid #2ea043; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- ٢. فەنکشنەکانی ئەندازیاری دەق (پاراستنی تۆکن و فۆرمات) ---
def parse_srt(srt_string):
    """کاتەکان لادەبات بۆ ئەوەی AI سەرلێشێواو نەبێت و تۆکن کەمتر بخوات"""
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
    """کاتەکان بە دروستی دەخاتەوە سەر دەقە وەرگێڕدراوەکە"""
    return '\n\n'.join([f"{item['id']}\n{item['time']}\n{item['text']}" for item in parsed_list])

# --- ٣. سیستەمی دابەشکاری بار (Load Balancer) ---
def call_gemini_with_keys(prompt, keys_list):
    """گۆڕینی زیرەکانەی کلیلەکان بۆ پاراستنی خێرایی و ڕێگری لە بلۆکبوون"""
    random.shuffle(keys_list)
    last_error = ""
    
    for key in keys_list:
        try:
            genai.configure(api_key=key.strip())
            # بەکارهێنانی مۆدێلی نوێی فلاش کە بۆ تێکست زۆر خێرایە
            model = genai.GenerativeModel("gemini-1.5-flash") 
            response = model.generate_content(prompt, request_options={"timeout": 60})
            return response.text
        except Exception as e:
            last_error = str(e)
            continue
            
    raise Exception(f"⚠️ هەموو کلیلەکان لیمیت کراون یان هەڵەن! دوایین کێشە: {last_error}")

# --- ٤. سایدبار (بێ کلیلە سەیڤکراوەکان بۆ پاراستنی ئاسایش) ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/8/8a/Google_Gemini_logo.svg", width=120)
    st.title("⚙️ ژووری کۆنترۆڵ (Directors Room)")
    
    st.warning("🔒 بۆ پاراستنی ئاسایش، کلیلەکانت لە گیتھەب مەهێڵەوە.")
    gemini_keys_input = st.text_area(
        "🔑 کلیلەکانی Google Gemini لێرە دابنێ:", 
        placeholder="AIzaSy..., AIzaSy...", 
        help="چەند کلیلێکت هەیە بە فاریزە (,) جیایان بکەرەوە بۆ ئەوەی خێراییەکەی ببێتە موشەک."
    )
    
    st.markdown("---")
    glossary = st.text_area("📚 فەرهەنگی کارەکتەرەکان", placeholder="John = جۆن\nMatrix = مەیتریکس")
    st.markdown("---")
    video_file = st.file_uploader("🎬 بارکردنی ڤیدیۆ (بۆ دەرهێنەری کۆتایی):", type=["mp4", "mov"])

# --- ٥. ڕووکاری سەرەکی ---
st.markdown("<h1 style='text-align: center; color: #c9d1d9;'>🎥 وەرگێڕی سینەمایی بلیمەت (10x PRO Edition)</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8b949e;'>بەهێزکراو بە ژیری تیمی هۆلیوود و سیستەمی ئاڵوگۆڕی کلیلەکان</p>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.markdown("<h3 class='kurdish-font'>📥 دەقی ئینگلیزی (SRT)</h3>", unsafe_allow_html=True)
    input_srt = st.text_area("", height=500, label_visibility="collapsed", placeholder="فایلی ژێرنووسەکەت لێرە دابنێ...")

with col2:
    st.markdown("<h3 class='kurdish-font'>📤 پەخشی ڕاستەوخۆ (Live Stream)</h3>", unsafe_allow_html=True)
    live_output = st.empty()
    live_output.info("چاوەڕێی فەرمانی دەستپێکردنم...")

# --- ٦. لۆژیکی سەرەکی و پڕۆمپتە سیحرییەکان ---
if st.button("🚀 ئەکشن! (دەستپێکردنی وەرگێڕان)"):
    keys_list = [k.strip() for k in gemini_keys_input.split(",") if k.strip()]
    
    if not input_srt:
        st.warning("⚠️ تکایە سەرەتا دەقی ژێرنووسەکە دابنێ.")
    elif not keys_list:
        st.error("⚠️ تکایە بەلانی کەمەوە یەک کلیلی Gemini دابنێ.")
    else:
        try:
            parsed_srt = parse_srt(input_srt)
            # زیادکردنی قەبارەی پارچەکان بۆ 20 لەبەر ئەوەی پڕۆمپتەکەمان زۆر زیرەکترە
            chunk_size = 20
            chunks = [parsed_srt[i:i+chunk_size] for i in range(0, len(parsed_srt), chunk_size)]
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            translated_parsed_srt = []
            
            # --- قۆناغی ١: تیمی وەرگێڕانی دەق ---
            for idx, chunk in enumerate(chunks):
                status_text.markdown(f"<div class='status-box'>⏳ تیمی هۆلیوود لە کاردان... (پارچەی {idx+1} لە کۆی {len(chunks)})</div>", unsafe_allow_html=True)
                
                text_to_translate = ""
                for item in chunk:
                    text_to_translate += f"[{item['id']}]\n{item['text']}\n\n"
                
                # پڕۆمپتی ١٠ هێندە بەهێزکراو (The 10x Master Prompt)
                prompt_gemini = f"""You are an elite Hollywood Localization Team translating subtitles to Kurdish Sorani.
Your team consists of 3 distinct roles working simultaneously:
1. The Linguist: Ensures 100% accurate meaning from English.
2. The Cinematic Writer: Adapts the dialogue to sound like a natural, dramatic, and authentic Kurdish movie (using pure Sorani vocabulary, avoiding literal weird translations).
3. The Editor: Ensures the formatting is strictly maintained.

CRITICAL RULES:
- Output MUST be exactly in this format: [ID] followed by the Kurdish text on the next line.
- DO NOT output any introductions, markdown formatting (like ```), or explanations. ONLY the IDs and translated text.
- If a sentence continues from a previous line, make sure the grammatical flow in Kurdish is natural.
- Mandatory Glossary to respect: {glossary}

Input Subtitles to Translate:
{text_to_translate}"""
                
                translated_chunk_text = call_gemini_with_keys(prompt_gemini, keys_list)
                
                # دۆزینەوەی دەقەکان بە وردی
                pattern = r'\[(\d+)\]\n(.*?)(?=\n\[\d+\]|\Z)'
                matches = re.findall(pattern, translated_chunk_text + '\n', re.DOTALL)
                translated_dict = {m[0]: m[1].strip() for m in matches}
                
                for item in chunk:
                    new_item = item.copy()
                    if item['id'] in translated_dict:
                        new_item['text'] = translated_dict[item['id']]
                    translated_parsed_srt.append(new_item)
                
                current_full_srt = build_srt(translated_parsed_srt)
                live_output.code(current_full_srt, language="srt")
                progress_bar.progress((idx + 1) / len(chunks))
                
                # سیستەمی پشوودانی زیرەک بەپێی ژمارەی کلیلەکان
                if len(keys_list) == 1:
                    time.sleep(4)
                else:
                    time.sleep(1)

            final_result = current_full_srt

            # --- قۆناغی ٢: دەرهێنەری ڤیدیۆ (Gemini Vision) ---
            if video_file:
                status_text.markdown("<div class='status-box' style='border-left-color: #f39c12;'>👁️ دەرهێنەر خەریکی بینینی ڤیدیۆکەیە بۆ هاوکاتکردنی (Sync) کۆتایی...</div>", unsafe_allow_html=True)
                
                genai.configure(api_key=keys_list[0])
                model_gemini = genai.GenerativeModel("gemini-1.5-pro") # بەکارهێنانی Pro بۆ بینینی ڤیدیۆ چونکە زیرەکترە
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                    tmp.write(video_file.read())
                    temp_path = tmp.name
                
                # بارکردن بۆ سێرڤەری گووگڵ
                g_file = genai.upload_file(path=temp_path)
                while g_file.state.name == "PROCESSING":
                    time.sleep(2)
                    g_file = genai.get_file(g_file.name)
                
                # پڕۆمپتی دەرهێنەر (The Director Prompt)
                prompt_vision = f"""You are an Academy Award-winning Film Director and Subtitle Synchronizer.
I have provided a video clip and its translated Kurdish Sorani SRT subtitles.
Your tasks:
1. Watch the video, observing the actors' emotions, lip movements, and scene transitions.
2. Adjust the timing (timestamps) or slightly tweak the Kurdish text so it fits perfectly with the visual context and audio length.
3. You MUST output ONLY the finalized, valid SRT text. Do NOT wrap it in markdown block quotes.

Draft SRT Subtitles:
{final_result}"""
                
                vision_response = model_gemini.generate_content([g_file, prompt_vision])
                # سڕینەوەی ماڕکداون ئەگەر AI بە هەڵە داینابوو
                clean_vision_text = vision_response.text.replace("```srt", "").replace("```", "").strip()
                final_result = clean_vision_text
                
                os.remove(temp_path)
                live_output.code(final_result, language="srt")
                st.success("✅ دەرهێنەر ڤیدیۆکەی پەسەند کرد! ژێرنووسەکە بە تەواوی گونجێندرا.")

            status_text.markdown("<div class='status-box' style='border-left-color: #3498db;'>🎉 پڕۆسەی وەرگێڕانی سینەمایی بە سەرکەوتوویی تەواو بوو!</div>", unsafe_allow_html=True)
            st.balloons()
            
            st.download_button(
                label="📥 داگرتنی فایلی SRT (بە کوالێتی هۆلیوود)",
                data=final_result,
                file_name="Hollywood_Movie_Kurdish.srt",
                mime="text/plain"
            )

        except Exception as e:
            st.error(f"❌ هەڵەیەک ڕوویدا: {str(e)}")
            st.info("💡 تکایە دڵنیابە لەوەی کلیلەکانت ڕاستن، یان کەمێک چاوەڕێ بکە ئەگەر فشاری زۆر لەسەر سێرڤەرەکان بێت.")
