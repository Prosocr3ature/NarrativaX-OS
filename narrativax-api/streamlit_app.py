import os, time, textwrap, requests, json, uuid
import streamlit as st
from docx import Document
from fpdf import FPDF
from tempfile import NamedTemporaryFile
from gtts import gTTS
import replicate
from streamlit_browser_cookie_manager import get_cookie, set_cookie

# KEYS
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
replicate_client = replicate.Client(api_token=REPLICATE_API_TOKEN)

# CONFIGS
VOICES = {"Rachel": "default", "Bella": "default", "Antoni": "default", "Elli": "default", "Josh": "default"}
TONE_MAP = {
    "Romantic": "sensual, romantic, literary",
    "NSFW": "detailed erotic, emotional, mature",
    "Hardcore": "intense, vulgar, graphic, pornographic"
}
MODELS = [
    "nothingiisreal/mn-celeste-12b", "openchat/openchat-3.5-0106",
    "gryphe/mythomax-l2-13b", "nousresearch/nous-capybara-7b",
    "cognitivecomputations/dolphin-mixtral"
]
IMAGE_MODELS = {
    "Reliberate V3 (Erotica/NSFW)": "asiryan/reliberate-v3:latest",
    "Stable Diffusion (General Purpose)": "stability-ai/stable-diffusion:ac732df..."
}
GENRES = [
    "Erotica", "Dark Fantasy", "Sci-Fi", "Romance", "Thriller", "Adventure", "Historical Fiction",
    "Mystery", "Fantasy", "Drama", "Slice of Life", "Teen Fiction", "Horror", "Cyberpunk",
    "Psychological", "Crime", "LGBTQ+", "Action", "Paranormal"
]

# STATE INIT
if "last_saved" not in st.session_state:
    st.session_state.last_saved = None
if "feedback_history" not in st.session_state:
    st.session_state.feedback_history = []
if "characters" not in st.session_state:
    st.session_state.characters = {}

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
    return call_openrouter(f"Generate 3 unique characters for a {tone} {genre} story. Format: Name, Role, Appearance, Personality, Motivation, Secret.\nPrompt: {prompt}", model)

def generate_image(prompt, model_key):
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
        st.error(f"Image error: {e}")
        return None

def generate_cover(prompt, model_key):
    return generate_image(prompt + ", full book cover", model_key)

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
        set_cookie("narrativax_session", json.dumps(st.session_state.book), max_age_days=7)
        st.session_state.last_saved = time.time()

def load_cookie_session():
    data = get_cookie("narrativax_session")
    if data:
        try:
            st.session_state.book = json.loads(data)
        except:
            st.warning("Could not load session.")

# UI CONFIG
st.set_page_config(page_title="NarrativaX Studio", layout="wide")
load_cookie_session()

with st.sidebar:
    st.image("https://i.imgur.com/vGV9N5k.png", width=200)
    st.markdown("**NarrativaX v2**")
    if st.session_state.last_saved:
        st.info(f"Last saved {int(time.time() - st.session_state.last_saved)}s ago")
    st.button("Save Now", on_click=save_session_json)

with st.expander("AI Story Settings", expanded=True):
    prompt = st.text_area("Book Idea", height=150)
    genre_type = st.radio("Genre Type", ["Normal", "Adult"], horizontal=True)
    genre_list = [g for g in GENRES if (genre_type == "Adult") == (g in ["Erotica", "NSFW", "Hardcore"])]
    genre = st.selectbox("Genre", genre_list)
    tone = st.selectbox("Tone", list(TONE_MAP.keys()))
    chapter_count = st.slider("Chapters", 6, 20, 8)
    model = st.selectbox("LLM Model", MODELS)

voice = st.selectbox("Voice", list(VOICES.keys()))
img_model = st.selectbox("Image Model", list(IMAGE_MODELS.keys()))

tabs = st.tabs(["Book", "Narration", "Illustrations", "Export", "Characters", "Feedback"])

# Tab: Book
with tabs[0]:
    if st.button("Create Book"):
        outline = generate_outline(prompt, genre, TONE_MAP[tone], chapter_count, model)
        st.session_state.outline = outline
        st.session_state.book = generate_full_book(outline, chapter_count, model)
        save_session_json()
    if "book" in st.session_state:
        for title, content in st.session_state.book.items():
            with st.expander(title):
                st.markdown(content)
                if st.button(f"Regenerate {title}", key=f"regen_{title}"):
                    st.session_state.book[title] = generate_section(title, st.session_state.outline, model)
                    st.experimental_rerun()

# Tab: Narration
with tabs[1]:
    if "book" in st.session_state:
        for title, content in st.session_state.book.items():
            if st.button(f"Narrate {title}", key=f"narrate_{title}"):
                audio = narrate_story(content, VOICES[voice])
                if audio:
                    st.audio(audio)

# Tab: Illustrations
with tabs[2]:
    if "book" in st.session_state:
        for title, content in st.session_state.book.items():
            if st.button(f"Illustrate {title}", key=f"img_{title}"):
                img_url = generate_image(content[:300], img_model)
                if img_url:
                    st.image(img_url, caption=title)

# Tab: Export
with tabs[3]:
    if "book" in st.session_state:
        if st.button("Export DOCX"):
            path = export_docx(st.session_state.book)
            st.download_button("Download DOCX", open(path, "rb"), file_name="book.docx")
        if st.button("Export PDF"):
            path = export_pdf(st.session_state.book)
            st.download_button("Download PDF", open(path, "rb"), file_name="book.pdf")

# Tab: Characters
with tabs[4]:
    new_char_name = st.text_input("Character Name")
    new_char_prompt = st.text_area("Character Description")
    if st.button("Generate Character"):
        output = generate_characters(new_char_prompt or prompt, genre, TONE_MAP[tone], model)
        st.session_state.characters[new_char_name or f"Char_{uuid.uuid4()}"] = output
    for name, profile in st.session_state.characters.items():
        with st.expander(f"{name}"):
            st.markdown(profile)
            if st.button(f"Regenerate Image for {name}"):
                img_url = generate_image(profile, model_key=img_model)
                if img_url:
                    st.image(img_url, caption=name)

# Tab: Feedback
with tabs[5]:
    with st.form("feedback_form"):
        feedback = st.text_area("Feedback or suggestions")
        submitted = st.form_submit_button("Submit")
        if submitted:
            st.session_state.feedback_history.append(feedback)
            st.success("Thanks — feedback stored.")
    for entry in st.session_state.feedback_history[-5:]:
        st.info(entry)
