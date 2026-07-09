import streamlit as st import google.generativeai as genai import time import re
import random import tempfile

==========================================

1. PRO STUDIO UI & CSS

==========================================

st.set_page_config(page_title="AI Movie Studio PRO | V11", layout="wide",
page_icon="🎬")

st.markdown("""  @import
url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;800&display=swap');
html, body, [data-testid="stSidebar"], .stMarkdown { font-family: 'Vazirmatn',
sans-serif; }

.main-title { text-align: center; font-weight: 800; background: -webkit-linear-gradient(45deg, #ff4b4b, #ff904f); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px; font-size: 3rem;}
.sub-title { text-align: center; color: #a0a0a0; margin-bottom: 30px; font-size: 1.2rem; }

.status-box { background: rgba(14, 17, 23, 0.8); border: 1px solid #333; padding: 15px; border-radius: 12px; margin-bottom: 10px; border-right: 4px solid #00ffcc; color: #fff;}
.live-preview-box { background: #111; padding: 20px; border-radius: 12px; border-top: 4px solid #ff4b4b; color: #ddd; direction: rtl; text-align: right; height: 300px; overflow-y: auto; font-size: 1.1em; line-height: 1.6;}

.stTextArea textarea { direction: ltr !important; font-family: 'Courier New', monospace; background-color: #0a0a0a; color: #00ffcc; border: 1px solid #333; border-radius: 8px;}
.stTextArea textarea:focus { border-color: #ff4b4b; box-shadow: 0 0 5px rgba(255, 75, 75, 0.5); }

.stButton>button { width: 100%; border-radius: 10px; height: 3.8em; background: linear-gradient(90deg, #ff4b4b 0%, #d42222 100%); color: white; font-size: 1.1em; font-weight: bold; border: none; transition: 0.3s;}
.stButton>button:hover { transform: scale(1.02); box-shadow: 0 5px 15px rgba(255, 75, 75, 0.4); }

/* Progress bar styling */
.stProgress > div > div > div > div { background-color: #00ffcc; }
</style>

""", unsafe_allow_html=True)

==========================================

2. SESSION STATE MANAGEMENT (ANTI-CRASH)

==========================================

ئەم بەشە ڕێگری دەکات لە سڕینەوەی داتا ئەگەر پەڕەکە ڕیفرێش بێت

if "saved_chunks" not in st.session_state: st.session_state.saved_chunks = {} #
پاراستنی پارچە وەرگێڕدراوەکان if "last_srt_input" not in st.session_state:
st.session_state.last_srt_input = "" if "master_context" not in
st.session_state: st.session_state.master_context = "" if "is_translating" not
in st.session_state: st.session_state.is_translating = False if "final_srt" not
in st.session_state: st.session_state.final_srt = ""

==========================================

3. SRT PARSER & BUILDER

==========================================

def parse_srt(srt_string): srt_string = srt_string.replace('\r\n', '\n').strip()
blocks = re.split(r'\n\n+', srt_string) parsed = [] for block in blocks: lines =
block.split('\n') if len(lines) >= 3: idx = lines[0].strip() time_str =
lines[1].strip() text = '\n'.join(lines[2:]).strip() parsed.append({'id': idx,
'time': time_str, 'text': text}) return parsed

def build_srt(parsed_list): return
'\n\n'.join([f"{item['id']}\n{item['time']}\n{item['text']}" for item in
parsed_list])

==========================================

4. AGENT 1: STORY ANALYZER

==========================================

def analyze_master_context(active_keys, model_name, srt_text, glossary,
video_file=None): prompt = f"""Analyze this subtitle file and create a
Translation Bible. Include: Story Summary, Character tone, and cultural notes.
Glossary: {glossary} Subtitles: {srt_text[:10000]}"""

for current_key in active_keys: # Fast try logic
    genai.configure(api_key=current_key)
    model = genai.GenerativeModel(model_name)
    contents = [prompt]
    try:
        if video_file:
            with st.spinner("⏳ ناردنی ڤیدیۆ (تایم ئاوت: ١٢٠ چرکە)..."):
                video_file.seek(0)
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                    tmp.write(video_file.read())
                    v_path = tmp.name
                g_file = genai.upload_file(path=v_path)
                
                start_time = time.time()
                while g_file.state.name == "PROCESSING":
                    if time.time() - start_time > 120:
                        st.warning("⚠️ ڤیدیۆکە زۆری خایاند، تەنها دەق بەکاردێنین.")
                        break
                    time.sleep(3)
                    g_file = genai.get_file(g_file.name)
                if g_file.state.name == "ACTIVE":
                    contents.insert(0, g_file)
                    
        with st.spinner("🕵️ بریکاری ١: شیکردنەوەی چیرۆک..."):
            response = model.generate_content(contents)
            return response.text
    except:
        continue
