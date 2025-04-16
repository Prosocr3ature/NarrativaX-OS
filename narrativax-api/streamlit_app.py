Continue 

Perfect. You’re choosing an efficient, low-cost and App Store-free route for launching NarrativaX as a mobile-optimized Progressive Web App (PWA) using Streamlit + Progressier. Here’s the complete plan and final implementation:

⸻

PWA-Ready Deployment Plan for NarrativaX

⸻

1. Stack Summary
	•	Frontend UI: Streamlit (optimized for mobile).
	•	PWA Wrapper: Progressier — for installability, push notifications, offline support.
	•	Backend: Built-in Streamlit server OR optionally extended with FastAPI for async routes.
	•	Assets: All icons, metadata, splash screens configured.
	•	API Key & Safety Logic: Already integrated with adult-mode gating, tone filtering, and uncensored mode toggle.
	•	Offline Installation (iPhone/iPad): “Add to Home Screen” via Safari.

⸻

2. Final Exportable Version for Streamlit + PWA

Below is the final unified app.py file you will deploy and register in Progressier:

You’ll also need manifest.json, service-worker.js, and icon assets which Progressier auto-generates when linking your app.

# app.py — Streamlit + NarrativaX PWA Core

import os, time, json, requests
import streamlit as st
from docx import Document
from fpdf import FPDF
from tempfile import NamedTemporaryFile
from gtts import gTTS
import replicate
from streamlit_sortables import sort_items

# --- CONFIG & CONSTANTS ---
st.set_page_config(page_title="NarrativaX", page_icon="🪶", layout="wide")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
replicate_client = replicate.Client(api_token=REPLICATE_API_TOKEN)

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
    "Realistic Vision v5.1": "lucataco/realistic-vision-v5.1:2c8e954decbf70b7607a4414e5785ef9e4de4b8c51d50fb8b8b349160e0ef6bb",
    "Reliberate V3 (NSFW)": "asiryan/reliberate-v3:d70438fcb9bb7adb8d6e59cf236f754be0b77625e984b8595d1af02cdf034b29"
}
SAFE_IMAGE_MODELS = {k: v for k, v in IMAGE_MODELS.items() if "NSFW" not in k}
GENRES = [
    "Adventure", "Dark Fantasy", "Sci-Fi", "Romance", "Thriller", "Historical Fiction", "Mystery",
    "Fantasy", "Drama", "Slice of Life", "Teen Fiction", "Horror", "Cyberpunk", "Psychological",
    "Crime", "LGBTQ+", "Action", "Paranormal"
]
ADULT_GENRES = ["Erotica", "NSFW", "Hardcore"]
GENRES += ADULT_GENRES

# --- SESSION INIT ---
def init_state():
    defaults = {
        "last_saved": None, "feedback_history": [], "characters": [], "chapter_order": [],
        "book": {}, "outline": "", "is_adult": False, "adult_confirmed": False
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
init_state()

# --- SAFETY LOGIC ---
def is_adult_mode():
    return genre in ADULT_GENRES or tone in TONE_MAP and "NSFW" in TONE_MAP[tone]

def require_adult_confirmation():
    if not st.session_state.adult_confirmed:
        with st.expander("⚠️ Adult Mode Consent Required", expanded=True):
            st.error("This content may contain mature or explicit themes. Viewer discretion is advised.")
            st.markdown("By continuing, you confirm you're **18 years or older** and agree to view uncensored content.")
            if st.button("I am 18+ and I understand"):
                st.session_state.adult_confirmed = True
            st.stop()

# --- API CALLS ---
def call_openrouter(prompt, model, max_tokens=1800):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json",
        "HTTP-Referer": "https://narrativax.app", "X-Title": "NarrativaX"
    }
    payload = {
        "model": model, "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.95, "max_tokens": max_tokens
    }
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def generate_outline(prompt, genre, tone, chapters, model):
    return call_openrouter(f"You are a ghostwriter. Create a complete outline for a {tone} {genre} novel with {chapters} chapters. Include: Title, Foreword, Introduction, {chapters} chapter titles, Final Words. Concept: {prompt}", model)

def generate_section(title, outline, model):
    return call_openrouter(f"Write only the section '{title}' in full detail based on the following outline:\n{outline}\n\nSection: {title}", model)

def generate_full_book(outline, chapters, model):
    book = {}
    sections = ["Foreword", "Introduction"] + [f"Chapter {i+1}" for i in range(chapters)] + ["Final Words"]
    progress = st.progress(0)
    for i, section in enumerate(sections):
        witty = ["Sharpening the quill...", "Pouring ink on the page...", "Whispering ideas to AI...", "Plotting the twist...", "Turning thoughts into text..."][i % 5]
        st.write(witty)
        book[section] = generate_section(section, outline, model)
        progress.progress((i + 1) / len(sections))
    st.session_state.chapter_order = sections
    return book

def generate_image(prompt, model_key):
    if is_adult_mode() and not st.session_state.adult_confirmed:
        require_adult_confirmation()
    model = IMAGE_MODELS[model_key]
    args = {"prompt": prompt[:300], "num_inference_steps": 30, "guidance_scale": 7.5, "width": 768, "height": 1024}
    return replicate_client.run(model, input=args)[0]

