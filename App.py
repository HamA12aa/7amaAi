import streamlit as st
import google.generativeai as genai

# --- ١. ڕێکخستنی سەرەکی لاپەڕە و دیزاین ---
st.set_page_config(page_title="Cinematic AI Translator", page_icon="🍿", layout="wide")

# دیزاینی تایبەت بە CSS بۆ جوانییەکی پرۆفیشناڵ
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;700;900&display=swap');
    
    * { font-family: 'Vazirmatn', sans-serif; direction: rtl; }
    
    /* دیزاینی تایتڵ */
    .title-text {
        text-align: center;
        color: #E50914;
        font-size: 45px;
        font-weight: 900;
        text-shadow: 2px 2px 5px rgba(0,0,0,0.4);
        margin-bottom: 5px;
    }
    .subtitle-text {
        text-align: center;
        color: #999;
        font-size: 18px;
        margin-bottom: 30px;
    }
    
    /* دیزاینی بۆکسەکانی دەق */
    .stTextArea textarea {
        background-color: #1e1e1e;
        color: #ffffff;
        border: 2px solid #333;
        border-radius: 10px;
        font-size: 16px;
        padding: 15px;
    }
    .stTextArea textarea:focus { border: 2px solid #E50914; }
    
    /* دیزاینی دوگمە */
    .stButton button {
        background: linear-gradient(90deg, #E50914 0%, #83060C 100%);
        color: white;
        font-size: 20px;
        font-weight: bold;
        border-radius: 10px;
        border: none;
        width: 100%;
        padding: 15px;
        transition: 0.3s;
    }
    .stButton button:hover {
        transform: scale(1.02);
        box-shadow: 0px 5px 15px rgba(229, 9, 20, 0.4);
    }
    
    /* دیزاینی بۆکسەکانی ئەنجام */
    .success-box {
        background-color: #0b3b24;
        border-right: 5px solid #00ff88;
        padding: 20px;
        border-radius: 10px;
        margin-top: 20px;
        color: white;
        font-size: 18px;
    }
    </style>
""", unsafe_allow_html=True)

# --- ٢. پیشاندانی تایتڵ ---
st.markdown('<div class="title-text">🎬 وەرگێڕی سینەمایی زیرەک</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle-text">نوێترین سیستەمی وەرگێڕانی فیلم بە کوالێتی ستۆدیۆکان (V 3.0)</div>', unsafe_allow_html=True)

# --- ٣. بەشی ڕێکخستنەکان (لەلای ڕاست) ---
with st.sidebar:
    st.header("⚙️ ڕێکخستنەکان")
    api_key = st.text_input("🔑 Google API Key:", type="password")
    
    st.markdown("---")
    st.subheader("فیلمەکە چۆنە؟")
    movie_genre = st.selectbox("🎭 جۆری فیلم:", ["ئاکشن و هەیاهو", "دراما و سۆزداری", "کۆمیدی", "خەیاڵی زانستی", "دۆکیومێنتاری"])
    dialogue_tone = st.selectbox("🗣️ شێوازی قسەکردن:", ["سەر شەقام (Slang/سروشتی)", "فەرمی (ئەدەبی)"])
    
    st.markdown("---")
    st.info("💡 **زانیاری:** ئەم سیستەمە خێراییەکەی دوو هێندە کراوە و لەسەر مۆدێلی Gemini 2.5 Flash کار دەکات بێ سنور.")

# --- ٤. بەشی سەرەکی وەرگێڕان ---
col1, col2 = st.columns([1, 1]) # دوو بەشی یەکسان بۆ شاشە گەورەکان

with col1:
    english_text = st.text_area("🇬🇧 دەقی ئینگلیزی لێرە دابنێ:", height=250, placeholder="وەک: ?What the hell are you doing here")

with col2:
    if st.button("🚀 وەرگێڕان بۆ کوردی"):
        if not api_key:
            st.error("⚠️ تکایە سەرەتا API Key لە لاتەنیشت دابنێ!")
        elif not english_text:
            st.warning("⚠️ تکایە دەقێکی ئینگلیزی بنووسە.")
        else:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')

                # قۆناغی ١: وەرگێڕانی بنەڕەتی بەپێی جۆر و شێواز (Mega Prompt 1)
                with st.spinner("⏳ بریکاری یەکەم خەریکی لێکدانەوەی مانای فیلمەکەیە..."):
                    prompt1 = f"""You are an elite Hollywood movie translator. Translate the following English dialogue to Kurdish Sorani.
                    Context provided by user:
                    - Movie Genre: {movie_genre}
                    - Desired Tone: {dialogue_tone}
                    
                    CRITICAL RULES:
                    1. NEVER translate word-for-word. Capture the exact vibe, emotion, and context of a {movie_genre} movie.
                    2. If it's English slang or an idiom, find the equivalent Kurdish idiom.
                    3. Do not include any explanations, just the translation.
                    
                    English Text: {english_text}"""
                    
                    res1 = model.generate_content(prompt1)
                    raw_translation = res1.text

                # قۆناغی ٢: دەرهێنەری سینەمایی (Mega Prompt 2)
                with st.spinner("🎥 بریکاری دووەم خەریکی ڕێکخستنی سینەمایی و لابردنی هەڵەکانە..."):
                    prompt2 = f"""You are the final Kurdish Subtitle Director. Review this Kurdish translation of an English dialogue.
                    Original English: {english_text}
                    Current Kurdish: {raw_translation}
                    
                    YOUR TASK:
                    1. Polish the Kurdish so it flows perfectly on a movie screen. It MUST sound like natural, everyday Kurdish spoken in Kurdistan.
                    2. Shorten long sentences if possible without losing meaning (perfect for subtitles).
                    3. Fix any grammatical errors (especially pronouns and verb tenses in Sorani).
                    4. ONLY output the final masterpiece Kurdish text. No extra text, no quotes.
                    """
                    
                    res2 = model.generate_content(prompt2)
                    final_kurdish = res2.text

                # پیشاندانی ئەنجامێکی نایاب
                st.markdown(f'<div class="success-box">✅ <b>ئەنجامی پرۆفیشناڵ:</b><br><br>{final_kurdish}</div>', unsafe_allow_html=True)
                st.balloons() # ئاهەنگگێڕانێکی بچووک کاتێک تەواو دەبێت!

            except Exception as e:
                st.error(f"❌ کێشەیەک ڕوویدا: {e}")
    else:
        st.info("👈 ئەنجامەکە لێرە دەردەکەوێت...")
