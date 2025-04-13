# NarrativaX — Full-featured AI Book Creator
# Includes: retry TTS, model switcher, progress %, illustration per chapter

import os, time, textwrap, requests, pyttsx3
import streamlit as st
from docx import Document
from fpdf import FPDF
from tempfile import NamedTemporaryFile
from elevenlabs import generate
from elevenlabs.client import ElevenLabs

# API KEYS
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
eleven_client = ElevenLabs(api_key=ELEVEN_API_KEY)

VOICES = {
    "Rachel": "EXAVITQu4vr4xnSDxMaL",
    "Bella": "29vD33N1CtxCmqQRPOHJ",
    "Antoni": "ErXwobaYiN019PkySvjV",
    "Elli": "MF3mGyEYCl7XYWbV9V6O",
    "Josh": "TxGEqnHWrfWFTfGW9XjX"
}

TONE_MAP = {
    "Romantic": "sensual, romantic, literary",
    "NSFW": "detailed erotic, emotional, mature",
    "Hardcore": "intense, vulgar, graphic, pornographic"
}

MODELS = [
    "nothingiisreal/mn-celeste-12b",
    "openchat/openchat-3.5-0106",
    "gryphe/mythomax-l2-13b",
    "nousresearch/nous-capybara-7b",
    "cognitivecomputations/dolphin-mixtral"
]

# --- Core LLM via OpenRouter ---
def call_openrouter(prompt, model, max_tokens=1800):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://narrativax.app",
        "X-Title": "NarrativaX"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.95,
        "max_tokens": max_tokens
    }
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

# --- Book Builder ---
def generate_outline(prompt, genre, tone, chapters, model):
    q = f"You are a ghostwriter. Create a full outline for a {tone} {genre} novel with {chapters} chapters."
    q += f" Include title, foreword, intro, {chapters} chapters and final words. Concept: {prompt}"
    return call_openrouter(q, model)

def generate_section(title, outline, model):
    prompt = f"Write the full section '{title}' based on this outline:
{outline}
Keep it rich, immersive and genre consistent."
    return call_openrouter(prompt, model)

def generate_full_book(outline, chapters, model, update_progress):
    sections = ["Foreword", "Introduction"] + [f"Chapter {i+1}" for i in range(chapters)] + ["Final Words"]
    total = len(sections)
    book_data = {}
    for i, sec in enumerate(sections):
        book_data[sec] = generate_section(sec, outline, model)
        update_progress((i+1) / total)
    return book_data

# --- Characters & Cover ---
def generate_characters(prompt, genre, tone, model):
    q = f"Generate 3 characters for a {tone} {genre} story. Concept:
{prompt}"
    return call_openrouter(q, model)

def generate_character_image(desc):
    url = "https://api.replicate.com/v1/predictions"
    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "version": "db21e45e14aa502f98f4df6736d3f6e18f87827d7c642a14970df61aeb06d519",
        "input": {
            "prompt": desc + ", fantasy illustration, ultra-detailed",
            "width": 768,
            "height": 1024
        }
    }
    r = requests.post(url, headers=headers, json=data)
    r.raise_for_status()
    poll_url = r.json()["urls"]["get"]
    while True:
        result = requests.get(poll_url, headers=headers).json()
        if result["status"] == "succeeded":
            return result["output"][0]
        elif result["status"] == "failed":
            raise RuntimeError("Image gen failed.")

def generate_cover(prompt): return generate_character_image(prompt + ", full book cover")

# --- TTS ---
def chunk_text(text, max_tokens=400): return textwrap.wrap(text, max_tokens, break_long_words=False)

def narrate_story(text, voice_id, retries=3):
    chunks = chunk_text(text)
    path = f"narration_{voice_id}.mp3"
    for attempt in range(retries):
        try:
            with open(path, "wb") as f:
                for part in chunks:
                    stream = generate(text=part, voice=voice_id, model="eleven_monolingual_v1", stream=True)
                    for chunk in stream: f.write(chunk)
            return path
        except Exception as e:
            st.warning(f"TTS {attempt+1} failed: {e}")
            time.sleep(2)
    # fallback
    try:
        fallback = f"fallback_{voice_id}.mp3"
        engine = pyttsx3.init()
        engine.save_to_file(text, fallback)
        engine.runAndWait()
        return fallback
    except Exception as e:
        st.error("TTS fallback failed.")
        return None

