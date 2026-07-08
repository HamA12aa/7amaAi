import streamlit as st
import google.generativeai as genai

# --- ڕێکخستنی لاپەڕە ---
st.set_page_config(page_title="وەرگێڕی زیرەکی کوردی", page_icon="🎬", layout="centered")

# --- چاککردنی دیزاین (ڕاستکردنەوەی هەڵەکە بۆ unsafe_allow_html) ---
st.markdown("""
    <style>
    .stTextArea textarea { text-align: right; direction: rtl; }
    .stMarkdown, p, h1, h2, h3 { text-align: right; direction: rtl; font-family: Arial, sans-serif; }
    </style>
    """, unsafe_allow_html=True)

st.title("سیستەمی ٤-قۆناغی بۆ وەرگێڕانی فیلم 🎬")
st.write("بەهێزترین سیستەم بە بەکارهێنانی Gemini 1.5 Flash بۆ وەرگێڕانی دروست و سروشتی.")

# --- وەرگرتنی کلیل لە لاتەنیشت ---
api_key = st.sidebar.text_input("🔑 Google API Key لێرە دابنێ:", type="password")
st.sidebar.markdown("بۆ بەدەستهێنانی کلیل بڕۆ بۆ [Google AI Studio](https://aistudio.google.com/)")

if api_key:
    # چالاککردنی زیرەکی دەستکرد
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    # وەرگرتنی دەق
    english_text = st.text_area("📝 دەقی ئینگلیزی (SRT یان گفتوگۆ) لێرە دابنێ:", height=200)

    if st.button("🚀 دەستپێکردنی وەرگێڕان"):
        if english_text:
            try:
                # قۆناغی ١
                with st.status("١. وەرگێڕان لە ئینگلیزییەوە بۆ کوردی...") as s:
                    p1 = f"Translate the following English movie dialogue to Kurdish Sorani accurately: {english_text}"
                    res1 = model.generate_content(p1)
                    trans1 = res1.text
                    s.update(label="✅ قۆناغی ١ تەواو بوو", state="complete")

                # قۆناغی ٢
                with st.status("٢. چاککردنی شێوازی دەربڕین و ڕێزمان...") as s:
                    p2 = f"Review this Kurdish translation. Make it sound like natural spoken Kurdish used in movies, not literal translation: {trans1}"
                    res2 = model.generate_content(p2)
                    trans2 = res2.text
                    s.update(label="✅ قۆناغی ٢ تەواو بوو", state="complete")

                # قۆناغی ٣
                with st.status("٣. گونجاندن بۆ قەبارەی ژێرنووس...") as s:
                    p3 = f"Shorten these Kurdish sentences so they fit on a screen as subtitles, but keep the full meaning: {trans2}"
                    res3 = model.generate_content(p3)
                    trans3 = res3.text
                    s.update(label="✅ قۆناغی ٣ تەواو بوو", state="complete")

                # قۆناغی ٤
                with st.status("٤. پیاچوونەوەی کۆتایی...") as s:
                    p4 = f"Final check: Compare the original English with this Kurdish version. Fix any meaning errors. ONLY output the final Kurdish text without any extra chat: \nEnglish: {english_text} \nKurdish: {trans3}"
                    res4 = model.generate_content(p4)
                    final_result = res4.text
                    s.update(label="✅ هەموو قۆناغەکان بەسەرکەوتوویی تەواو بوون!", state="complete")

                # پیشاندانی ئەنجام
                st.subheader("🎯 ئەنجامی کۆتایی:")
                st.text_area("وەرگێڕانی ئامادە بۆ فیلمەکە:", final_result, height=250)
                st.success("بە سەرکەوتوویی وەرگێڕدرا!")
                
            except Exception as e:
                st.error(f"⚠️ هەڵەیەک ڕوویدا لە کاتی وەرگێڕاندا: {e}")
                st.info("تکایە دڵنیابە کە API Keyـەکەت ڕاستە یان ئینتەرنێتت هەیە.")
        else:
            st.warning("⚠️ تکایە سەرەتا دەقێکی ئینگلیزی داخڵ بکە.")
else:
    st.info("👈 تکایە لە لای چەپ کلیلەکە (API Key) داخڵ بکە بۆ ئەوەی بەرنامەکە کار بکات.")
