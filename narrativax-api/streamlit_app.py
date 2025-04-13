# streamlit_app.py — NarrativaX Final Enhanced Version
# Features: Book Builder, SDXL Covers + Chapter Art, TTS Retry, Continue Writing, Export, Model Selector

import os, time, textwrap, requests, pyttsx3
import streamlit as st
from docx import Document
from fpdf import FPDF
from tempfile import NamedTemporaryFile
from elevenlabs import generate
from elevenlabs.client import ElevenLabs

# KEYS
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
eleven_client = ElevenLabs(api_key=ELEVEN_API_KEY)

# CONFIG
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

def generate_outline(prompt, genre, tone, chapters, model):
    return call_openrouter(
        f"You are a ghostwriter. Create a complete outline for a {tone} {genre} novel with {chapters} chapters. Include: Title, Foreword, Introduction, {chapters} chapter titles, Final Words. Concept: {prompt}",
        model)

def generate_section(title, outline, model):
    return call_openrouter(f"Write the section '{title}' in full based on this outline:
{outline}", model)

def generate_full_book(outline, chapters, model):
    book = {}
    for sec in ["Foreword", "Introduction"] + [f"Chapter {i+1}" for i in range(chapters)] + ["Final Words"]:
        book[sec] = generate_section(sec, outline, model)
    return book

def generate_characters(prompt, genre, tone, model):
    return call_openrouter(
        f"Generate 3 unique characters for a {tone} {genre} story based on this: {prompt}. Format: Name, Role, Appearance, Personality, Motivation, Secret.",
        model)

def generate_image(prompt):
    headers = {"Authorization": f"Token {REPLICATE_API_TOKEN}", "Content-Type": "application/json"}
    data = {
        "version": "db21e45e14aa502f98f4df6736d3f6e18f87827d7c642a14970df61aeb06d519",
        "input": {"prompt": prompt, "width": 768, "height": 1024}
    }
    r = requests.post("https://api.replicate.com/v1/predictions", headers=headers, json=data)
    r.raise_for_status()
    poll_url = r.json()["urls"]["get"]
    while True:
        check = requests.get(poll_url, headers=headers).json()
        if check["status"] == "succeeded":
            return check["output"][0]
        elif check["status"] == "failed":
            raise RuntimeError("Image generation failed.")
        time.sleep(1)

def generate_cover(prompt):
    return generate_image(prompt + ", full book cover, illustration")

def chunk_text(text, max_tokens=400):
    return textwrap.wrap(text, max_tokens, break_long_words=False)

def narrate_story(text, voice_id, retries=3):
    chunks = chunk_text(text)
    path = f"narration_{voice_id}.mp3"
    for attempt in range(retries):
        try:
            with open(path, "wb") as f:
                for part in chunks:
                    stream = generate(text=part, voice=voice_id, model="eleven_monolingual_v1", stream=True)
                    for chunk in stream:
                        f.write(chunk)
            return path
        except Exception as e:
            st.warning(f"TTS failed {attempt+1}: {e}")
            time.sleep(2)
    try:
        engine = pyttsx3.init()
        engine.save_to_file(text, f"fallback_{voice_id}.mp3")
        engine.runAndWait()
        return f"fallback_{voice_id}.mp3"
    except Exception as e:
        st.error(f"Local fallback failed: {e}")
        return None

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

# --- UI ---
st.set_page_config(page_title="NarrativaX Studio", layout="wide")
st.title("NarrativaX — AI Book Creation Studio")

prompt = st.text_area("Book Idea:", height=200)
genre = st.selectbox("Genre", ["Erotica", "Dark Fantasy", "Sci-Fi", "Romance", "Thriller"])
tone = st.selectbox("Tone", list(TONE_MAP.keys()))
chapter_count = st.slider("Chapters", 6, 20, 8)
model = st.selectbox("Choose LLM", MODELS)
voice = st.selectbox("Voice", list(VOICES.keys()))
voice_id = VOICES[voice]

if st.button("Create Full Book"):
    with st.spinner("Generating outline and chapters..."):
        outline = generate_outline(prompt, genre, TONE_MAP[tone], chapter_count, model)
        st.session_state.outline = outline
        book = generate_full_book(outline, chapter_count, model)
        st.session_state.book = book

if "book" in st.session_state:
    st.subheader("Read, Expand or Narrate")
    for title, content in st.session_state.book.items():
        with st.expander(title, expanded=True):
            st.markdown(content)
            if st.button(f"Narrate {title}", key=f"narrate_{title}"):
                audio = narrate_story(content, voice_id)
                st.audio(audio)
            if st.button(f"Continue Writing: {title}", key=f"cont_{title}"):
                addition = call_openrouter(f"Expand and continue this: {content}", model)
                st.session_state.book[title] += "
" + addition
                st.markdown(addition)
            if st.button(f"Generate Illustration for {title}", key=f"img_{title}"):
                img_url = generate_image(content[:300])
                st.image(img_url, caption=f"{title} Art", use_container_width=True)

    st.subheader("Export Book")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("DOCX"):
            path = export_docx(st.session_state.book)
            st.download_button("Download DOCX", open(path, "rb"), file_name="book.docx")
    with col2:
        if st.button("PDF"):
            path = export_pdf(st.session_state.book)
            st.download_button("Download PDF", open(path, "rb"), file_name="book.pdf")

    st.subheader("Generate Book Cover")
    if st.button("Cover Illustration"):
        cover = generate_cover(prompt)
        st.image(cover, caption="Cover", use_container_width=True)

    st.subheader("Characters")
    if st.button("Generate Characters"):
        chars = generate_characters(prompt, genre, TONE_MAP[tone], model)
        st.text_area("Character Profiles", chars, height=200)
        st.session_state.characters = chars
    if "characters" in st.session_state:
        if st.button("Visualize Characters"):
            for i, desc in enumerate(st.session_state.characters.split("

")[:3]):
                try:
                    url = generate_image(desc)
                    st.image(url, caption=f"Character {i+1}", use_container_width=True)
                except:
                    st.warning(f"Image generation failed: Character {i+1}")
