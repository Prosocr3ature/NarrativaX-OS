# streamlit_app.py

import os
import streamlit as st
import requests
from PIL import Image
from io import BytesIO
from elevenlabs import save, play, set_api_key, Voice, VoiceSettings, generate

# Load environment keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

set_api_key(ELEVEN_API_KEY)

VOICES = ["Rachel", "Bella", "Antoni", "Elli", "Josh"]

# Story generation via Mistral model (OpenRouter)
def generate_story(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://yourdomain.com",
        "X-Title": "NarrativaX",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistralai/mistral-7b-instruct:free",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.9,
        "max_tokens": 800
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# Generate image via OpenAI DALL·E
def generate_cover_image(prompt):
    dalle_key = os.getenv("OPENAI_API_KEY")
    headers = {"Authorization": f"Bearer {dalle_key}"}
    json_data = {
        "prompt": prompt,
        "n": 1,
        "size": "512x512"
    }
    r = requests.post("https://api.openai.com/v1/images/generations", headers=headers, json=json_data)
    r.raise_for_status()
    return r.json()["data"][0]["url"]

# Narration
def narrate_story(text, voice):
    audio = generate(
        text=text,
        voice=voice,
        model="eleven_monolingual_v1",
        voice_settings=VoiceSettings(stability=0.4, similarity_boost=0.8)
    )
    path = f"{voice}_narration.mp3"
    save(audio, path)
    return path

# UI
st.set_page_config("NarrativaX - AI Story Studio")
st.title("NarrativaX AI Story Generator")

prompt = st.text_area("Describe your story idea:", height=200)
voice = st.selectbox("Choose narrator voice", VOICES)

if st.button("Generate Story"):
    with st.spinner("Summoning Mistral..."):
        try:
            story = generate_story(prompt)
            st.session_state.story_text = story
            st.success("Here's your story:")
            st.markdown(story)
        except Exception as e:
            st.error(f"Story generation failed: {e}")

if st.button("Generate Cover Image"):
    if "story_text" in st.session_state:
        with st.spinner("Creating AI cover..."):
            try:
                image_url = generate_cover_image(st.session_state.story_text[:150])
                st.image(image_url, caption="AI-Generated Cover", use_column_width=True)
            except Exception as e:
                st.error(f"Image failed: {e}")
    else:
        st.warning("Generate a story first.")

if st.button("Narrate Story"):
    if "story_text" in st.session_state:
        with st.spinner("Narrating..."):
            try:
                audio_path = narrate_story(st.session_state.story_text, voice)
                st.audio(audio_path)
            except Exception as e:
                st.error(f"Narration failed: {e}")
    else:
        st.warning("Generate a story first.")
