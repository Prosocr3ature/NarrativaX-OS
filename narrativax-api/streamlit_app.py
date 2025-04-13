import os
import streamlit as st
import requests
from io import BytesIO
from PIL import Image
from elevenlabs.client import ElevenLabs

# ENV setup
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

# ElevenLabs client
eleven_client = ElevenLabs(api_key=ELEVEN_API_KEY)

# UI setup
st.set_page_config(page_title="NarrativaX AI", layout="centered")
st.title("NarrativaX AI Story Generator")

# Inputs
prompt = st.text_area("Describe your story idea", height=200)
voice = st.selectbox("Choose narrator voice", ["Rachel", "Bella", "Antoni", "Elli", "Josh"])

# Generate story from OpenRouter
def generate_story(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://narrativax.vercel.app",
        "X-Title": "NarrativaX",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openrouter/openchat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.85,
        "max_tokens": 700
    }
    res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]

# Generate image with DALL·E 3
def generate_cover(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}"
    }
    payload = {
        "model": "openai/dall-e-3",
        "prompt": f"Book cover illustration: {prompt}",
        "size": "1024x1024",
        "n": 1
    }
    res = requests.post("https://openrouter.ai/api/v1/images/generations", headers=headers, json=payload)
    res.raise_for_status()
    return res.json()["data"][0]["url"]

# Narrate story with ElevenLabs
def narrate_story(text, voice):
    audio = eleven_client.text_to_speech.convert(
        voice=voice,
        model="eleven_monolingual_v1",
        text=text
    )
    out_path = f"story_{voice}.mp3"
    with open(out_path, "wb") as f:
        f.write(audio)
    return out_path

# Buttons
if st.button("Generate Story"):
    with st.spinner("Writing your story..."):
        try:
            story = generate_story(prompt)
            st.success("Here's your story:")
            st.markdown(story)
            st.session_state.story = story
        except Exception as e:
            st.error(f"Story generation failed: {e}")

if st.button("Generate Cover"):
    if "story" in st.session_state:
        with st.spinner("Generating cover..."):
            try:
                url = generate_cover(st.session_state.story[:300])
                st.image(url, caption="AI-Generated Cover", use_column_width=True)
            except Exception as e:
                st.error(f"Cover generation failed: {e}")
    else:
        st.warning("Generate a story first.")

if st.button("Narrate Story"):
    if "story" in st.session_state:
        with st.spinner("Narrating..."):
            try:
                audio_file = narrate_story(st.session_state.story, voice)
                st.audio(audio_file)
            except Exception as e:
                st.error(f"Narration failed: {e}")
    else:
        st.warning("Generate a story first.")
