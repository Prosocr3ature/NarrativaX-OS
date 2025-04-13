# NarrativaX — Final Version with TTS retry, fallback, and model selection

import os, time, textwrap, requests, pyttsx3
import streamlit as st
from docx import Document
from fpdf import FPDF
from tempfile import NamedTemporaryFile
from elevenlabs.client import ElevenLabs

# API KEYS
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
eleven_client = ElevenLabs(api_key=ELEVEN_API_KEY)

# VOICES
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
    q = f"""You are a ghostwriter. Create a complete outline for a {tone} {genre} novel with {chapters} chapters.
    Include:
    - Title
    - Foreword
    - Introduction
    - {chapters} chapter titles
    - Final Words
    Concept: {prompt}"""
    return call_openrouter(q, model)

def generate_section(title, outline, model):
    p = f"Write the section '{title}' in full based on this outline:\n{outline}\nMake it intelligent, immersive, and genre consistent."
    return call_openrouter(p, model)

def generate_full_book(outline, chapters, model):
    book_data = {}
    for sec in ["Foreword", "Introduction"] + [f"Chapter {i+1}" for i in range(chapters)] + ["Final Words"]:
        book_data[sec] = generate_section(sec, outline, model)
    return book_data

# --- Characters ---
def generate_characters(prompt, genre, tone, model):
    q = f"""Generate 3 unique characters for a {tone} {genre} story based on this:
    {prompt}
    Format:
    Name, Role, Appearance, Personality, Motivation, Secret (optional)"""
    return call_openrouter(q, model)

def generate_character_image(desc):
    url = "https://api.replicate.com/v1/predictions"
    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    json_data = {
        "version": "db21e45e14aa502f98f4df6736d3f6e18f87827d7c642a14970df61aeb06d519",
        "input": {
            "prompt": desc + ", cinematic fantasy portrait, ultra-detailed",
            "width": 768,
            "height": 1024
        }
    }
    res = requests.post(url, headers=headers, json=json_data)
    res.raise_for_status()
    poll_url = res.json()["urls"]["get"]
    while True:
        check = requests.get(poll_url, headers=headers).json()
        if check["status"] == "succeeded":
            return check["output"][0]
        elif check["status"] == "failed":
            raise RuntimeError("Character image generation failed.")

# --- Cover ---
def generate_cover(prompt):
    return generate_character_image(prompt + ", full book cover")

# --- TTS ---
def chunk_text(text, max_tokens=400):
    return textwrap.wrap(text, max_tokens, break_long_words=False)

def narrate_story(text, voice_id, retries=3):
    chunks = chunk_text(text)
    path = f"narration_{voice_id}.mp3"
    for attempt in range(retries):
        try:
            with open(path, "wb") as f:
                for part in chunks:
                    stream = eleven_client.text_to_speech.convert(
                        voice_id=voice_id,
                        model_id="eleven_monolingual_v1",
                        text=part,
                        stream=True
                    )
                    for chunk in stream:
                        f.write(chunk)
            return path
        except Exception as e:
            st.warning(f"TTS attempt {attempt+1} failed: {e}")
            time.sleep(2)
    fallback = f"fallback_{voice_id}.mp3"
    try:
        engine = pyttsx3.init()
        engine.save_to_file(text, fallback)
        engine.runAndWait()
        return fallback
    except Exception as fe:
        st.error(f"Local TTS failed too: {fe}")
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

# --- Flow ---
if st.button("Generate Book"):
    with st.spinner("Outlining and writing..."):
        outline = generate_outline(prompt, genre, TONE_MAP[tone], chapter_count, model)
        st.session_state.outline = outline
        book = generate_full_book(outline, chapter_count, model)
        st.session_state.book = book

if "book" in st.session_state:
    st.subheader("Book Chapters")
    for k, v in st.session_state.book.items():
        with st.expander(k, expanded=True):
            st.markdown(v, unsafe_allow_html=True)
            if st.button(f"Narrate {k}", key=f"voice_{k}"):
                audio = narrate_story(v, voice_id)
                st.audio(audio)
            if st.button(f"Continue Writing: {k}", key=f"continue_{k}"):
                added = call_openrouter(f"Expand the chapter: {v}", model)
                st.session_state.book[k] += "\n" + added
                st.markdown(added)

    st.subheader("Export")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Export DOCX"):
            path = export_docx(st.session_state.book)
            st.download_button("Download .docx", open(path, "rb"), file_name="book.docx")
    with col2:
        if st.button("Export PDF"):
            path = export_pdf(st.session_state.book)
            st.download_button("Download .pdf", open(path, "rb"), file_name="book.pdf")

    st.subheader("Book Cover")
    if st.button("Generate Cover"):
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
