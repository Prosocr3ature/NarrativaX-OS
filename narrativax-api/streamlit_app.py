# streamlit_app.py — NarrativaX Final Version
# Includes: full book builder, continue-writing, multiple LLMs, character AI, SDXL covers, progress bar

import os
import streamlit as st
import requests
import textwrap
from docx import Document
from fpdf import FPDF
from tempfile import NamedTemporaryFile
from elevenlabs.client import ElevenLabs

# --- API KEYS ---
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

MODELS = {
    "Celeste-12B": "nothingiisreal/mn-celeste-12b",
    "MythoMax-L2": "gryphe/mythomax-l2-13b",
    "Dolphin-Mixtral": "austism/dolphin-mixtral-8x7b",
    "OpenHermes 2.5 Mistral": "teknium/OpenHermes-2.5-Mistral-7B"
}

# --- CORE LLM CALL ---
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

# --- BOOK ---
def generate_outline(prompt, genre, tone, chapters, model):
    q = f"""
    You are a ghostwriter. Create a complete outline for a {tone} {genre} novel with {chapters} chapters.
    Include Title, Foreword, Introduction, {chapters} chapter titles, Final Words.
    Concept: {prompt}
    """
    return call_openrouter(q, model)

def generate_full_book(outline, chapters, model, progress_callback):
    book_data = {}
    sections = ["Foreword", "Introduction"] + [f"Chapter {i+1}" for i in range(chapters)] + ["Final Words"]
    for i, sec in enumerate(sections):
        p = f"""Write the section '{sec}' in full based on this outline:\n{outline}\nMake it immersive and genre-consistent."""
        book_data[sec] = call_openrouter(p, model)
        progress_callback((i + 1) / len(sections))
    return book_data

def continue_writing(section_title, content, model):
    p = f"Continue the section '{section_title}' from this content:\n{content}"
    return call_openrouter(p, model)

# --- CHARACTERS ---
def generate_characters(prompt, genre, tone, model):
    q = f"""
    Generate 3 unique characters for a {tone} {genre} story:
    {prompt}
    Format: Name, Role, Appearance, Personality, Motivation, Secret (optional)
    """
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
    poll_url = res.json()["urls"]["get"]
    while True:
        poll = requests.get(poll_url, headers=headers).json()
        if poll["status"] == "succeeded":
            return poll["output"][0]
        elif poll["status"] == "failed":
            raise RuntimeError("Character image generation failed")

def generate_cover(prompt):
    return generate_character_image(prompt + ", full book cover design")

# --- AUDIO ---
def chunk_text(text, max_tokens=400):
    return textwrap.wrap(text, max_tokens, break_long_words=False)

def narrate_story(text, voice_id):
    path = f"narration_{voice_id}.mp3"
    with open(path, "wb") as f:
        for part in chunk_text(text):
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
st.title("NarrativaX — AI Book Ghostwriter")

prompt = st.text_area("Book Concept", height=160)
genre = st.selectbox("Genre", list(["Erotica", "Dark Fantasy", "Sci-Fi", "Romance", "Thriller"]))
tone = st.selectbox("Tone", list(TONE_MAP.keys()))
model_choice = st.selectbox("Model", list(MODELS.keys()))
model = MODELS[model_choice]
chapter_count = st.slider("Number of Chapters", 6, 20, 8)
voice = st.selectbox("Narrator", list(VOICES.keys()))
voice_id = VOICES[voice]

if st.button("Generate Book"):
    progress_bar = st.progress(0)
    with st.spinner("Outlining and writing..."):
        outline = generate_outline(prompt, genre, TONE_MAP[tone], chapter_count, model)
        st.session_state.outline = outline
        st.text_area("Outline", outline, height=280)
        book = generate_full_book(outline, chapter_count, model, progress_callback=progress_bar.progress)
        st.session_state.book = book
        for k, v in book.items():
            with st.expander(k):
                st.markdown(v)
                if st.button(f"Continue {k}", key=f"cont_{k}"):
                    continuation = continue_writing(k, v, model)
                    st.markdown("**Extended:**\n" + continuation)

if "book" in st.session_state:
    st.subheader("Narrate Book")
    for k, v in st.session_state.book.items():
        with st.expander(k):
            st.markdown(v)
            if st.button(f"Narrate {k}", key=k):
                path = narrate_story(v, voice_id)
                st.audio(path)

    st.subheader("Export Book")
    if st.button("Download DOCX"):
        path = export_docx(st.session_state.book)
        st.download_button("Download DOCX", open(path, "rb"), file_name="book.docx")
    if st.button("Download PDF"):
        path = export_pdf(st.session_state.book)
        st.download_button("Download PDF", open(path, "rb"), file_name="book.pdf")

    st.subheader("Book Cover")
    if st.button("Generate Cover"):
        img_url = generate_cover(prompt)
        st.image(img_url, caption="Book Cover", use_container_width=True)

    st.subheader("Characters")
    if st.button("Create Characters"):
        chars = generate_characters(prompt, genre, TONE_MAP[tone], model)
        st.text_area("Character Profiles", chars, height=300)
        st.session_state.characters = chars

    if "characters" in st.session_state:
        if st.button("Visualize Characters"):
            for i, profile in enumerate(st.session_state.characters.split("\n\n")[:3]):
                try:
                    img = generate_character_image(profile)
                    st.image(img, caption=f"Character {i+1}", use_container_width=True)
                except:
                    st.warning(f"Image failed for character {i+1}")
