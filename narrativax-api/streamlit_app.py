# streamlit_app.py — NarrativaX Final Pro Version
# Includes: full book builder, chapter playback, character AI, SDXL covers, model selection, save/resume

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

# --- Config ---
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

MODEL_MAP = {
    "Celeste 12B (Creative)": "nothingiisreal/mn-celeste-12b",
    "MythoMax (Balanced)": "gryphe/mythomax-l2-13b",
    "Dolphin (Fast)": "cognitivecomputations/dolphin-2.2.1-mistral-7b",
    "Hermes 2 (Conversational)": "nousresearch/nous-hermes-2-mixtral"
}

# --- LLM Generation ---
def call_openrouter(prompt, model_id):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://narrativax.app",
        "X-Title": "NarrativaX"
    }
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.95,
        "max_tokens": 1800
    }
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

# --- Book ---
def generate_outline(prompt, genre, tone, chapters, model_id):
    q = f"""You are a ghostwriter. Create a full outline for a {tone} {genre} book with {chapters} chapters.
    Include: Title, Foreword, Introduction, Chapter titles, Final Words.
    Theme: {prompt}"""
    return call_openrouter(q, model_id)

def generate_full_book(outline, chapters, model_id):
    data = {}
    for i, sec in enumerate(["Foreword", "Introduction"] + [f"Chapter {i+1}" for i in range(chapters)] + ["Final Words"]):
        st.info(f"Writing {sec}... ({i+1}/{chapters+3})")
        p = f"Write the full section '{sec}' based on this outline:\n{outline}\nMake it immersive and on-tone."
        data[sec] = call_openrouter(p, model_id)
        st.progress((i+1) / (chapters+3))
    return data

def continue_section(title, outline, model_id):
    q = f"Continue and extend the section '{title}' in the same style. Use the following outline:\n{outline}"
    return call_openrouter(q, model_id)

# --- Character + Cover ---
def generate_characters(prompt, genre, tone, model_id):
    q = f"""Generate 3 vivid characters for a {tone} {genre} story about: {prompt}.
    Format: Name, Role, Appearance, Personality, Motivation, Secret (optional)"""
    return call_openrouter(q, model_id)

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
    r = requests.post(url, headers=headers, json=json_data)
    r.raise_for_status()
    poll_url = r.json()["urls"]["get"]
    while True:
        result = requests.get(poll_url, headers=headers).json()
        if result["status"] == "succeeded":
            return result["output"][0]
        elif result["status"] == "failed":
            raise RuntimeError("Image failed.")

def generate_cover(prompt):
    return generate_character_image(prompt + ", full book cover, high fantasy")

# --- Narration ---
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
st.set_page_config(page_title="NarrativaX Studio", layout="wide")
st.title("NarrativaX — AI Ghostwriter & Publisher")

prompt = st.text_area("Story Idea:", height=200)
genre = st.selectbox("Genre", list(["Erotica", "Dark Fantasy", "Sci-Fi", "Romance", "Thriller"]))
tone = st.selectbox("Tone", list(TONE_MAP.keys()))
model_name = st.selectbox("OpenRouter Model", list(MODEL_MAP.keys()))
model_id = MODEL_MAP[model_name]
chapters = st.slider("Number of Chapters", 6, 20, 10)
voice = st.selectbox("Narrator", list(VOICES.keys()))
voice_id = VOICES[voice]

col1, col2 = st.columns(2)
with col1:
    if st.button("Generate Book"):
        with st.spinner("Creating Outline..."):
            outline = generate_outline(prompt, genre, TONE_MAP[tone], chapters, model_id)
            st.session_state.outline = outline
        with st.spinner("Generating Book..."):
            book = generate_full_book(outline, chapters, model_id)
            st.session_state.book = book
            st.success("Book Ready!")
            st.balloons()

with col2:
    if st.button("Save Progress"):
        st.session_state.saved = {
            "prompt": prompt,
            "outline": st.session_state.get("outline", ""),
            "book": st.session_state.get("book", {})
        }
        st.success("Session Saved.")

if "saved" in st.session_state:
    if st.button("Resume Saved Session"):
        st.session_state.update(st.session_state.saved)
        st.success("Session Restored.")

# --- Book Output ---
if "book" in st.session_state:
    st.subheader("Book Output & Controls")
    for k, v in st.session_state.book.items():
        with st.expander(f"{k}"):
            st.text_area("Generated Text", v, key=f"view-{k}", height=400)
            if st.button(f"Narrate {k}", key=f"narrate-{k}"):
                audio = narrate_story(v, voice_id)
                st.audio(audio)
            if st.button(f"Continue Writing {k}", key=f"cont-{k}"):
                cont = continue_section(k, st.session_state.outline, model_id)
                st.session_state.book[k] += "\n" + cont
                st.experimental_rerun()

    st.subheader("Export Book")
    if st.button("Download DOCX"):
        path = export_docx(st.session_state.book)
        st.download_button("📄 Download DOCX", open(path, "rb"), file_name="NarrativaX_Book.docx")

    if st.button("Download PDF"):
        path = export_pdf(st.session_state.book)
        st.download_button("📄 Download PDF", open(path, "rb"), file_name="NarrativaX_Book.pdf")

    st.subheader("Generate Cover")
    if st.button("Create Cover"):
        url = generate_cover(prompt)
        st.image(url, caption="AI Book Cover", use_container_width=True)

    st.subheader("Build Characters")
    if st.button("Generate Characters"):
        chars = generate_characters(prompt, genre, TONE_MAP[tone], model_id)
        st.session_state.characters = chars
        st.text_area("Characters", chars, height=300)

    if "characters" in st.session_state:
        if st.button("Visualize Characters"):
            for i, profile in enumerate(st.session_state.characters.split("\n\n")[:3]):
                try:
                    img = generate_character_image(profile)
                    st.image(img, caption=f"Character {i+1}", use_container_width=True)
                except:
                    st.warning(f"Image failed for Character {i+1}")
