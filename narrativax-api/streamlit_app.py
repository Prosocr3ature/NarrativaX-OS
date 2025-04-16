# Filename: narrativaX_app.py

import os, time, json, requests
import streamlit as st
from docx import Document
from fpdf import FPDF
from tempfile import NamedTemporaryFile
from gtts import gTTS
import replicate
from streamlit_sortables import sort_items

# --- CONFIG ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
replicate_client = replicate.Client(api_token=REPLICATE_API_TOKEN)

VOICES = {"Rachel": "default", "Bella": "default", "Antoni": "default"}
TONE_MAP = {
    "Romantic": "sensual, romantic",
    "NSFW": "mature, erotic",
    "Hardcore": "explicit, pornographic"
}
MODELS = [
    "openchat/openchat-3.5-0106",
    "gryphe/mythomax-l2-13b",
    "nothingiisreal/mn-celeste-12b"
]
IMAGE_MODELS = {
    "LucaTaco Realistic Vision V5.1": "lucataco/realistic-vision-v5.1:2c8e954...",
    "Reliberate V3 (NSFW)": "asiryan/reliberate-v3:d70438fc..."
}
GENRES = [
    "Adventure", "Fantasy", "Sci-Fi", "Romance", "Horror",
    "Erotica", "NSFW", "Hardcore"  # Adult genres will be locked
]

# --- STATE INIT ---
def initialize_state():
    defaults = {
        "last_saved": None,
        "book": {},
        "outline": "",
        "characters": [],
        "chapter_order": [],
        "adult_mode": False
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

initialize_state()

# --- SAFETY / AGE VERIFICATION ---
with st.sidebar:
    st.markdown("### Safety & Access")
    if not st.session_state.adult_mode:
        st.warning("**This app includes adult content filters.**\nYou must confirm you are 18+ to unlock NSFW options.")
        if st.button("I am 18+ and Understand"):
            st.session_state.adult_mode = True
    else:
        st.success("Adult content unlocked")
        if st.button("Lock Adult Mode"):
            st.session_state.adult_mode = False

# Filter genres/images based on age confirmation
genre_type = "Adult" if st.session_state.adult_mode else "Normal"
allowed_genres = [g for g in GENRES if (genre_type == "Adult") == (g in ["Erotica", "NSFW", "Hardcore"])]
allowed_image_models = {k: v for k, v in IMAGE_MODELS.items() if ("NSFW" not in k) or st.session_state.adult_mode}

# --- API CALLS ---
def call_openrouter(prompt, model, max_tokens=1500):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9,
        "max_tokens": max_tokens
    }
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def generate_outline(prompt, genre, tone, chapters, model):
    return call_openrouter(f"Create a {tone} {genre} novel outline with {chapters} chapters.\nPrompt: {prompt}", model)

def generate_section(title, outline, model):
    return call_openrouter(f"Write only the section '{title}' from this outline:\n{outline}\nSection: {title}", model)

def generate_full_book(outline, chapters, model):
    book = {}
    parts = ["Foreword", "Introduction"] + [f"Chapter {i+1}" for i in range(chapters)] + ["Final Words"]
    progress = st.progress(0)
    for i, title in enumerate(parts):
        st.write(f"**{title}**: Sharpening pencils...")
        book[title] = generate_section(title, outline, model)
        progress.progress((i+1)/len(parts))
    st.session_state.chapter_order = parts.copy()
    return book

# --- IMAGE ---
def generate_image(prompt, model_key):
    model = allowed_image_models.get(model_key)
    if not model:
        st.error("Access denied for this image model.")
        return None
    try:
        return replicate_client.run(model, input={"prompt": prompt[:300], "width": 768, "height": 1024})[0]
    except Exception as e:
        st.error(f"Image error: {e}")
        return None

# --- AUDIO ---
def narrate_story(text):
    try:
        tts = gTTS(text.strip().replace("\n", " "))
        fname = "narration.mp3"
        tts.save(fname)
        return fname
    except:
        return None

