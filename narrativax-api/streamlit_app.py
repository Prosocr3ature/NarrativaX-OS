# narrativax-api/streamlit_app.py

import os
import streamlit as st
import openai
from elevenlabs import generate, save, set_api_key
import requests
from PIL import Image
from io import BytesIO

# Load environment variables
openai.api_key = os.getenv("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")
set_api_key(os.getenv("sk_2cc5e16d7dba729974d8b2c58bd562eb032060aa75fc849f"))

# Page config
st.set_page_config(page_title="NarrativaX AI", layout="centered")
st.title("NarrativaX AI Story Generator")

# UI
story_prompt = st.text_area("Describe your story idea:")

story_text = ""

if st.button("Generate Story"):
    with st.spinner("Summoning GPT..."):
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": story_prompt}],
                temperature=0.9,
                max_tokens=700
            )
            story_text = response.choices[0].message.content
            st.success("Here's your story:")
            st.write(story_text)
        except Exception as e:
            st.error(f"Story generation failed: {e}")

# Generate Cover Image using DALL·E
if story_text and st.button("Generate Cover Image"):
    with st.spinner("Creating cover with DALL·E..."):
        try:
            image_response = openai.images.generate(
                model="dall-e-3",
                prompt=f"Book cover for: {story_text[:100]}",
                n=1,
                size="1024x1024"
            )
            image_url = image_response.data[0].url
            img_data = requests.get(image_url).content
            st.image(Image.open(BytesIO(img_data)), caption="AI-Generated Cover", use_column_width=True)
        except Exception as e:
            st.error(f"Cover generation failed: {e}")

# Narrate Story with ElevenLabs
if story_text and st.button("Narrate Story with ElevenLabs"):
    with st.spinner("Narrating..."):
        try:
            audio = generate(text=story_text, voice="Rachel", model="eleven_monolingual_v1")
            output_path = "/tmp/narration.mp3"
            save(audio, output_path)
            st.audio(output_path)
        except Exception as e:
            st.error(f"Narration failed: {e}")
