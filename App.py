import streamlit as st
import google.generativeai as genai
import time

# --- دیزاینی لاپەڕە ---
st.set_page_config(page_title="وەرگێڕی زیرەکی کوردی", page_icon="🎬", layout="centered")

st.markdown("""
    <style>
    .stTextArea textarea { text-align: right; direction: rtl; }
    .stMarkdown { text-align: right; direction: rtl; }
    </style>
    """, unsafe_allow_status=True)

st.title("سیستەمی ٤-قۆناغی بۆ وەرگێڕانی فیلم")
st.write("ئەم سایتە Gemini 1.5 Flash بەکاردەهێنێت بۆ وەرگێڕانێکی ورد")

# --- وەرگرتنی کلیل ---
api_key = st.sidebar.text_input("Google API Key دابنێ", type="password")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    english_text = st.text_area("دەقی ئینگلیزی لێرە دابنێ:", height=200)

    if st.button("دەستپێکردنی وەرگێڕان"):
        if english_text:
            try:
                # قۆناغی ١: وەرگێڕی ڕاستەوخۆ
                with st.status("١. وەرگێڕان لە ئینگلیزییەوە بۆ کوردی...") as s:
                    p1 = f"Translate the following English movie dialogue to Kurdish Sorani accurately: {english_text}"
                    res1 = model.generate_content(p1)
                    trans1 = res1.text
                    s.update(label="قۆناغی ١ تەواو بوو", state="complete")

                # قۆناغی ٢: ڕێکخەری کلتووری و زمانەوانی
                with st.status("٢. چاککردنی شێوازی دەربڕین و ڕێزمان...") as s:
                    p2 = f"Review this Kurdish translation. Make it sound like natural spoken Kurdish used in movies, not literal translation: {trans1}"
                    res2 = model.generate_content(p2)
                    trans2 = res2.text
                    s.update(label="قۆناغی ٢ تەواو بوو", state="complete")

                # قۆناغی ٣: کورتکەرەوە بۆ ژێرنووس
                with st.status("٣. گونجاندن بۆ قەبارەی ژێرنووس (Subtitle Formatting)...") as s:
                    p3 = f"Shorten these Kurdish sentences so they fit on a screen as subtitles, but keep the full meaning: {trans2}"
                    res3 = model.generate_content(p3)
                    trans3 = res3.text
                    s.update(label="قۆناغی ٣ تەواو بوو", state="complete")

                # قۆناغی ٤: پیاچوونەوەی کۆتایی و هەڵەبڕی
                with st.status("٤. پیاچوونەوەی کۆتایی و دڵنیابوونەوە لە مانا...") as s:
                    p4 = f"Final check: Compare the original English with this Kurdish version. If there's any loss of meaning, fix it now: \nEnglish: {english_text} \nKurdish: {trans3}"
                    res4 = model.generate_content(p4)
                    final_result = res4.text
                    s.update(label="هەموو قۆناغەکان بەسەرکەوتوویی تەواو بوون", state="complete")

                st.subheader("ئەنجامی کۆتایی:")
                st.text_area("", final_result, height=250)
                st.success("وەرگێڕان ئامادەیە!")
                
            except Exception as e:
                st.error(f"هەڵەیەک ڕوویدا: {e}")
        else:
            st.warning("تکایە دەقێک داخڵ بکە.")
else:
    st.info("تکایە لە لای چەپ کلیلەکە (API Key) داخڵ بکە. ئەگەر نەتەوێت هەموو جارێک دایبنێیت، دەتوانرێت لە ڕێکخستنی سایتەکە جێگیر بکرێت.")
