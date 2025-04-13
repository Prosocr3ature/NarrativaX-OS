# narrativax-api/streamlit_app.py

import os
import streamlit as st
import openai
import requests
from io import BytesIO
from PIL import Image
from elevenlabs import Voice, VoiceSettings, set_api_key, generate, play

# Set your API keys from environment
openai.api_key = os.getenv("OPENAI_API_KEY")
set_api_key(os.getenv("ELEVEN_API_KEY"))

# ElevenLabs available voices
VOICES = ["Rachel", "Bella", "Antoni", "Elli", "Josh"]

# Generate story using Chat Completions
def generate_story(prompt):
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.85,
        max_tokens=700
    )
    return response.choices[0].message.content

# Generate a DALL·E image
def generate_cover_image(prompt):
    response = openai.Image.create(
        prompt=prompt,
        n=1,
        size="512x512"
    )
    return response["data"][0]["url"]

# Narrate story using ElevenLabs
def narrate_story(story_text, voice):
    audio = generate(
        text=story_text,
        voice=voice,
        model="eleven_monolingual_v1"
    )
    output_path = f"narration_{voice}.mp3"
    with open(output_path, "wb") as f:
        f.write(audio)
    return output_path

# Streamlit UI setup
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
                audio_path = narrate_story(st.session_state.story_text, voice_option)
                st.audio(audio_path)
            except Exception as e:
                st.error(f"Narration failed: {e}")
    else:
        st.warning("Generate a story first.")