return "⚠️ نەتوانرا چیرۆکەکە بەتەواوی شیکار بکرێت، بەڵام وەرگێڕانەکە بەردەوام دەبێت..."

==========================================

5. FAST XML TRANSLATOR (30 LINES AT ONCE)

==========================================

def translate_chunk_fast(chunk, active_keys, master_context, visual_container,
selected_model): xml_input = "" for item in chunk: clean_text =
item['text'].replace('<', '').replace('>', '') xml_input += f'<sub
id="{item["id"]}">{clean_text}\n'

# پڕۆمپتی زۆر خێرا و کورت بۆ ئەوەی ڕاستەوخۆ ئەنجام بدات
prompt = f"""You are a professional Anime translator (English to Kurdish Sorani).

Master Context: {master_context}

RULES:

1.  NEVER shorten the sentences. Translate every detail to match the original
    length.
2.  ONLY output the XML format. No extra text, no thoughts.

Input: {xml_input}

Output format ONLY: kurdish text... """

attempts = 0
while attempts < len(active_keys) * 2:
    current_key = random.choice(active_keys)
    try:
        visual_container.markdown(f"<div class='status-box'>⚡ <b>بریکارەکان خەریکی کارن:</b> وەرگێڕانی ٣٠ دێڕ پێکەوە (کلیل: ***{current_key[-4:]})</div>", unsafe_allow_html=True)
        
        genai.configure(api_key=current_key)
        model = genai.GenerativeModel(selected_model, generation_config={"temperature": 0.2})
        
        response = model.generate_content(prompt)
        clean_response = response.text.replace('```xml', '').replace('```', '').strip()
        
        matches = re.findall(r'<sub id="(\d+)"\s*>(.*?)</sub>', clean_response, re.DOTALL | re.IGNORECASE)
        
        if matches:
            result_map = {m[0].strip(): m[1].strip() for m in matches}
            return result_map
        else:
            time.sleep(1)
    except Exception as e:
        if "429" in str(e) or "ResourceExhausted" in str(e):
            visual_container.error(f"🔴 لیمیتە! گۆڕینی کلیل...")
            time.sleep(2)
        else:
            time.sleep(1)
    attempts += 1
return None

==========================================

6. MAIN UI & LOGIC

==========================================

