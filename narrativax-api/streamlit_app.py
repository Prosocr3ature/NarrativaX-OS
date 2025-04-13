# streamlit_app.py

import os
import streamlit as st
import requests
from elevenlabs.client import ElevenLabs

# Load API keys from environment
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
eleven_client = ElevenLabs(api_key=ELEVEN_API_KEY)

# Voices available
VOICES = {
    "Rachel": "EXAVITQu4vr4xnSDxMaL",
    "Bella": "29vD33N1CtxCmqQRPOHJ",
    "Antoni": "ErXwobaYiN019PkySvjV",
    "Elli": "MF3mGyEYCl7XYWbV9V6O",
    "Josh": "TxGEqnHWrfWFTfGW9XjX"
}

# Generate story with Mistral (OpenRouter)
def generate_story(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://yourapp.vercel.app",
        "X-Title": "NarrativaX",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9,
        "max_tokens": 800
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# Generate DALL·E image from OpenAI
def generate_cover(prompt):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024"
    }
    response = requests.post("https://api.openai.com/v1/images/generations", headers=headers, json=data)
    response.raise_for_status()
    return response.json()["data"][0]["url"]

# Narrate story with ElevenLabs
def narrate_story(text, voice_id):
    stream = eleven_client.text_to_speech.convert(
        voice_id=voice_id,
        model_id="eleven_monolingual_v1",
        text=text,
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

prompt = st.text_area("Describe your story idea:", height=200)
voice_name = st.selectbox("Choose narrator voice", list(VOICES.keys()))
voice_id = VOICES[voice_name]

if st.button("Generate Story"):
    with st.spinner("Writing your story..."):
        try:
            story = generate_story(prompt)
            st.session_state.story = story
            st.success("Here's your story:")
            st.markdown(story)
        except Exception as e:
            st.error(f"Story generation failed: {e}")

if st.button("Generate Cover Image"):
    if "story" in st.session_state:
        with st.spinner("Generating cover with DALL·E..."):
            try:
                image_url = generate_cover(st.session_state.story[:300])
                st.image(image_url, caption="AI-Generated Cover", use_column_width=True)
            except Exception as e:
                st.error(f"Cover generation failed: {e}")
    else:
        st.warning("Generate a story first.")

if st.button("Narrate Story"):
    if "story" in st.session_state:
        with st.spinner("Narrating..."):
            try:
                audio_path = narrate_story(st.session_state.story, voice_id)
                st.audio(audio_path)
            except Exception as e:
                st.error(f"Narration failed: {e}")
    else:
        st.warning("Generate a story first.")