# --- EXPORT ---
def export_docx(data):
    doc = Document()
    for k, v in data.items():
        doc.add_heading(k, level=1)
        doc.add_paragraph(v)
    f = NamedTemporaryFile(delete=False, suffix=".docx")
    doc.save(f.name)
    return f.name

def export_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for k, v in data.items():
        pdf.set_font("Arial", style="B", size=14)
        pdf.cell(200, 10, k, ln=True)
        pdf.set_font("Arial", size=12)
        for line in v.splitlines():
            pdf.multi_cell(0, 10, line)
    f = NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(f.name)
    return f.name
# --- MAIN UI CONFIG ---
st.set_page_config(page_title="NarrativaX", layout="wide")
st.title("✒️ NarrativaX — AI Book Studio")

st.markdown("Craft, Illustrate & Narrate your books with AI — now PWA ready!")

# --- Book Builder UI ---
with st.expander("**Start Your Book**", expanded=True):
    prompt = st.text_area("Your Idea", placeholder="e.g. A lonely space captain explores a forgotten galaxy...")
    genre = st.selectbox("Genre", allowed_genres)
    tone = st.selectbox("Tone", list(TONE_MAP.keys()))
    chapters = st.slider("Chapters", 5, 20, 8)
    model = st.selectbox("Language Model", MODELS)
    image_model = st.selectbox("Image Model", list(allowed_image_models.keys()))
    voice = st.selectbox("Voice", list(VOICES.keys()))

    if st.button("Generate Book"):
        with st.spinner("Outlining story and writing chapters..."):
            outline = generate_outline(prompt, genre, TONE_MAP[tone], chapters, model)
            st.session_state.outline = outline
            st.session_state.book = generate_full_book(outline, chapters, model)
            st.session_state.last_saved = time.time()

# --- Display Book ---
if st.session_state.book:
    st.subheader("Your Book")
    order = sort_items(st.session_state.chapter_order)
    if order:
        st.session_state.chapter_order = order

    for section in st.session_state.chapter_order:
        with st.expander(section):
            st.markdown(st.session_state.book[section])
            if st.button(f"Narrate {section}", key=f"narrate_{section}"):
                audio = narrate_story(st.session_state.book[section])
                if audio:
                    st.audio(audio)
            if st.button(f"Illustrate {section}", key=f"img_{section}"):
                url = generate_image(st.session_state.book[section], image_model)
                if url:
                    st.image(url, caption=section)

# --- Character Tools ---
st.subheader("Characters")
cols = st.columns([1, 3])
with cols[0]:
    char_count = st.number_input("Characters", 1, 10, 3)
if st.button("Generate Characters"):
    chars = call_openrouter(
        f"Generate {char_count} characters for a {tone} {genre} story. "
        f"Format: Name, Role, Appearance, Personality, Motivation, Secret.", model
    ).split("\n\n")
    st.session_state.characters = chars

for i, char in enumerate(st.session_state.get("characters", [])):
    with st.expander(f"Character {i+1}"):
        updated = st.text_area("Edit", char, key=f"edit_char_{i}")
        st.session_state.characters[i] = updated
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Visualize", key=f"viz_char_{i}"):
                url = generate_image(updated, image_model)
                if url:
                    st.image(url, caption=f"Character {i+1}")
        with col2:
            if st.button("Delete", key=f"del_char_{i}"):
                st.session_state.characters.pop(i)
                st.experimental_rerun()

# --- Export ---
st.subheader("Export")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Export DOCX"):
        f = export_docx(st.session_state.book)
        st.download_button("Download DOCX", open(f, "rb"), file_name="book.docx")
with col2:
    if st.button("Export PDF"):
        f = export_pdf(st.session_state.book)
        st.download_button("Download PDF", open(f, "rb"), file_name="book.pdf")
with col3:
    st.download_button("Download JSON", json.dumps(st.session_state.book), file_name="book.json")

# --- Footer ---
st.markdown("---")
st.info("NarrativaX is installable as a mobile app! On iOS, tap 'Share → Add to Home Screen'. PWA powered.")