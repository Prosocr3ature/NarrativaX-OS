# streamlit_app.py

import os
import requests
import textwrap
import zipfile
from PIL import Image
from io import BytesIO
from tempfile import NamedTemporaryFile
from docx import Document
from fpdf import FPDF
import streamlit as st
from elevenlabs.client import ElevenLabs

# === API KEYS ===
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
eleven_client = ElevenLabs(api_key=ELEVEN_API_KEY)

# === SETTINGS ===
VOICES = {
    "Rachel": "EXAVITQu4vr4xnSDxMaL",
    "Bella": "29vD33N1CtxCmqQRPOHJ",
    "Antoni": "ErXwobaYiN019PkySvjV",
    "Elli": "MF3mGyEYCl7XYWbV9V6O",
    "Josh": "TxGEqnHWrfWFTfGW9XjX"
}

TONE_MAP = {
    "Romantic": "sensual, romantic, emotional",
    "NSFW": "detailed erotic, mature, uncensored",
    "Hardcore": "extreme, graphic, adult-only"
}

# === OPENROUTER CALL ===
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

# === STORY STRUCTURE ===
def generate_outline(prompt, genre, tone):
    q = f"You are a ghostwriter. Write a full novel outline for a {tone} {genre} story. Include title, foreword, intro, 10+ chapter names, final words. Theme: {prompt}"
    return call_openrouter(q)

def generate_section(title, outline, memory):
    p = f"Write the section '{title}' in full based on this outline:
{outline}
Memory:
{memory}"
    return call_openrouter(p)

# === IMAGE GENERATION (SDXL) ===
def generate_cover_image(prompt):
    url = "https://api.replicate.com/v1/predictions"
    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "version": "db21e45e14aa502f98f4df6736d3f6e18f87827d7c642a14970df61aeb06d519",
        "input": {
            "prompt": prompt + ", fantasy cover art, masterpiece, 4k",
            "width": 768,
            "height": 1024
        }
    }
    res = requests.post(url, headers=headers, json=data)
    res.raise_for_status()
    result = res.json()
    get_url = result["urls"]["get"]

    # Poll until complete
    while True:
        check = requests.get(get_url, headers=headers).json()
        if check["status"] == "succeeded":
            return check["output"][0]
        elif check["status"] == "failed":
            raise RuntimeError("Cover generation failed.")

# === TEXT TO AUDIO ===
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

# === EXPORT ===
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

def export_zip(docx, pdf, cover_url):
    img = Image.open(BytesIO(requests.get(cover_url).content))
    zip_temp = NamedTemporaryFile(delete=False, suffix=".zip")
    img_path = zip_temp.name.replace(".zip", ".png")
    img.save(img_path)

    with zipfile.ZipFile(zip_temp.name, "w") as zipf:
        zipf.write(docx, "book.docx")
        zipf.write(pdf, "book.pdf")
        zipf.write(img_path, "cover.png")

    return zip_temp.name

# === UI ===
st.set_page_config(page_title="NarrativaX | AI Bookwriter", layout="centered")
st.title("NarrativaX â Advanced AI Book Ghostwriter")

with st.expander("**Choose Book Settings**", expanded=True):
    prompt = st.text_area("What's your story about?", height=150)
    genre = st.selectbox("Genre", ["Erotica", "Dark Fantasy", "Sci-Fi", "Romance", "Thriller"])
    tone = st.selectbox("Explicitness Level", list(TONE_MAP.keys()))
    voice_name = st.selectbox("Voice for narration", list(VOICES.keys()))
    voice_id = VOICES[voice_name]

if st.button("Generate Complete Book"):
    with st.spinner("Creating outline..."):
        outline = generate_outline(prompt, genre, TONE_MAP[tone])
        st.session_state.outline = outline
        st.success("Outline ready!")

    memory = ""
    book_data = {}
    sections = ["Foreword", "Introduction"] + [f"Chapter {i}" for i in range(1, 11)] + ["Final Words"]
    for sec in sections:
        with st.spinner(f"Writing {sec}..."):
            content = generate_section(sec, outline, memory)
            book_data[sec] = content
            memory += f"\n{content}"

    st.session_state.book_data = book_data
    st.success("Book generation complete!")
    st.subheader("Live Preview")
    for k, v in book_data.items():
        st.markdown(f"### {k}")
        st.markdown(v)

if "book_data" in st.session_state:
    st.subheader("Narrate & Export")

    if st.button("Narrate Full Book"):
        audio_path = narrate_story("\n\n".join(st.session_state.book_data.values()), voice_id)
        st.audio(audio_path, format="audio/mp3")

    if st.button("Generate Cover Image"):
        img_url = generate_cover_image(prompt)
        st.image(img_url, caption="AI Generated Cover", use_container_width=True)
        st.session_state.cover_url = img_url

    if st.button("Export ZIP Bundle"):
        docx_path = export_docx(st.session_state.book_data)
        pdf_path = export_pdf(st.session_state.book_data)
        zip_path = export_zip(docx_path, pdf_path, st.session_state.cover_url)
        with open(zip_path, "rb") as f:
            st.download_button("Download Full Book Bundle (.zip)", f, file_name="NarrativaX_Book.zip", mime="application/zip")