# --- Export ---
def export_docx(book_data):
    doc = Document()
    for k, v in book_data.items():
        doc.add_heading(k, level=1)
        doc.add_paragraph(v)
    f = NamedTemporaryFile(delete=False, suffix=".docx")
    doc.save(f.name)
    return f.name

def export_pdf(book_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for k, v in book_data.items():
        pdf.set_font("Arial", style="B", size=14)
        pdf.cell(200, 10, k, ln=True)
        pdf.set_font("Arial", size=12)
        for line in v.splitlines():
            pdf.multi_cell(0, 10, line)
    f = NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(f.name)
    return f.name

# --- UI ---
st.set_page_config(page_title="NarrativaX", layout="wide")
st.title("NarrativaX — AI Ghostwriter OS")

prompt = st.text_area("Book Concept:", height=160)
genre = st.selectbox("Genre", ["Erotica", "Dark Fantasy", "Sci-Fi", "Romance", "Thriller"])
tone = st.selectbox("Explicitness", list(TONE_MAP.keys()))
chapter_count = st.slider("Chapters", 6, 20, 10)
model = st.selectbox("LLM Model", MODELS)
voice = st.selectbox("Voice", list(VOICES.keys()))
voice_id = VOICES[voice]

# --- Main ---
progress = st.empty()
if st.button("Generate Book"):
    with st.spinner("Generating outline..."):
        outline = generate_outline(prompt, genre, TONE_MAP[tone], chapter_count, model)
        st.session_state.outline = outline
    with st.spinner("Generating book..."):
        book = generate_full_book(outline, chapter_count, model, lambda p: progress.progress(p))
        st.session_state.book = book

if "book" in st.session_state:
    st.subheader("Chapters")
    for k, v in st.session_state.book.items():
        with st.expander(k, expanded=True):
            st.markdown(v, unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1,1,2])
            with col1:
                if st.button(f"Narrate {k}", key=f"voice_{k}"):
                    audio = narrate_story(v, voice_id)
                    st.audio(audio)
            with col2:
                if st.button(f"Continue Writing: {k}", key=f"cont_{k}"):
                    add = call_openrouter(f"Expand the following with intelligent continuation:

{v}", model)
                    st.session_state.book[k] += "\n\n" + add
                    st.markdown(add)
            with col3:
                if st.button(f"Illustrate {k}", key=f"img_{k}"):
                    try:
                        img = generate_character_image(prompt + " " + k)
                        st.image(img, use_container_width=True)
                    except:
                        st.warning("Image failed")

    st.subheader("Export")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Download DOCX"):
            path = export_docx(st.session_state.book)
            st.download_button("Download DOCX", open(path, "rb"), file_name="book.docx")
    with c2:
        if st.button("Download PDF"):
            path = export_pdf(st.session_state.book)
            st.download_button("Download PDF", open(path, "rb"), file_name="book.pdf")

    st.subheader("Generate Cover")
    if st.button("Create Cover"):
        url = generate_cover(prompt)
        st.image(url, use_container_width=True)

    st.subheader("Characters")
    if st.button("Generate Characters"):
        chars = generate_characters(prompt, genre, TONE_MAP[tone], model)
        st.text_area("Character Profiles", chars, height=250)
        st.session_state.characters = chars
    if "characters" in st.session_state:
        if st.button("Visualize Characters"):
            for i, desc in enumerate(st.session_state.characters.split("\n\n")[:3]):
                try:
                    url = generate_character_image(desc)
                    st.image(url, caption=f"Character {i+1}", use_container_width=True)
                except:
                    st.warning(f"Image failed for character {i+1}")
