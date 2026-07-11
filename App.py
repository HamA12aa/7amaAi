import streamlit as st
import google.generativeai as genai

# ==========================================
# 1. UI & CSS (خێرا و سینەمایی)
# ==========================================
st.set_page_config(page_title="AI Director Studio | Lore V6", layout="wide", page_icon="📖")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;800&display=swap');
    html, body, [data-testid="stSidebar"], .stMarkdown { font-family: 'Vazirmatn', sans-serif; direction: rtl; }
    
    .main-title { text-align: center; font-weight: 900; background: -webkit-linear-gradient(45deg, #00f2fe, #4facfe); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px; font-size: 3.5rem;}
    .sub-title { text-align: center; color: #a0a0a0; margin-bottom: 30px; font-size: 1.2rem; }
    
    .agent-header { padding: 15px; border-radius: 10px; color: white; text-align: center; font-size: 1.4rem; font-weight: bold; margin-bottom: 15px;}
    .bg-story { background: linear-gradient(90deg, #1e3c72, #2a5298); box-shadow: 0 4px 15px rgba(42, 82, 152, 0.5);}
    .bg-wiki { background: linear-gradient(90deg, #b20a2c, #fffbd5); color: #111 !important; box-shadow: 0 4px 15px rgba(178, 10, 44, 0.5);}
    
    .result-box-ku { background: #0d0d0d; padding: 25px; border-radius: 12px; border: 1px solid #333; color: #ddd; direction: rtl; text-align: right; overflow-y: auto; font-size: 1.1em; line-height: 1.9;}
    .result-box-en { background: #050505; padding: 25px; border-radius: 12px; border: 1px solid #444; color: #00ffcc; direction: ltr; text-align: left; overflow-y: auto; font-size: 1.1em; line-height: 1.7; font-family: 'Courier New', monospace;}
    
    .stTextArea textarea { direction: ltr !important; font-family: 'Courier New', monospace; background-color: #050505; color: #00ffcc; border: 1px solid #444; border-radius: 8px;}
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%); color: #000; font-size: 1.1em; font-weight: bold; border: none; transition: 0.3s;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. بریکاری یەکەم: شیکاری چیرۆک (سۆرانی)
# ==========================================
def run_agent1(keys, model_name, srt_text):
    prompt = f"""You are 'Agent 1: The Master Lore Architect'.
Your task is to analyze this SRT file in **Kurdish (Sorani)**.
DO NOT TRANSLATE IT. IGNORE ALL SONGS AND LYRICS completely.

Provide your output beautifully formatted with these specific sections:
1. 📖 **کڕۆکی چیرۆکەکە (The Deep Core):** A 100% accurate explanation of what is truly happening in this scene/episode.
2. 🎭 **شیکاری دەروونی کەسایەتییەکان (Psychological Profile):** Who is speaking? What are their hidden motivations?
3. 🔍 **هێما و شاراوەکان (Hidden Meanings):** Any cultural context or hidden lore.
4. 📜 **دەستووری وەرگێڕان (The Translation Bible):** Absolute rules for the translator.

SRT Text:
{srt_text[:40000]}"""
    
    for key in keys:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(model_name)
            return model.generate_content(prompt).text
        except Exception: continue
    return "❌ هەڵە لە بریکاری یەکەم. دڵنیابە لە کلیلەکەت."

# ==========================================
# 3. بریکاری دووەم: پرۆفایل و زانیاری (ئینگلیزی)
# ==========================================
def run_agent2(keys, model_name, srt_text):
    prompt = f"""You are 'Agent 2: The Anime Wiki Master'.
Read the provided SRT. Deduce which anime, movie, or series this is from. 
Then, search your vast knowledge base and provide a HIGHLY DETAILED Wiki-style profile in **ENGLISH**.

Include these sections specifically in ENGLISH:
1. 🎬 **Anime/Series Name & Overview:** Identify the show and give a brief synopsis of its world.
2. 👤 **Main Character Profiles:** Detail the backstory, personality, abilities/powers, and role of the key characters mentioned in this text.
3. 🌍 **Cities, Locations & Lore:** Describe the specific cities, regions, or universe elements relevant to this text.

Provide exhaustive, rich details as if writing for an encyclopedia.

SRT Text:
{srt_text[:40000]}"""
    
    for key in keys:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(model_name)
            return model.generate_content(prompt).text
        except Exception: continue
    return "❌ Error in Agent 2. Please check your API keys."

# ==========================================
# 4. ڕووکاری سەرەکی (Main UI)
# ==========================================
st.markdown("<h1 class='main-title'>AI Lore Studio 📖 V6</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>شیکاری قووڵی دەق + دروستکردنی پرۆفایلی کەسایەتییەکان بە ئینگلیزی</p>", unsafe_allow_html=True)

with st.sidebar:
    st.header("🔑 کلیلەکان")
    gemini_keys = [st.text_input(f"Gemini Key {i+1}", type="password") for i in range(2)]
    active_g_keys = [k.strip() for k in gemini_keys if k.strip()]
    
    st.markdown("---")
    st.header("⚙️ هەڵبژاردنی مۆدێلەکان")
    available_models = []
    
    if active_g_keys:
        try:
            genai.configure(api_key=active_g_keys[0])
            available_models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        except:
            st.error("کێشە لە کلیلەکانی Gemini هەیە.")
    
    if available_models:
        agent1_model = st.selectbox("بریکاری ١ (شیکاری کوردی):", available_models, index=0)
        agent2_model = st.selectbox("بریکاری ٢ (زانیاری ئینگلیزی):", available_models, index=0)
    else:
        agent1_model, agent2_model = None, None
        st.warning("تکایە کلیلی Gemini دابنێ بۆ بینینی مۆدێلەکان.")

input_srt = st.text_area("📄 دەقی ئینگلیزی (SRT) یان چەند دێڕێک لێرە دابنێ:", height=250)

if st.button("🚀 دەستپێکردنی گەڕان و شیکاری"):
    if not active_g_keys:
        st.warning("تکایە کلیلی API دابنێ لە لای ڕاست.")
    elif not input_srt.strip():
        st.warning("تکایە دەقی فیلمەکە دابنێ.")
    elif not agent1_model or not agent2_model:
        st.error("تکایە مۆدێلەکان هەڵبژێرە.")
    else:
        status_box = st.empty()
        
        status_box.info("🕵️ بریکاری یەکەم خەریکی شیکاری چیرۆکەکەیە بە کوردی...")
        agent1_result = run_agent1(active_g_keys, agent1_model, input_srt)
        
        status_box.warning("📚 بریکاری دووەم خەریکی کۆکردنەوەی زانیاری و پرۆفایلە بە ئینگلیزی...")
        agent2_result = run_agent2(active_g_keys, agent2_model, input_srt)
        
        status_box.empty()
        st.success("✅ هەموو زانیارییەکان بە سەرکەوتوویی ئامادەکران!")
        
        # نیشاندانی ئەنجامەکان لە دوو تابی جیا
        tab1, tab2 = st.tabs(["🕵️ بریکاری ١ (شیکاری کوردی)", "📚 بریکاری ٢ (پرۆفایل بە ئینگلیزی)"])
        
        with tab1:
            st.markdown("<div class='agent-header bg-story'>شیکاری قووڵی چیرۆک و دەق</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='result-box-ku'>{agent1_result}</div>", unsafe_allow_html=True)
            st.download_button("📥 سەیڤکردنی شیکاری", agent1_result, "Agent1_Story.txt")
            
        with tab2:
            st.markdown("<div class='agent-header bg-wiki'>Anime Wiki & Character Profiles</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='result-box-en'>{agent2_result}</div>", unsafe_allow_html=True)
            st.download_button("📥 سەیڤکردنی پرۆفایلەکان", agent2_result, "Agent2_Wiki_Profiles.txt")