st.markdown("AI Movie Studio PRO 🎬", unsafe_allow_html=True)
st.markdown("سیستەمی دژە-ڕیفرێش | وەرگێڕانی خێرا (٣٠ دێڕ) | نەپچڕانی
پرۆسە", unsafe_allow_html=True)

with st.sidebar: st.header("🔑 کلیلی API") api_inputs = [ st.text_input("Slot 1",
type="password"), st.text_input("Slot 2", type="password"),
st.text_input("Slot 3", type="password"), st.text_input("Slot 4",
type="password") ] active_keys = [k.strip() for k in api_inputs if k.strip()]

st.markdown("---")
st.header("🤖 مۆدێلەکان")

gemini_model_name = None
if active_keys:
    try:
        genai.configure(api_key=active_keys[0])
        available_models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if available_models:
            gemini_model_name = st.selectbox("مۆدێل:", available_models)
    except:
        st.error("⚠️ کێشەی کلیل.")
        
st.markdown("---")
glossary = st.text_area("📚 فەرهەنگ", placeholder="وشەکان لێرە بنووسە...")
uploaded_video = st.file_uploader("🎥 ڤیدیۆ", type=['mp4'])

tab1, tab2, tab3 = st.tabs(["📥 ١. فایلی SRT", "⚙️ ٢. ستۆدیۆی وەرگێڕان", "✅ ٣.
بەرهەمی کۆتایی"])

with tab1: input_srt = st.text_area("دەقی SRT لێرە دابنێ:", height=300)
start_btn = st.button("🚀 دەستپێکردن / بەردەوامبوون (Resume)")

if start_btn: if not input_srt: st.warning("دەق دابنێ.") elif not active_keys:
st.error("کلیل دابنێ.") elif not gemini_model_name: st.error("مۆدێل
نەدۆزرایەوە.") else: # لۆژیکی دژە-سڕینەوە: ئەگەر دەقەکە هەمان دەقی پێشوو نەبوو،
ئەوا ڕیفرێش کراوە بۆ پەڕەیەکی نوێ if input_srt !=
st.session_state.last_srt_input: st.session_state.saved_chunks = {} # سڕینەوەی
داتای کۆن st.session_state.master_context = "" st.session_state.last_srt_input =
input_srt

    st.session_state.is_translating = True

if getattr(st.session_state, 'is_translating', False): with tab2: # 1.
شیکردنەوەی چیرۆک if not st.session_state.master_context:
st.session_state.master_context = analyze_master_context(active_keys,
gemini_model_name, input_srt, glossary, uploaded_video) st.success("✅ چیرۆکەکە
شیکرایەوە.")

    # 2. ئامادەکردنی پارچەکان
    parsed_data = parse_srt(input_srt)
    chunk_size = 30 # بڕی وەرگێڕانی زۆر خێرا
    chunks = [parsed_data[i : i + chunk_size] for i in range(0, len(parsed_data), chunk_size)]
    total_chunks = len(chunks)
    
    progress_bar = st.progress(0)
    status_box = st.empty()
    preview_box = st.empty()
    
    # پیشاندانی پێشکەوتنی ڕاستەوخۆ تەنانەت ئەگەر ڕیفرێشیش کرابێت
    current_srt_preview = ""
    for k, v in sorted(st.session_state.saved_chunks.items()):
        current_srt_preview += build_srt(v) + "\n\n"
    
    if current_srt_preview:
        preview_box.markdown(f"<div class='live-preview-box'>{current_srt_preview[-800:].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
        st.info(f"🔄 دەستپێکردنەوە (Resume) لە پارچەی {len(st.session_state.saved_chunks) + 1}...")

    # 3. وەرگێڕانی پارچەکان
    for chunk_idx, chunk in enumerate(chunks):
        # ئەگەر ئەم پارچەیە پێشتر وەرگێڕدراوە (سەیڤ بووە)، با کاتی بۆ نەکوژین!
        if chunk_idx in st.session_state.saved_chunks:
            progress_bar.progress((chunk_idx + 1) / total_chunks)
            continue
        
        with status_box.container():
            st.markdown(f"**پارچەی {chunk_idx + 1} لە کۆی {total_chunks}** (هەر پارچەیەک ٣٠ دێڕە)")
            
            result_map = translate_chunk_fast(chunk, active_keys, st.session_state.master_context, st.empty(), gemini_model_name)
            
            translated_chunk = []
            if result_map:
                for item in chunk:
                    new_item = item.copy()
                    item_id = str(item['id'])
                    if item_id in result_map and result_map[item_id]:
                        new_item['text'] = result_map[item_id]
                    translated_chunk.append(new_item)
            else:
                st.error(f"❌ شکستی هێنا لە پارچەی {chunk_idx+1}.")
                translated_chunk.extend(chunk)
            
            # سەیڤکردنی ڕاستەوخۆ لەناو مێشک (Auto-Save)
            st.session_state.saved_chunks[chunk_idx] = translated_chunk
            
        # نوێکردنەوەی پیشاندانی ڕاستەوخۆ
        current_srt_preview += build_srt(translated_chunk) + "\n\n"
        preview_box.markdown(f"<div class='live-preview-box'>{current_srt_preview[-800:].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
        progress_bar.progress((chunk_idx + 1) / total_chunks)
        time.sleep(1)
        
    # کۆتایی هاتن
    final_list = []
    for i in range(total_chunks):
        final_list.extend(st.session_state.saved_chunks.get(i, chunks[i]))
        
    st.session_state.final_srt = build_srt(final_list)
    st.session_state.is_translating = False
    st.success("✅ وەرگێڕان بە خێرایی کۆتایی هات! بڕۆ بۆ تابی سێیەم.")

with tab3: if st.session_state.final_srt: st.balloons() st.download_button("📥
داگرتنی فایلی کۆتایی (.srt)", data=st.session_state.final_srt,
file_name="Studio_Translated.srt") st.markdown("📝 کۆدی SRT",
unsafe_allow_html=True) st.text_area("", st.session_state.final_srt, height=400,
label_visibility="collapsed") else: st.info("هێشتا وەرگێڕان نەکراوە.") import
streamlit as st import google.generativeai as genai import time import re import
random import tempfile

==========================================

1. PRO STUDIO UI & CSS

==========================================

st.set_page_config(page_title="AI Movie Studio PRO | V11", layout="wide",
page_icon="🎬")

st.markdown("""  @import
url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;800&display=swap');
html, body, [data-testid="stSidebar"], .stMarkdown { font-family: 'Vazirmatn',
sans-serif; }

.main-title { text-align: center; font-weight: 800; background: -webkit-linear-gradient(45deg, #ff4b4b, #ff904f); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px; font-size: 3rem;}
.sub-title { text-align: center; color: #a0a0a0; margin-bottom: 30px; font-size: 1.2rem; }

.status-box { background: rgba(14, 17, 23, 0.8); border: 1px solid #333; padding: 15px; border-radius: 12px; margin-bottom: 10px; border-right: 4px solid #00ffcc; color: #fff;}
.live-preview-box { background: #111; padding: 20px; border-radius: 12px; border-top: 4px solid #ff4b4b; color: #ddd; direction: rtl; text-align: right; height: 300px; overflow-y: auto; font-size: 1.1em; line-height: 1.6;}

.stTextArea textarea { direction: ltr !important; font-family: 'Courier New', monospace; background-color: #0a0a0a; color: #00ffcc; border: 1px solid #333; border-radius: 8px;}
.stTextArea textarea:focus { border-color: #ff4b4b; box-shadow: 0 0 5px rgba(255, 75, 75, 0.5); }

.stButton>button { width: 100%; border-radius: 10px; height: 3.8em; background: linear-gradient(90deg, #ff4b4b 0%, #d42222 100%); color: white; font-size: 1.1em; font-weight: bold; border: none; transition: 0.3s;}
.stButton>button:hover { transform: scale(1.02); box-shadow: 0 5px 15px rgba(255, 75, 75, 0.4); }

/* Progress bar styling */
.stProgress > div > div > div > div { background-color: #00ffcc; }
</style>

""", unsafe_allow_html=True)

==========================================

2. SESSION STATE MANAGEMENT (ANTI-CRASH)

==========================================

ئەم بەشە ڕێگری دەکات لە سڕینەوەی داتا ئەگەر پەڕەکە ڕیفرێش بێت

if "saved_chunks" not in st.session_state: st.session_state.saved_chunks = {} #
پاراستنی پارچە وەرگێڕدراوەکان if "last_srt_input" not in st.session_state:
st.session_state.last_srt_input = "" if "master_context" not in
st.session_state: st.session_state.master_context = "" if "is_translating" not
in st.session_state: st.session_state.is_translating = False if "final_srt" not
in st.session_state: st.session_state.final_srt = ""

==========================================

3. SRT PARSER & BUILDER

==========================================

def parse_srt(srt_string): srt_string = srt_string.replace('\r\n', '\n').strip()
blocks = re.split(r'\n\n+', srt_string) parsed = [] for block in blocks: lines =
block.split('\n') if len(lines) >= 3: idx = lines[0].strip() time_str =
lines[1].strip() text = '\n'.join(lines[2:]).strip() parsed.append({'id': idx,
'time': time_str, 'text': text}) return parsed

def build_srt(parsed_list): return
'\n\n'.join([f"{item['id']}\n{item['time']}\n{item['text']}" for item in
parsed_list])

==========================================

4. AGENT 1: STORY ANALYZER

==========================================

def analyze_master_context(active_keys, model_name, srt_text, glossary,
video_file=None): prompt = f"""Analyze this subtitle file and create a
Translation Bible. Include: Story Summary, Character tone, and cultural notes.
Glossary: {glossary} Subtitles: {srt_text[:10000]}"""

for current_key in active_keys: # Fast try logic
    genai.configure(api_key=current_key)
    model = genai.GenerativeModel(model_name)
    contents = [prompt]
    try:
        if video_file:
            with st.spinner("⏳ ناردنی ڤیدیۆ (تایم ئاوت: ١٢٠ چرکە)..."):
                video_file.seek(0)
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                    tmp.write(video_file.read())
                    v_path = tmp.name
                g_file = genai.upload_file(path=v_path)
                
                start_time = time.time()
                while g_file.state.name == "PROCESSING":
                    if time.time() - start_time > 120:
                        st.warning("⚠️ ڤیدیۆکە زۆری خایاند، تەنها دەق بەکاردێنین.")
                        break
                    time.sleep(3)
                    g_file = genai.get_file(g_file.name)
                if g_file.state.name == "ACTIVE":
                    contents.insert(0, g_file)
                    
        with st.spinner("🕵️ بریکاری ١: شیکردنەوەی چیرۆک..."):
            response = model.generate_content(contents)
            return response.text
    except:
        continue
return "⚠️ نەتوانرا چیرۆکەکە بەتەواوی شیکار بکرێت، بەڵام وەرگێڕانەکە بەردەوام دەبێت..."

==========================================

5. FAST XML TRANSLATOR (30 LINES AT ONCE)

==========================================

def translate_chunk_fast(chunk, active_keys, master_context, visual_container,
selected_model): xml_input = "" for item in chunk: clean_text =
item['text'].replace('<', '').replace('>', '') xml_input += f'<sub
id="{item["id"]}">{clean_text}\n'

# پڕۆمپتی زۆر خێرا و کورت بۆ ئەوەی ڕاستەوخۆ ئەنجام بدات
prompt = f"""You are a professional Anime translator (English to Kurdish Sorani).

Master Context: {master_context}

RULES:

1.  NEVER shorten the sentences. Translate every detail to match the original
    length.
2.  ONLY output the XML format. No extra text, no thoughts.

Input: {xml_input}

Output format ONLY: kurdish text... """

attempts = 0
while attempts < len(active_keys) * 2:
    current_key = random.choice(active_keys)
    try:
        visual_container.markdown(f"<div class='status-box'>⚡ <b>بریکارەکان خەریکی کارن:</b> وەرگێڕانی ٣٠ دێڕ پێکەوە (کلیل: ***{current_key[-4:]})</div>", unsafe_allow_html=True)
        
        genai.configure(api_key=current_key)
        model = genai.GenerativeModel(selected_model, generation_config={"temperature": 0.2})
        
        response = model.generate_content(prompt)
        clean_response = response.text.replace('```xml', '').replace('```', '').strip()
        
        matches = re.findall(r'<sub id="(\d+)"\s*>(.*?)</sub>', clean_response, re.DOTALL | re.IGNORECASE)
        
        if matches:
            result_map = {m[0].strip(): m[1].strip() for m in matches}
            return result_map
        else:
            time.sleep(1)
    except Exception as e:
        if "429" in str(e) or "ResourceExhausted" in str(e):
            visual_container.error(f"🔴 لیمیتە! گۆڕینی کلیل...")
            time.sleep(2)
        else:
            time.sleep(1)
    attempts += 1
return None

==========================================

6. MAIN UI & LOGIC

==========================================

st.markdown("AI Movie Studio PRO 🎬", unsafe_allow_html=True)
st.markdown("سیستەمی دژە-ڕیفرێش | وەرگێڕانی خێرا (٣٠ دێڕ) | نەپچڕانی
پرۆسە", unsafe_allow_html=True)

with st.sidebar: st.header("🔑 کلیلی API") api_inputs = [ st.text_input("Slot 1",
type="password"), st.text_input("Slot 2", type="password"),
st.text_input("Slot 3", type="password"), st.text_input("Slot 4",
type="password") ] active_keys = [k.strip() for k in api_inputs if k.strip()]

st.markdown("---")
st.header("🤖 مۆدێلەکان")

gemini_model_name = None
if active_keys:
    try:
        genai.configure(api_key=active_keys[0])
        available_models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if available_models:
            gemini_model_name = st.selectbox("مۆدێل:", available_models)
    except:
        st.error("⚠️ کێشەی کلیل.")
        
st.markdown("---")
glossary = st.text_area("📚 فەرهەنگ", placeholder="وشەکان لێرە بنووسە...")
uploaded_video = st.file_uploader("🎥 ڤیدیۆ", type=['mp4'])

tab1, tab2, tab3 = st.tabs(["📥 ١. فایلی SRT", "⚙️ ٢. ستۆدیۆی وەرگێڕان", "✅ ٣.
بەرهەمی کۆتایی"])

with tab1: input_srt = st.text_area("دەقی SRT لێرە دابنێ:", height=300)
start_btn = st.button("🚀 دەستپێکردن / بەردەوامبوون (Resume)")

if start_btn: if not input_srt: st.warning("دەق دابنێ.") elif not active_keys:
st.error("کلیل دابنێ.") elif not gemini_model_name: st.error("مۆدێل
نەدۆزرایەوە.") else: # لۆژیکی دژە-سڕینەوە: ئەگەر دەقەکە هەمان دەقی پێشوو نەبوو،
ئەوا ڕیفرێش کراوە بۆ پەڕەیەکی نوێ if input_srt !=
st.session_state.last_srt_input: st.session_state.saved_chunks = {} # سڕینەوەی
داتای کۆن st.session_state.master_context = "" st.session_state.last_srt_input =
input_srt

    st.session_state.is_translating = True

if getattr(st.session_state, 'is_translating', False): with tab2: # 1.
شیکردنەوەی چیرۆک if not st.session_state.master_context:
st.session_state.master_context = analyze_master_context(active_keys,
gemini_model_name, input_srt, glossary, uploaded_video) st.success("✅ چیرۆکەکە
شیکرایەوە.")

    # 2. ئامادەکردنی پارچەکان
    parsed_data = parse_srt(input_srt)
    chunk_size = 30 # بڕی وەرگێڕانی زۆر خێرا
    chunks = [parsed_data[i : i + chunk_size] for i in range(0, len(parsed_data), chunk_size)]
    total_chunks = len(chunks)
    
    progress_bar = st.progress(0)
    status_box = st.empty()
    preview_box = st.empty()
    
    # پیشاندانی پێشکەوتنی ڕاستەوخۆ تەنانەت ئەگەر ڕیفرێشیش کرابێت
    current_srt_preview = ""
    for k, v in sorted(st.session_state.saved_chunks.items()):
        current_srt_preview += build_srt(v) + "\n\n"
    
    if current_srt_preview:
        preview_box.markdown(f"<div class='live-preview-box'>{current_srt_preview[-800:].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
        st.info(f"🔄 دەستپێکردنەوە (Resume) لە پارچەی {len(st.session_state.saved_chunks) + 1}...")

    # 3. وەرگێڕانی پارچەکان
    for chunk_idx, chunk in enumerate(chunks):
        # ئەگەر ئەم پارچەیە پێشتر وەرگێڕدراوە (سەیڤ بووە)، با کاتی بۆ نەکوژین!
        if chunk_idx in st.session_state.saved_chunks:
            progress_bar.progress((chunk_idx + 1) / total_chunks)
            continue
        
        with status_box.container():
            st.markdown(f"**پارچەی {chunk_idx + 1} لە کۆی {total_chunks}** (هەر پارچەیەک ٣٠ دێڕە)")
            
            result_map = translate_chunk_fast(chunk, active_keys, st.session_state.master_context, st.empty(), gemini_model_name)
            
            translated_chunk = []
            if result_map:
                for item in chunk:
                    new_item = item.copy()
                    item_id = str(item['id'])
                    if item_id in result_map and result_map[item_id]:
                        new_item['text'] = result_map[item_id]
                    translated_chunk.append(new_item)
            else:
                st.error(f"❌ شکستی هێنا لە پارچەی {chunk_idx+1}.")
                translated_chunk.extend(chunk)
            
            # سەیڤکردنی ڕاستەوخۆ لەناو مێشک (Auto-Save)
            st.session_state.saved_chunks[chunk_idx] = translated_chunk
            
        # نوێکردنەوەی پیشاندانی ڕاستەوخۆ
        current_srt_preview += build_srt(translated_chunk) + "\n\n"
        preview_box.markdown(f"<div class='live-preview-box'>{current_srt_preview[-800:].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
        progress_bar.progress((chunk_idx + 1) / total_chunks)
        time.sleep(1)
        
    # کۆتایی هاتن
    final_list = []
    for i in range(total_chunks):
        final_list.extend(st.session_state.saved_chunks.get(i, chunks[i]))
        
    st.session_state.final_srt = build_srt(final_list)
    st.session_state.is_translating = False
    st.success("✅ وەرگێڕان بە خێرایی کۆتایی هات! بڕۆ بۆ تابی سێیەم.")

with tab3: if st.session_state.final_srt: st.balloons() st.download_button("📥
داگرتنی فایلی کۆتایی (.srt)", data=st.session_state.final_srt,
file_name="Studio_Translated.srt") st.markdown("📝 کۆدی SRT",
unsafe_allow_html=True) st.text_area("", st.session_state.final_srt, height=400,
label_visibility="collapsed") else: st.info("هێشتا وەرگێڕان نەکراوە.")
