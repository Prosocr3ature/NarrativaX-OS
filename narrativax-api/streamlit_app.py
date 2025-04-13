import os
import streamlit as st
import requests
from elevenlabs.client import ElevenLabs

# API Keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
eleven_client = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))

# ElevenLabs Voice IDs
VOICES = {
    "Rachel": "EXAVITQu4vr4xnSDxMaL",
    "Bella": "29vD33N1CtxCmqQRPOHJ",
    "Antoni": "ErXwobaYiN019PkySvjV",
    "Elli": "MF3mGyEYCl7XYWbV9V6O",
    "Josh": "TxGEqnHWrfWFTfGW9XjX"
}

# Generate story using OpenRouter

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

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# Generate single cover image

def generate_cover_image(prompt):
    dalle_url = "https://api.openai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    data = {
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024"
    }

    response = requests.post(dalle_url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()["data"][0]["url"]

# Narrate with ElevenLabs

def narrate_story(text, voice_id):
    audio = eleven_client.text_to_speech.convert(
        voice_id=voice_id,
        model_id="eleven_monolingual_v1",
        text=text,
        stream=True
    )
    path = f"narration_{voice_id}.mp3"
    with open(path, "wb") as f:
        for chunk in audio:
            f.write(chunk)
    return path

# Streamlit UI
st.set_page_config(page_title="NarrativaX AI Story Generator")
st.title("NarrativaX AI Story Generator")

prompt = st.text_area("Describe your story idea:", height=200)
voice = st.selectbox("Choose narrator voice", list(VOICES.keys()))
voice_id = VOICES[voice]

if st.button("Generate Story"):
    with st.spinner("Summoning uncensored story..."):
        try:
            story = generate_story(prompt)
            st.session_state.story = story
            st.success("Here's your story:")
            st.markdown(story)
        except Exception as e:
            st.error(f"Failed to generate story: {e}")

if st.button("Generate Cover Image"):
    if "story" in st.session_state:
        with st.spinner("Creating cover with DALL·E..."):
            try:
                img_url = generate_cover_image(st.session_state.story[:300])
                st.image(img_url, caption="AI-Generated Cover", use_column_width=True)
            except Exception as e:
                st.error(f"Cover generation failed: {e}")
    else:
        st.warning("Generate a story first.")

if st.button("Narrate Story"):
    if "story" in st.session_state:
        with st.spinner("Narrating story..."):
            try:
                audio_file = narrate_story(st.session_state.story, voice_id)
                st.audio(audio_file)
            except Exception as e:
                st.error(f"Narration failed: {e}")
    else:
        st.warning("Generate a story first.")
