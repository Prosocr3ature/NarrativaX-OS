import os, time, textwrap, requests, json
import streamlit as st
from docx import Document
from fpdf import FPDF
from tempfile import NamedTemporaryFile
from gtts import gTTS
import replicate
from streamlit_themes import set_theme

# THEME SETUP
set_theme({"base": "dark", "primaryColor": "#ff4b4b", "backgroundColor": "#0e1117", "secondaryBackgroundColor": "#262730", "textColor": "#fafafa", "font": "sans serif"})

# KEYS
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
replicate_client = replicate.Client(api_token=REPLICATE_API_TOKEN)

# CONFIG
VOICES = {"Rachel": "default", "Bella": "default", "Antoni": "default", "Elli": "default", "Josh": "default"}
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
IMAGE_MODELS = {
    "Reliberate V3 (Erotica/NSFW)": "asiryan/reliberate-v3:d70438fcb9bb7adb8d6e59cf236f754be0b77625e984b8595d1af02cdf034b29",
    "Stable Diffusion (General Purpose)": "stability-ai/stable-diffusion:ac732df83cea7fff18b8472768c88ad041fa750ff7682a21affe81863cbe77e4"
}
GENRES = [
    "Erotica", "Dark Fantasy", "Sci-Fi", "Romance", "Thriller", "Adventure", "Historical Fiction",
    "Mystery", "Fantasy", "Drama", "Slice of Life", "Teen Fiction", "Horror", "Cyberpunk",
    "Psychological", "Crime", "LGBTQ+", "Action", "Paranormal"
]

if "last_saved" not in st.session_state:
    st.session_state.last_saved = None
if "feedback_history" not in st.session_state:
    st.session_state.feedback_history = []

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
    return call_openrouter(f"You are a ghostwriter. Create a complete outline for a {tone} {genre} novel with {chapters} chapters. Include: Title, Foreword, Introduction, {chapters} chapter titles, Final Words. Concept: {prompt}", model)

def generate_section(title, outline, model):
    return call_openrouter(f"Write the section '{title}' in full based on this outline:\n{outline}", model)

def generate_full_book(outline, chapters, model):
    book = {}
    sections = ["Foreword", "Introduction"] + [f"Chapter {i+1}" for i in range(chapters)] + ["Final Words"]
    progress = st.progress(0)
    for idx, sec in enumerate(sections):
        book[sec] = generate_section(sec, outline, model)
        progress.progress((idx + 1) / len(sections))
    return book

def generate_characters(prompt, genre, tone, model):
    return call_openrouter(f"Generate 3 unique characters for a {tone} {genre} story based on this: {prompt}. Format: Name, Role, Appearance, Personality, Motivation, Secret.", model)

def generate_image(prompt, model_key="Reliberate V3 (Erotica/NSFW)"):
    with st.spinner("Generating image..."):
        try:
            model = IMAGE_MODELS[model_key]
            input_args = {
                "prompt": prompt,
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
                "width": 768,
                "height": 1024
            }
            if "stable-diffusion" in model:
                input_args["scheduler"] = "K_EULER"
            output = replicate_client.run(model, input=input_args)
            return output[0]
        except Exception as e:
            st.error(f"Image generation failed: {str(e)}")
            return None

def generate_cover(prompt, model_key="Reliberate V3 (Erotica/NSFW)"):
    return generate_image(prompt + ", full book cover, illustration", model_key)

def narrate_story(text, voice_id=None):
    try:
        tts = gTTS(text)
        filename = f"narration_{voice_id or 'default'}.mp3"
        tts.save(filename)
        return filename
    except Exception as e:
        st.error(f"TTS failed: {e}")
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

def save_session_json():
    if "book" in st.session_state:
        with open("session.json", "w") as f:
            json.dump(st.session_state.book, f)
        st.session_state.last_saved = time.time()

def load_session_json():
    try:
        with open("session.json") as f:
            st.session_state.book = json.load(f)
    except Exception as e:
        st.warning(f"Could not load session: {e}")

# All remaining UI logic goes here after this block...
