# streamlit_app.py — NarrativaX v2.0
# Features: full book builder, continuation, chapter narration, image wrap

import os
import time
import textwrap
import streamlit as st
import requests
from tempfile import NamedTemporaryFile
from docx import Document
from fpdf import FPDF
from elevenlabs.client import ElevenLabs

# API Keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
eleven_client = ElevenLabs(api_key=ELEVEN_API_KEY)

# Constants
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
    "gryphe/mythomax-l2",
    "nothingiisreal/mn-celeste-12b",
    "austism/chronos-hermes-13b",
    "nousr/llava-hf"
]

# Core Generation
def call_openrouter(prompt, model):
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

def generate_outline(prompt, genre, tone, chapters, model):
    q = f"""You are a ghostwriter. Create a complete outline for a {tone} {genre} novel with {chapters} chapters.
    Include: Title, Foreword, Introduction, {chapters} chapter titles, Final Words. Concept: {prompt}"""
    return call_openrouter(q, model)

def generate_full_book(outline, chapters, model):
    book_data = {}
    sections = ["Foreword", "Introduction"] + [f"Chapter {i+1}" for i in range(chapters)] + ["Final Words"]
    progress = st.progress(0)
    for i, sec in enumerate(sections):
        p = f"""Write the section '{sec}' in full based on this outline:\n{outline}\nMake it intelligent, immersive, and genre consistent."""
        book_data[sec] = call_openrouter(p, model)
        progress.progress((i + 1) / len(sections))
    return book_data

def continue_chapter(section_text, model):
    continuation = call_openrouter(f"Continue this story in same style:\n{section_text}", model)
    return section_text + "\n\n" + continuation

# Characters & Cover
def generate_characters(prompt, genre, tone, model):
    q = f"""Generate 3 unique characters for a {tone} {genre} story based on: {prompt}
    Format: Name, Role, Appearance, Personality, Motivation, Secret (optional)"""
    return call_openrouter(q, model)

def generate_sdxl_image(desc, width=768, height=1024):
    url = "https://api.replicate.com/v1/predictions"
    headers = {"Authorization": f"Token {REPLICATE_API_TOKEN}", "Content-Type": "application/json"}
    data = {
        "version": "db21e45e14aa502f98f4df6736d3f6e18f87827d7c642a14970df61aeb06d519",
        "input": {"prompt": desc, "width": width, "height": height}
    }
    r = requests.post(url, headers=headers, json=data)
    status_url = r.json()["urls"]["get"]
    while True:
        res = requests.get(status_url, headers=headers).json()
        if res["status"] == "succeeded":
            return res["output"][0]
        elif res["status"] == "failed":
            raise RuntimeError("Image generation failed.")
        time.sleep(1)

def generate_cover(prompt):
    return generate_sdxl_image(prompt + ", cinematic book cover, intricate, trending on artstation", 1024, 1024)

def generate_book_wrap(prompt):
    return generate_sdxl_image(prompt + ", full wraparound book cover, spine, back cover, epic illustration", 2048, 1024)

# Narration
def chunk_text(text, max_tokens=400):
    return textwrap.wrap(text, max_tokens, break_long_words=False)

def narrate_story(text, voice_id):
    chunks = chunk_text(text)
    path = f"narration_{voice_id}.mp3"
    with open(path, "wb") as f:
        for part in chunks:
            stream = eleven_client.text_to_speech.convert(
                voice_id=voice_id, model_id="eleven_monolingual_v1", text=part, stream=True)
            for chunk in stream:
                f.write(chunk)
    return path

# Export
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
st.set_page_config(page_title="NarrativaX Studio", layout="wide")
st.title("NarrativaX — AI Book Ghostwriter & Publishing Studio")

prompt = st.text_area("Book Concept:", height=200)
genre = st.selectbox("Genre", ["Erotica", "Dark Fantasy", "Sci-Fi", "Romance", "Thriller"])
tone = st.selectbox("Tone", list(TONE_MAP.keys()))
model = st.selectbox("LLM Model", MODELS, index=0)
chapter_count = st.slider("Chapters", 6, 20, 8)
voice = st.selectbox("Narration Voice", list(VOICES.keys()))
voice_id = VOICES[voice]

if st.button("Generate Book"):
    with st.spinner("Creating outline and writing chapters..."):
        outline = generate_outline(prompt, genre, TONE_MAP[tone], chapter_count, model)
        st.session_state.outline = outline
        st.text_area("Outline", outline, height=200)
        book = generate_full_book(outline, chapter_count, model)
        st.session_state.book = book

if "book" in st.session_state:
    st.subheader("Your Book:")
    for k, v in st.session_state.book.items():
        with st.expander(k, expanded=False):
            st.markdown(v)
            if st.button(f"Continue Writing {k}", key=k):
                updated = continue_chapter(v, model)
                st.session_state.book[k] = updated
                st.experimental_rerun()
            if st.button(f"Narrate {k}", key=k + "_narrate"):
                path = narrate_story(v, voice_id)
                st.audio(path)

    st.subheader("Export")
    if st.button("Download .docx"):
        f = export_docx(st.session_state.book)
        st.download_button("Download DOCX", open(f, "rb"), file_name="book.docx")
    if st.button("Download .pdf"):
        f = export_pdf(st.session_state.book)
        st.download_button("Download PDF", open(f, "rb"), file_name="book.pdf")

    st.subheader("Book Cover")
    if st.button("Generate Cover"):
        img = generate_cover(prompt)
        st.image(img, use_container_width=True)

    if st.button("Generate Full Book Wrap"):
        img = generate_book_wrap(prompt)
        st.image(img, use_container_width=True)

    st.subheader("Characters")
    if st.button("Generate Characters"):
        chars = generate_characters(prompt, genre, TONE_MAP[tone], model)
        st.session_state.chars = chars
        st.text_area("Character Profiles", chars, height=300)

    if "chars" in st.session_state:
        if st.button("Visualize Characters"):
            for i, char in enumerate(st.session_state.chars.split("\n\n")):
                try:
                    img = generate_sdxl_image(char)
                    st.image(img, caption=f"Character {i+1}", use_container_width=True)
                except:
                    st.warning(f"Failed to render Character {i+1}")
