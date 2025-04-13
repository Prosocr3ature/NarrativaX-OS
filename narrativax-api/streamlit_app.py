# narrativax-api/streamlit_app.py

import os
import streamlit as st
import openai
import requests
from io import BytesIO
from PIL import Image
from elevenlabs.client import ElevenLabs

# Load environment variables
openai.api_key = os.getenv("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")
eleven_api_key = os.getenv("sk_2cc5e16d7dba729974d8b2c58bd562eb032060aa75fc849f")
client = ElevenLabs(api_key=eleven_api_key)

# UI Setup
st.set_page_config(page_title="NarrativaX AI Story Generator", layout="centered")
st.title("NarrativaX AI Story Generator")

story_prompt = st.text_area("Describe your story idea:")

# Generate story with GPT
if st.button("Generate Story"):
    with st.spinner("Summoning GPT..."):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{
                    "role": "user",
                    "content": f"Write a vivid, emotional short story based on: {story_prompt}"
                }],
                temperature=0.9,
                max_tokens=900
            )
            story_text = response.choices[0].message.content.strip()
            st.subheader("Here's your story:")
            st.markdown(story_text)
            st.session_state["story_text"] = story_text
        except Exception as e:
            st.error(f"Story generation failed: {e}")

# Generate cover with DALL·E
if "story_text" in st.session_state:
    if st.button("Generate Cover Image"):
        with st.spinner("Creating cover with DALL·E..."):
            try:
                cover_prompt = st.session_state["story_text"][:150]
                response = openai.Image.create(
                    prompt=cover_prompt,
                    n=1,
                    size="512x512"
                )
                image_url = response["data"][0]["url"]
                st.image(image_url, caption="AI-Generated Cover", use_column_width=True)
            except Exception as e:
                st.error(f"Cover generation failed: {e}")

# Narrate story with ElevenLabs
    voice = st.selectbox("Select voice for narration", ["Rachel", "Antoni", "Bella", "Elli", "Josh"])
    if st.button("Narrate Story with ElevenLabs"):
        with st.spinner("Narrating with ElevenLabs..."):
            try:
                audio = client.text_to_speech.convert(
                    voice=voice,
                    model="eleven_multilingual_v2",
                    text=st.session_state["story_text"]
                )
                st.audio(audio, format="audio/mp3")
            except Exception as e:
                st.error(f"Narration failed: {e}")
