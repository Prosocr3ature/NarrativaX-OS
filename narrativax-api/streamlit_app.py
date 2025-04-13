import os
import streamlit as st
import openai
import requests
from io import BytesIO
from PIL import Image
from elevenlabs.client import ElevenLabs

# Set API keys
openai.api_key = os.getenv("OPENAI_API_KEY")
eleven_client = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))

# Voices
VOICES = ["Rachel", "Bella", "Antoni", "Elli", "Josh"]

# Generate story
def generate_story(prompt):
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.85,
        max_tokens=700
    )
    return response.choices[0].message.content.strip()

# Generate cover image
def generate_cover_image(prompt):
    response = openai.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1
    )
    return response.data[0].url

# Narrate with ElevenLabs
def narrate_story(story_text, voice):
    audio = eleven_client.text_to_speech.convert(
        voice=voice,
        model="eleven_monolingual_v1",
        text=story_text
    )
    path = f"narration_{voice}.mp3"
    with open(path, "wb") as f:
        f.write(audio)
    return path

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
                img_url = generate_cover_image(st.session_state.story_text[:300])
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
