# streamlit_app.py — NarrativaX Final Version
# Includes: full book builder, chapter playback, character AI, SDXL covers

import os
import streamlit as st
import requests
import textwrap
from docx import Document
from fpdf import FPDF
from tempfile import NamedTemporaryFile
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

# --- CORE LLM GENERATION ---
def call_openrouter(prompt, model="nothingiisreal/mn-celeste-12b"):
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
        "max_tokens": 1800
    }
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

# --- BOOK BUILDER ---
def generate_outline(prompt, genre, tone, chapters):
    q = f"""
    You are a ghostwriter. Create a complete outline for a {tone} {genre} novel with {chapters} chapters.
    Include:
    - Title
    - Foreword
    - Introduction
    - {chapters} chapter titles
    - Final Words
    Concept: {prompt}
    """
    return call_openrouter(q)

def generate_full_book(outline, chapters):
    book_data = {}
    for sec in ["Foreword", "Introduction"] + [f"Chapter {i+1}" for i in range(chapters)] + ["Final Words"]:
        prompt = f"""Write the section '{sec}' in full based on this outline:\n{outline}\nMake it intelligent, immersive, and genre consistent."""
        book_data[sec] = call_openrouter(prompt)
    return book_data

# --- CHARACTERS ---
def generate_characters(prompt, genre, tone):
    q = f"""
    Generate 3 unique characters for a {tone} {genre} story based on this:
    {prompt}
    Format:
    Name, Role, Appearance, Personality, Motivation, Secret (optional)
    """
    return call_openrouter(q)

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

# --- COVER IMAGE ---
def generate_cover(prompt):
    return generate_character_image(prompt + ", book cover")

# --- AUDIO ---
def chunk_text(text, max_tokens=400):
    return textwrap.wrap(text, max_tokens, break_long_words=False)

def narrate_story(text, voice_id):
    chunks = chunk_text(text)
    path = f"narration_{voice_id}.mp3"
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

# --- EXPORT ---
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
st.set_page_config(page_title="NarrativaX Studio", layout="centered")
st.title("NarrativaX — AI-Powered Book Creator")

prompt = st.text_area("Story Idea:")
genre = st.selectbox("Genre", ["Erotica", "Dark Fantasy", "Sci-Fi", "Romance", "Thriller"])
tone = st.selectbox("Tone", list(TONE_MAP.keys()))
chapter_count = st.slider("Number of Chapters", 6, 20, 8)
voice = st.selectbox("Voice", list(VOICES.keys()))
voice_id = VOICES[voice]

if st.button("Generate Book"):
    with st.spinner("Outlining and writing..."):
        outline = generate_outline(prompt, genre, TONE_MAP[tone], chapter_count)
        st.session_state.outline = outline
        st.text_area("Outline", outline)
        book = generate_full_book(outline, chapter_count)
        st.session_state.book = book
        for k, v in book.items():
            with st.expander(k):
                st.markdown(v)

if "book" in st.session_state:
    st.subheader("Narrate by Chapter")
    for k, v in st.session_state.book.items():
        with st.expander(k):
            st.markdown(v)
            if st.button(f"Narrate {k}", key=k):
                path = narrate_story(v, voice_id)
                st.audio(path)

    st.subheader("Export Book")
    if st.button("Download DOCX"):
        path = export_docx(st.session_state.book)
        st.download_button("DOCX", open(path, "rb"))
    if st.button("Download PDF"):
        path = export_pdf(st.session_state.book)
        st.download_button("PDF", open(path, "rb"))

    st.subheader("Generate Cover")
    if st.button("Create Cover"):
        img_url = generate_cover(prompt)
        st.image(img_url, caption="Book Cover", use_container_width=True)

    st.subheader("Character Generator")
    if st.button("Build Characters"):
        chars = generate_characters(prompt, genre, TONE_MAP[tone])
        st.text_area("Character Profiles", chars, height=300)
        st.session_state.characters = chars

    if "characters" in st.session_state:
        if st.button("Visualize Characters"):
            for i, profile in enumerate(st.session_state.characters.split("\n\n")[:3]):
                try:
                    url = generate_character_image(profile)
                    st.image(url, caption=f"Character {i+1}", use_container_width=True)
                except:
                    st.warning(f"Image failed for Character {i+1}")
