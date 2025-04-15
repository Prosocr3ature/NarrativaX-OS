import os, time, json, requests
import streamlit as st
from docx import Document
from fpdf import FPDF
from tempfile import NamedTemporaryFile
from gtts import gTTS
import replicate
from streamlit_sortables import sort_items

# --- CONFIG & CONSTANTS ---
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
    "Reliberate V3 (Erotica/NSFW)": "asiryan/reliberate-v3:d70438fcb9bb7adb8d6e59cf236f754be0b77625e984b8595d1af02cdf034b29",
    "Stable Diffusion (General Purpose)": "stability-ai/stable-diffusion:ac732df83cea7fff18b8472768c88ad041fa750ff7682a21affe81863cbe77e4"
}
GENRES = [
    "Erotica", "Dark Fantasy", "Sci-Fi", "Romance", "Thriller", "Adventure", "Historical Fiction",
    "Mystery", "Fantasy", "Drama", "Slice of Life", "Teen Fiction", "Horror", "Cyberpunk",
    "Psychological", "Crime", "LGBTQ+", "Action", "Paranormal"
]

# --- SESSION STATE INIT ---
def initialize_state():
    defaults = {
        "last_saved": None,
        "feedback_history": [],
        "characters": [],
        "chapter_order": [],
        "book": {},
        "outline": ""
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

initialize_state()

# --- API CALL FUNCTIONS ---
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
    st.session_state.chapter_order = sections.copy()
    return book

def generate_characters(prompt, genre, tone, model):
    result = call_openrouter(f"Generate 3 unique characters for a {tone} {genre} story based on this: {prompt}. Format: Name, Role, Appearance, Personality, Motivation, Secret.", model)
    return result.split("\n\n")

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

# --- EXPORT ---
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
            st.session_state.chapter_order = list(st.session_state.book.keys())
    except Exception as e:
        st.warning(f"Could not load session: {e}")

# --- UI ---
st.set_page_config(page_title="NarrativaX Studio", layout="wide")
st.title("NarrativaX — AI Book Creation Studio")

with st.sidebar:
    st.image("https://i.imgur.com/vGV9N5k.png", width=200)
    st.markdown("**NarrativaX v2**")
    if st.session_state.last_saved:
        st.info(f"Last saved {int(time.time() - st.session_state.last_saved)}s ago")
    if st.button("Save Now"): save_session_json()
    if st.button("Load Session"): load_session_json()

with st.expander("AI Story Settings", expanded=True):
    prompt = st.text_area("Book Idea", height=150)
    genre_type = st.radio("Genre Type", ["Normal", "Adult"], horizontal=True)
    genre_list = [g for g in GENRES if (genre_type == "Adult") == (g in ["Erotica", "NSFW", "Hardcore"])]
    genre = st.selectbox("Genre", genre_list)
    tone = st.selectbox("Tone", list(TONE_MAP.keys()))
    chapter_count = st.slider("Chapters", 6, 20, 8)
    model = st.selectbox("Choose LLM", MODELS)
    voice = st.selectbox("Voice", list(VOICES.keys()))
    img_model = st.selectbox("Image Model", list(IMAGE_MODELS.keys()))

# --- Tabs ---
tabs = st.tabs(["Book", "Narration", "Illustrations", "Export", "Characters", "Feedback"])

# Book Tab
with tabs[0]:
    if st.button("Create Full Book"):
        with st.spinner("Generating outline and chapters..."):
            outline = generate_outline(prompt, genre, TONE_MAP[tone], chapter_count, model)
            st.session_state.outline = outline
            st.session_state.book = generate_full_book(outline, chapter_count, model)
            save_session_json()

    if st.session_state.book:
        st.subheader("Reorder Chapters")
        reordered = sort_items(st.session_state.chapter_order)
        if reordered:
            st.session_state.chapter_order = reordered

        for title in st.session_state.chapter_order:
            content = st.session_state.book.get(title, "")
            with st.expander(title):
                st.markdown(content)
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"Regenerate {title}", key=f"regen_{title}"):
                        st.session_state.book[title] = generate_section(title, st.session_state.outline, model)
                with col2:
                    if st.button(f"AI Edit {title}", key=f"edit_{title}"):
                        instruction = st.text_input("Instruction", key=f"inst_{title}")
                        if instruction:
                            improved = call_openrouter(f"Please {instruction}:\n\n{content}", model)
                            st.session_state.book[title] = improved

# Narration Tab
with tabs[1]:
    if st.session_state.book:
        for title, content in st.session_state.book.items():
            with st.expander(f"\U0001F509 {title}"):
                if st.button(f"Narrate {title}", key=f"narrate_{title}"):
                    audio = narrate_story(content, VOICES[voice])
                    if audio:
                        st.audio(audio)

# Illustrations Tab
with tabs[2]:
    if st.session_state.book:
        for title, content in st.session_state.book.items():
            if st.button(f"Illustrate {title}", key=f"img_{title}"):
                img_url = generate_image(content[:300], model_key=img_model)
                if img_url:
                    st.image(img_url, caption=title, use_container_width=True)
        if st.button("Generate Book Cover"):
            cover = generate_cover(prompt, model_key=img_model)
            if cover:
                st.image(cover, caption="Book Cover", use_container_width=True)

# Export Tab
with tabs[3]:
    if st.session_state.book:
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Export DOCX"):
                path = export_docx(st.session_state.book)
                st.download_button("Download DOCX", open(path, "rb"), file_name="book.docx")
        with col2:
            if st.button("Export PDF"):
                path = export_pdf(st.session_state.book)
                st.download_button("Download PDF", open(path, "rb"), file_name="book.pdf")
        with col3:
            st.download_button("Download JSON", json.dumps(st.session_state.book), file_name="book.json")

# Characters Tab
with tabs[4]:
    st.subheader("Create & Visualize Characters")
    if st.button("Generate Characters"):
        chars = generate_characters(prompt, genre, TONE_MAP[tone], model)
        st.session_state.characters.extend(chars)

    for i, desc in enumerate(st.session_state.characters):
        with st.expander(f"Character {i+1}"):
            st.markdown(desc)
            edit_desc = st.text_area(f"Edit Description {i+1}", desc, key=f"edit_desc_{i}")
            if st.button(f"Update Character {i+1}", key=f"save_char_{i}"):
                st.session_state.characters[i] = edit_desc
            if st.button(f"Visualize {i+1}", key=f"viz_char_{i}"):
                url = generate_image(edit_desc, model_key=img_model)
                if url:
                    st.image(url, caption=f"Character {i+1}", use_container_width=True)

# Feedback Tab
with tabs[5]:
    st.subheader("Help us improve NarrativaX")
    with st.form("feedback_form"):
        feedback = st.text_area("What would you like to see improved?")
        submitted = st.form_submit_button("Submit")
        if submitted:
            st.session_state.feedback_history.append(feedback)
            st.success("Thank you! We'll adapt accordingly.")

    if st.session_state.feedback_history:
        st.markdown("### Past Feedback")
        for item in st.session_state.feedback_history[-5:]:
            st.info(item)
