# streamlit_app.py
import os
import streamlit as st
import requests
import textwrap
from docx import Document
from fpdf import FPDF
from tempfile import NamedTemporaryFile
from elevenlabs.client import ElevenLabs

# Setup
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
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

# Story generator

def call_openrouter(prompt, model="mistralai/mistral-7b-instruct"):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://yourapp.vercel.app",
        "X-Title": "NarrativaX"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9,
        "max_tokens": 1200
    }
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def generate_outline(title_prompt, genre, tone):
    outline_prompt = f"""
    You are a ghostwriter. Create a complete outline for a {tone} {genre} novel:
    - Title
    - Foreword
    - Introduction
    - At least 6 chapter titles
    - Final Words
    The concept is: {title_prompt}
    """
    return call_openrouter(outline_prompt)


def generate_section(section_title, outline):
    content_prompt = f"Write the full section '{section_title}' based on this outline: {outline}\nMake it immersive and consistent in tone."
    return call_openrouter(content_prompt)

# Narration

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

# Cover

def generate_cover(prompt):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024"
    }
    r = requests.post("https://api.openai.com/v1/images/generations", headers=headers, json=data)
    r.raise_for_status()
    return r.json()["data"][0]["url"]

# Export

def export_docx(book_data):
    doc = Document()
    for k, v in book_data.items():
        doc.add_heading(k, level=1)
        doc.add_paragraph(v)
    temp = NamedTemporaryFile(delete=False, suffix=".docx")
    doc.save(temp.name)
    return temp.name


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
    temp = NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp.name)
    return temp.name

# UI
st.set_page_config(page_title="NarrativaX AI Publishing Studio", layout="centered")
st.title("NarrativaX: Professional AI Ghostwriter")

prompt = st.text_area("Enter your book concept:")
genre = st.selectbox("Choose genre", ["Dark Fantasy", "Sci-Fi", "Erotica", "Thriller", "Romance"])
tone = st.selectbox("Explicitness", ["Romantic", "NSFW", "Hardcore"])
voice_name = st.selectbox("Narrator Voice", list(VOICES.keys()))
voice_id = VOICES[voice_name]

if st.button("Generate Outline"):
    with st.spinner("Crafting book structure..."):
        try:
            outline = generate_outline(prompt, genre, TONE_MAP[tone])
            st.session_state["outline"] = outline
            st.success("Outline created!")
            st.text(outline)
        except Exception as e:
            st.error(e)

if "outline" in st.session_state:
    book_data = {}
    st.subheader("Generate Sections")
    sections = ["Foreword", "Introduction", "Chapter 1", "Chapter 2", "Chapter 3", "Chapter 4", "Chapter 5", "Final Words"]
    for section in sections:
        if st.button(f"Write {section}"):
            with st.spinner(f"Writing {section}..."):
                result = generate_section(section, st.session_state["outline"])
                book_data[section] = result
                st.session_state["book_data"] = book_data
                st.success(f"{section} completed!")
                st.markdown(result)

    if "book_data" in st.session_state:
        st.markdown("---")
        st.subheader("Narrate Book")
        full_story = "\n\n".join(st.session_state["book_data"].values())
        if st.button("Narrate with ElevenLabs"):
            path = narrate_story(full_story, voice_id)
            st.audio(path)

        st.subheader("Generate Cover")
        if st.button("Create Book Cover"):
            img = generate_cover(prompt + ", full illustrated novel book cover")
            st.image(img, caption="AI Cover", use_container_width=True)

        st.subheader("Export")
        if st.button("Download .docx"):
            f = export_docx(st.session_state["book_data"])
            st.download_button("Download DOCX", open(f, "rb"), file_name="book.docx")
        if st.button("Download .pdf"):
            f = export_pdf(st.session_state["book_data"])
            st.download_button("Download PDF", open(f, "rb"), file_name="book.pdf")
