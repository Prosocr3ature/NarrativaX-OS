# narrativax-api/streamlit_app.py

import os
import streamlit as st
import openai
import requests
from io import BytesIO
from PIL import Image
from elevenlabs import generate, save, set_api_key

# Set your API keys
openai.api_key = os.getenv("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")
set_api_key(os.getenv("ELEVEN_API_KEY"))

# Available ElevenLabs voices
VOICES = ["Rachel", "Bella", "Antoni", "Elli", "Josh"]

# Generate story with OpenAI
def generate_story(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.85,
        max_tokens=700
    )
    return response["choices"][0]["message"]["content"]

# Generate cover image with DALL·E
def generate_cover_image(prompt):
    response = openai.Image.create(
        prompt=prompt,
        n=1,
        size="512x512"
    )
    return response["data"][0]["url"]

# Narrate story using ElevenLabs
def narrate_story(story, voice):
    audio = generate(text=story, voice=voice, model="eleven_monolingual_v1")
    output_path = f"narration_{voice}.mp3"
    save(audio, output_path)
    return output_path

# Streamlit UI
st.set_page_config(page_title="NarrativaX AI Story Generator", layout="centered")
st.title("NarrativaX AI Story Generator")

story_prompt = st.text_area("Describe your story idea:", height=200)
voice_option = st.selectbox("Choose narrator voice", VOICES)

if st.button("Generate Story"):
    with st.spinner("Summoning GPT..."):
        try:
            story_text = generate_story(story_prompt)
            st.success("Here's your story:")
            st.markdown(story_text)
            st.session_state.story_text = story_text
        except Exception as e:
            st.error(f"Story generation failed: {e}")

if st.button("Generate Cover Image"):
    if "story_text" in st.session_state:
        with st.spinner("Creating cover with DALL·E..."):
            try:
                img_url = generate_cover_image(st.session_state.story_text[:150])
                st.image(img_url, caption="AI-Generated Cover", use_column_width=True)
            except Exception as e:
                st.error(f"Cover generation failed: {e}")
    else:
        st.warning("Generate a story first.")

if st.button("Narrate Story with ElevenLabs"):
    if "story_text" in st.session_state:
        with st.spinner("Narrating with ElevenLabs..."):
            try:
                audio_path = narrate_story(st.session_state.story_text, voice=voice_option)
                st.audio(audio_path)
            except Exception as e:
                st.error(f"Narration failed: {e}")
    else:
        st.warning("Generate a story first.")
