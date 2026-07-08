import streamlit as st
import google.generativeai as genai

# --- ڕێکخستنی لاپەڕە ---
st.set_page_config(page_title="وەرگێڕی زیرەکی کوردی Pro", page_icon="🎬", layout="centered")

st.markdown("""
    <style>
    .stTextArea textarea { text-align: right; direction: rtl; font-size: 16px; }
    .stMarkdown, p, h1, h2, h3 { text-align: right; direction: rtl; font-family: Arial, sans-serif; }
    </style>
    """, unsafe_allow_html=True)

st.title("سیستەمی وەرگێڕانی فیلم (وەشانی Pro) 🎬")
st.write("ئەم وەشانە مۆدێلی زۆر پێشکەوتووی (Gemini 1.5 Pro) بەکاردەهێنێت بۆ وەرگێڕانی دروست و پاراوی کوردی.")

# --- وەرگرتنی کلیل لە لاتەنیشت ---
api_key = st.sidebar.text_input("🔑 Google API Key لێرە دابنێ:", type="password")

if api_key:
    genai.configure(api_key=api_key)
    # لێرەدا زیرەکترین مۆدێلمان بەکارهێناوە
    model = genai.GenerativeModel('gemini-1.5-pro')

    english_text = st.text_area("📝 دەقی ئینگلیزی لێرە دابنێ:", height=200)

    if st.button("🚀 دەستپێکردنی وەرگێڕان"):
        if english_text:
            try:
                # قۆناغی ١: وەرگێڕانی واتا نەک وشە
                with st.status("١. وەرگێڕانی مانای ڕستەکان...") as s:
                    p1 = f"""You are a professional movie translator. Translate this English text to Kurdish Sorani. 
                    Rule 1: DO NOT translate word-for-word. 
                    Rule 2: Focus on the true meaning and context.
                    Text: {english_text}"""
                    res1 = model.generate_content(p1)
                    trans1 = res1.text
                    s.update(label="✅ قۆناغی ١ تەواو بوو", state="complete")

                # قۆناغی ٢: بە کوردیکردنی ڕەسەن
                with st.status("٢. داڕشتنەوەی کوردییانە (وەک قسەکردنی ناو فیلم)...") as s:
                    p2 = f"""Take this Kurdish translation and rewrite it to sound completely natural for a Kurdish movie watcher.
                    Rule 1: Use natural Sorani slang or expressions where appropriate.
                    Rule 2: Ensure the grammar is 100% correct. Fix any weird AI-sounding sentences.
                    Kurdish text: {trans1}"""
                    res2 = model.generate_content(p2)
                    trans2 = res2.text
                    s.update(label="✅ قۆناغی ٢ تەواو بوو", state="complete")

                # قۆناغی ٣: پیاچوونەوەی کۆتایی
                with st.status("٣. پیاچوونەوەی کۆتایی مانا و هەڵەکان...") as s:
                    p3 = f"""Compare the original English text with the final Kurdish text. 
                    If the Kurdish translation lost any meaning, fix it. If it is perfect, just output the final Kurdish text.
                    DO NOT add any conversational text, ONLY output the final Kurdish translation.
                    English: {english_text}
                    Kurdish: {trans2}"""
                    res3 = model.generate_content(p3)
                    final_result = res3.text
                    s.update(label="✅ هەموو قۆناغەکان بەسەرکەوتوویی تەواو بوون!", state="complete")

                # پیشاندانی ئەنجام
                st.subheader("🎯 ئەنجامی کۆتایی:")
                st.text_area("وەرگێڕانی ئامادە بۆ فیلمەکە:", final_result, height=250)
                st.success("بە سەرکەوتوویی وەرگێڕدرا!")
                
            except Exception as e:
                st.error(f"⚠️ هەڵەیەک ڕوویدا: {e}")
        else:
            st.warning("⚠️ تکایە سەرەتا دەقێکی ئینگلیزی داخڵ بکە.")
else:
    st.info("👈 تکایە لە لای چەپ کلیلەکە (API Key) داخڵ بکە.")
