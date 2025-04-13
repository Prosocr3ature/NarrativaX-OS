# narrativax-api/streamlit_app.py

import os
import streamlit as st
import requests
from io import BytesIO
from PIL import Image
from elevenlabs import generate, play, set_api_key

# OpenRouter (uncensored model) and ElevenLabs API keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
set_api_key(os.getenv("ELEVEN_API_KEY"))

# Available voice options
VOICES = ["Rachel", "Bella", "Antoni", "Elli", "Josh"]

# Generate story via OpenRouter (Dolphin Mixtral)
def generate_story(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "cognitivecomputations/dolphin-mixtral-8x22b",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# DALL·E cover generation
def generate_cover_image(prompt):
    openai_key = os.getenv("OPENAI_API_KEY")
    dalle_url = "https://api.openai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {openai_key}"}
    json_data = {"prompt": prompt, "n": 1, "size": "512x512"}

    response = requests.post(dalle_url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()["data"][0]["url"]

# Narrate story with ElevenLabs
def narrate_story(story, voice):
    audio_stream = generate(text=story, voice=voice, model="eleven_monolingual_v1")
    audio_path = f"narration_{voice}.mp3"
    with open(audio_path, "wb") as f:
        for chunk in audio_stream:
            f.write(chunk)
    return audio_path

# Streamlit interface
st.set_page_config(page_title="NarrativaX AI Story Generator", layout="centered")
st.title("NarrativaX AI Story Generator")

story_prompt = st.text_area("Describe your story idea:", height=200)
voice_option = st.selectbox("Choose narrator voice", VOICES)

if st.button("Generate Story"):
    with st.spinner("Summoning uncensored story..."):
        try:
            story_text = generate_story(story_prompt)
            st.session_state.story_text = story_text
            st.success("Here's your story:")
            st.markdown(story_text)
        except Exception as e:
            st.error(f"Story generation failed: {e}")

if st.button("Generate Cover Image"):
    if "story_text" in st.session_state:
        with st.spinner("Creating cover with DALL·E..."):
            try:
                image_url = generate_cover_image(st.session_state.story_text[:150])
                st.image(image_url, caption="AI-Generated Cover", use_column_width=True)
            except Exception as e:
                st.error(f"Cover generation failed: {e}")
    else:
        st.warning("Generate a story first.")

if st.button("Narrate Story with ElevenLabs"):
    if "story_text" in st.session_state:
        with st.spinner("Narrating..."):
            try:
                audio_path = narrate_story(st.session_state.story_text, voice=voice_option)
                st.audio(audio_path)
            except Exception as e:
                st.error(f"Narration failed: {e}")
    else:
        st.warning("Generate a story first.")
