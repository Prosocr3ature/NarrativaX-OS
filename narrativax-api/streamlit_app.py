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

def call_openrouter(prompt, model="nothingiisreal/mn-celeste-12b"):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://yourapp.vercel.app",
        "X-Title": "NarrativaX"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.95,
        "max_tokens": 1600
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

def generate_full_book(outline):
    sections = ["Foreword", "Introduction", "Chapter 1", "Chapter 2", "Chapter 3", "Chapter 4", "Chapter 5", "Final Words"]
    book_data = {}
    for section in sections:
        content_prompt = f"Write the full section '{section}' based on this outline: {outline}\nMake it immersive and consistent in tone."
        book_data[section] = call_openrouter(content_prompt)
    return book_data

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

def generate_cover(prompt):
    url = "https://api.replicate.com/v1/predictions"
    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    json_data = {
        "version": "db21e45e14aa502f98f4df6736d3f6e18f87827d7c642a14970df61aeb06d519",  # SDXL 1.0
        "input": {
            "prompt": prompt + ", highly detailed, full book cover design, vibrant",
            "width": 1024,
            "height": 1024
        }
    }
    response = requests.post(url, headers=headers, json=json_data)
    response.raise_for_status()
    prediction = response.json()
    status_url = prediction["urls"]["get"]
    while True:
        poll = requests.get(status_url, headers=headers)
        result = poll.json()
        if result["status"] == "succeeded":
            return result["output"][0]
        elif result["status"] == "failed":
            raise RuntimeError("Image generation failed")

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

# Streamlit UI
st.set_page_config(page_title="NarrativaX AI Studio", layout="centered")
st.title("NarrativaX: Complete AI Book Ghostwriter")

prompt = st.text_area("Enter your book concept:")
genre = st.selectbox("Choose genre", ["Dark Fantasy", "Sci-Fi", "Erotica", "Thriller", "Romance"])
tone = st.selectbox("Explicitness", ["Romantic", "NSFW", "Hardcore"])
voice_name = st.selectbox("Narrator Voice", list(VOICES.keys()))
voice_id = VOICES[voice_name]

if st.button("Generate Full Book"):
    with st.spinner("Generating outline and full content..."):
        try:
            outline = generate_outline(prompt, genre, TONE_MAP[tone])
            st.session_state["outline"] = outline
            st.text(outline)
            book_data = generate_full_book(outline)
            st.session_state["book_data"] = book_data
            st.success("Book generated!")
            for k, v in book_data.items():
                st.markdown(f"### {k}")
                st.markdown(v)
        except Exception as e:
            st.error(e)

if "book_data" in st.session_state:
    st.subheader("Narrate Entire Book")
    full_story = "\n\n".join(st.session_state["book_data"].values())
    if st.button("Narrate with ElevenLabs"):
        path = narrate_story(full_story, voice_id)
        st.audio(path)

    st.subheader("Generate Cover")
    if st.button("Create Book Cover"):
        try:
            img_url = generate_cover(prompt + ", cinematic fantasy illustration for book cover")
            st.image(img_url, caption="AI Cover", use_container_width=True)
        except Exception as e:
            st.error(f"Cover generation failed: {e}")

    st.subheader("Export")
    if st.button("Download .docx"):
        f = export_docx(st.session_state["book_data"])
        st.download_button("Download DOCX", open(f, "rb"), file_name="book.docx")
    if st.button("Download .pdf"):
        f = export_pdf(st.session_state["book_data"])
        st.download_button("Download PDF", open(f, "rb"), file_name="book.pdf")
