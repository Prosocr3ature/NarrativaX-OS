import os
import streamlit as st
import openai
import requests
from io import BytesIO
from PIL import Image
from elevenlabs.client import ElevenLabs
import random

# API Keys
openai.api_key = os.getenv("OPENAI_API_KEY")
eleven_client = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))

# ElevenLabs Voice IDs
VOICES = {
    "Rachel": "EXAVITQu4vr4xnSDxMaL",
    "Bella": "29vD33N1CtxCmqQRPOHJ",
    "Antoni": "ErXwobaYiN019PkySvjV",
    "Elli": "MF3mGyEYCl7XYWbV9V6O",
    "Josh": "TxGEqnHWrfWFTfGW9XjX"
}

# Style Presets
STYLE_PRESETS = {
    "Realistic": "in realistic style",
    "Fantasy Art": "as detailed fantasy art, intricate lighting",
    "Anime": "as Japanese anime character art",
    "Cinematic": "cinematic illustration, depth of field",
    "Cyberpunk": "neon cyberpunk futuristic atmosphere"
}

# Generate story

def generate_story(prompt):
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.85,
        max_tokens=700
    )
    return response.choices[0].message.content.strip()

# Generate single cover image

def generate_cover_image(prompt, style_desc):
    styled_prompt = f"{prompt} — {style_desc}"
    response = openai.images.generate(
        model="dall-e-3",
        prompt=styled_prompt,
        size="1024x1024",
        quality="standard",
        n=1
    )
    return response.data[0].url, styled_prompt

# Narrate story

def narrate_story(story_text, voice_id):
    stream = eleven_client.text_to_speech.convert(
        voice_id=voice_id,
        model_id="eleven_monolingual_v1",
        text=story_text,
        stream=True
    )
    path = f"narration_{voice_id}.mp3"
    with open(path, "wb") as f:
        for chunk in stream:
            f.write(chunk)
    return path

# Streamlit UI
st.set_page_config(page_title="NarrativaX AI Story Generator", layout="centered")
st.title("NarrativaX AI Story Generator")

story_prompt = st.text_area("Describe your story idea:", height=200)
voice_name = st.selectbox("Choose narrator voice", list(VOICES.keys()))
voice_id = VOICES[voice_name]

# Style picker
preset = st.selectbox("Choose cover image style preset", list(STYLE_PRESETS.keys()) + ["Custom"])
if preset == "Custom":
    style_description = st.text_input("Describe your custom style")
else:
    style_description = STYLE_PRESETS[preset]

if st.button("Surprise Me with Random Style"):
    preset = random.choice(list(STYLE_PRESETS.keys()))
    style_description = STYLE_PRESETS[preset]
    st.success(f"Random style chosen: {preset}")

# Generate story
if st.button("Generate Story"):
    with st.spinner("Summoning GPT..."):
        try:
            story_text = generate_story(story_prompt)
            st.success("Here's your story:")
            st.markdown(story_text)
            st.session_state.story_text = story_text
        except Exception as e:
            st.error(f"Story generation failed: {e}")

# Generate 1 cover image
if st.button("Generate Cover Image"):
    if "story_text" in st.session_state:
        with st.spinner("Creating cover with DALL·E..."):
            try:
                url, final_prompt = generate_cover_image(st.session_state.story_text[:300], style_description)
                st.session_state.generated_cover = url
                st.session_state.cover_prompt = final_prompt
            except Exception as e:
                st.error(f"Cover generation failed: {e}")
    else:
        st.warning("Generate a story first.")

# Display selected cover image
if "generated_cover" in st.session_state:
    st.image(st.session_state.generated_cover, caption=f"Prompt: {st.session_state.cover_prompt}", use_column_width=True)
    if st.button("Download Cover Image"):
        img_data = requests.get(st.session_state.generated_cover).content
        st.download_button("Download Image", img_data, file_name="cover_image.png", mime="image/png")

# Narration
if st.button("Narrate Story with ElevenLabs"):
    if "story_text" in st.session_state:
        with st.spinner("Narrating with ElevenLabs..."):
            try:
                audio_path = narrate_story(st.session_state.story_text, voice_id)
                st.audio(audio_path)
            except Exception as e:
                st.error(f"Narration failed: {e}")
    else:
        st.warning("Generate a story first.")
