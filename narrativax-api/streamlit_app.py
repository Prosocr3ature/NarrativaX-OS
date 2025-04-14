import os, time, textwrap, requests, pyttsx3, json
import streamlit as st
from docx import Document
from fpdf import FPDF
from tempfile import NamedTemporaryFile
from gtts import gTTS
import replicate

# KEYS
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
replicate_client = replicate.Client(api_token=REPLICATE_API_TOKEN)

# CONFIG
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

# --- AI UTILS ---
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
    return call_openrouter(f"""Write the section '{title}' in full based on this outline:\n{outline}""", model)

def generate_full_book(outline, chapters, model):
    book = {}
    sections = ["Foreword", "Introduction"] + [f"Chapter {i+1}" for i in range(chapters)] + ["Final Words"]
    progress = st.progress(0)
    for idx, sec in enumerate(sections):
        book[sec] = generate_section(sec, outline, model)
        progress.progress((idx + 1) / len(sections))
    return book

def generate_characters(prompt, genre, tone, model):
    return call_openrouter(
        f"Generate 3 unique characters for a {tone} {genre} story based on this: {prompt}. Format: Name, Role, Appearance, Personality, Motivation, Secret.",
        model)

# --- IMAGE GENERATION ---
def generate_image(prompt):
    with st.spinner("Generating image..."):
        try:
            output = replicate_client.run(
                "asiryan/reliberate-v3:d70438fcb9bb7adb8d6e59cf236f754be0b77625e984b8595d1af02cdf034b29",
                input={
                    "prompt": prompt,
                    "num_inference_steps": 30,
                    "guidance_scale": 7.5,
                    "width": 768,
                    "height": 1024
                }
            )
            return output[0]
        except Exception as e:
            st.error(f"Image generation failed: {str(e)}")
            return None

def generate_cover(prompt):
    return generate_image(prompt + ", full book cover, illustration")

def chunk_text(text, max_tokens=400):
    return textwrap.wrap(text, max_tokens, break_long_words=False)

def narrate_story(text, retries=3):
    try:
        tts = gTTS(text, lang='en', tld='co.uk')
        path = "narration.mp3"
        tts.save(path)
        return path
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

def load_session_json():
    try:
        with open("session.json") as f:
            st.session_state.book = json.load(f)
    except Exception as e:
        st.warning(f"Could not load session: {e}")

# --- UI ---
st.set_page_config(page_title="NarrativaX Studio", layout="wide")
st.title("NarrativaX — AI Book Creation Studio")

col3, col4 = st.columns(2)
with col3:
    if st.button("Save Session to File"):
        save_session_json()
        st.success("Session saved.")
    st.download_button("Download Session JSON", json.dumps(st.session_state.get("book", {})), file_name="session.json")
with col4:
    if st.button("Load Session from File"):
        load_session_json()

prompt = st.text_area("Book Idea:", height=200)
genre = st.selectbox("Genre", ["Erotica", "Dark Fantasy", "Sci-Fi", "Romance", "Thriller"])
tone = st.selectbox("Tone", list(TONE_MAP.keys()))
chapter_count = st.slider("Chapters", 6, 20, 8)
model = st.selectbox("Choose LLM", MODELS)

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
                audio = narrate_story(content)
                st.audio(audio)
            if st.button(f"Continue Writing: {title}", key=f"cont_{title}"):
                addition = call_openrouter(f"Expand and continue this: {content}", model)
                st.session_state.book[title] += "\n\n" + addition
                st.markdown(addition)
            if st.button(f"Generate Illustration for {title}", key=f"img_{title}"):
                img_url = generate_image(content[:300])
                if img_url:
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
        if cover:
            st.image(cover, caption="Cover", use_container_width=True)

    st.subheader("Characters")
    if st.button("Generate Characters"):
        chars = generate_characters(prompt, genre, TONE_MAP[tone], model)
        st.text_area("Character Profiles", chars, height=200)
        st.session_state.characters = chars
    if "characters" in st.session_state:
        if st.button("Visualize Characters"):
            for i, desc in enumerate(st.session_state.characters.split("\n\n")[:3]):
                try:
                    url = generate_image(desc)
                    if url:
                        st.image(url, caption=f"Character {i+1}", use_container_width=True)
                except:
                    st.warning(f"Image generation failed: Character {i+1}")