def narrate_story(text, voice_id=None):
    text = text.replace("\n", " ")
    tts = gTTS(text)
    filename = f"narration_{voice_id or 'default'}.mp3"
    tts.save(filename)
    return filename

# --- UI ---
st.title("NarrativaX — AI Book Studio 🪶")

with st.sidebar:
    st.image("https://i.imgur.com/vGV9N5k.png", width=180)
    st.info("Tap 'Add to Home Screen' to install NarrativaX on iPhone/iPad.")
    st.markdown("**Version**: 3.2 | **PWA** Ready")
    st.markdown("---")

    if st.session_state.last_saved:
        st.success(f"Last saved: {int(time.time() - st.session_state.last_saved)}s ago")

    if st.button("Save Project"): save_path = "session.json"; json.dump(st.session_state.book, open(save_path, "w"))
    if st.button("Load Project"):
        try:
            st.session_state.book = json.load(open("session.json"))
            st.session_state.chapter_order = list(st.session_state.book.keys())
            st.success("Session loaded successfully!")
        except Exception as e:
            st.error(f"Failed to load session: {e}")

# --- Settings ---
with st.expander("AI Book Settings", expanded=True):
    prompt = st.text_area("Book Idea / Concept", height=150)
    genre_type = st.radio("Content Type", ["Normal", "Adult"], horizontal=True)
    genre_list = [g for g in GENRES if (genre_type == "Adult") == (g in ADULT_GENRES)]
    genre = st.selectbox("Genre", genre_list)
    tone = st.selectbox("Tone", list(TONE_MAP.keys()))
    chapter_count = st.slider("Number of Chapters", 6, 20, 10)
    model = st.selectbox("Text Model", MODELS)
    voice = st.selectbox("Narration Voice", list(VOICES.keys()))
    img_model = st.selectbox("Image Model", list(SAFE_IMAGE_MODELS.keys()) if not is_adult_mode() else list(IMAGE_MODELS.keys()))

# --- Book Generation ---
if st.button("Create Full Book"):
    if is_adult_mode():
        require_adult_confirmation()
    with st.spinner("Crafting your story..."):
        st.session_state.outline = generate_outline(prompt, genre, TONE_MAP[tone], chapter_count, model)
        st.session_state.book = generate_full_book(st.session_state.outline, chapter_count, model)
        st.success("Book created!")

# --- Book View ---
if st.session_state.book:
    st.header("Generated Book")
    new_order = sort_items(st.session_state.chapter_order)
    if new_order:
        st.session_state.chapter_order = new_order

    for title in st.session_state.chapter_order:
        with st.expander(title):
            st.markdown(st.session_state.book[title])
            if st.button(f"Regenerate {title}", key=f"regen_{title}"):
                st.session_state.book[title] = generate_section(title, st.session_state.outline, model)

# --- Narration ---
st.header("Narration")
for title in st.session_state.book:
    with st.expander(f"🔊 {title}"):
        if st.button(f"Read Aloud: {title}", key=f"tts_{title}"):
            audio_file = narrate_story(st.session_state.book[title], voice)
            st.audio(audio_file)

# --- Illustration ---
st.header("Illustrate Book")
if st.session_state.book:
    for title, content in st.session_state.book.items():
        if st.button(f"Generate Image: {title}", key=f"img_{title}"):
            image_url = generate_image(content, img_model)
            if image_url:
                st.image(image_url, caption=title)

# --- Export ---
st.header("Export Your Book")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Export to DOCX"):
        doc = Document()
        for title, text in st.session_state.book.items():
            doc.add_heading(title, level=1)
            doc.add_paragraph(text)
        file = NamedTemporaryFile(delete=False, suffix=".docx")
        doc.save(file.name)
        st.download_button("Download DOCX", open(file.name, "rb"), file_name="NarrativaX_Book.docx")

with col2:
    if st.button("Export to PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for title, text in st.session_state.book.items():
            pdf.set_font("Arial", style="B", size=14)
            pdf.cell(200, 10, title, ln=True)
            pdf.set_font("Arial", size=12)
            for line in text.splitlines():
                pdf.multi_cell(0, 10, line)
        f = NamedTemporaryFile(delete=False, suffix=".pdf")
        pdf.output(f.name)
        st.download_button("Download PDF", open(f.name, "rb"), file_name="NarrativaX_Book.pdf")

with col3:
    if st.button("Export as JSON"):
        json_data = json.dumps(st.session_state.book)
        st.download_button("Download JSON", json_data, file_name="NarrativaX_Book.json")

# --- Feedback ---
st.header("Feedback")
with st.form("feedback_form"):
    feedback = st.text_area("Help us improve NarrativaX!", height=100)
    submitted = st.form_submit_button("Submit Feedback")
    if submitted:
        st.session_state.feedback_history.append(feedback)
        st.success("Thanks for your feedback!")

# --- Footer ---
st.markdown("---")
st.caption("© 2025 NarrativaX. Built with AI, with respect to human imagination.")
