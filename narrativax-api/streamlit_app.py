import os
import streamlit as st
import openai
import requests
from io import BytesIO
from PIL import Image
from elevenlabs import generate, save, set_api_key

# Set API keys
openai.api_key = os.getenv("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")
set_api_key(os.getenv("sk_2cc5e16d7dba729974d8b2c58bd562eb032060aa75fc849f"))

st.set_page_config(page_title="NarrativaX AI Story Generator")
st.title("NarrativaX AI Story Generator")

# Text input
story_prompt = st.text_area("Describe your story idea:", height=150)
story_text = ""

# Generate story
if st.button("Generate Story"):
    with st.spinner("Summoning GPT..."):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a story writer."},
                    {"role": "user", "content": story_prompt}
                ]
            )
            story_text = response.choices[0].message["content"]
            st.success("Here's your story:")
            st.write(story_text)
        except Exception as e:
            st.error(f"Story generation failed: {e}")

# Generate cover
if story_text and st.button("Generate Cover Image"):
    with st.spinner("Creating cover with DALL·E..."):
        try:
            dalle_response = openai.Image.create(
                prompt=story_text[:150],
                n=1,
                size="512x512"
            )
            image_url = dalle_response['data'][0]['url']
            image = Image.open(requests.get(image_url, stream=True).raw)
            st.image(image, caption="AI-Generated Cover", use_column_width=True)
        except Exception as e:
            st.error(f"Cover generation failed: {e}")

# Narrate story
voices = ["Rachel", "Bella", "Antoni", "Elli", "Arnold"]
voice_choice = st.selectbox("Choose Narration Voice", voices)

if story_text and st.button("Narrate Story with ElevenLabs"):
    with st.spinner("Narrating..."):
        try:
            audio = generate(text=story_text, voice=voice_choice, model="eleven_monolingual_v1")
            audio_path = "narration.mp3"
            save(audio, audio_path)
            st.audio(audio_path)
        except Exception as e:
            st.error(f"Narration failed: {e}")
