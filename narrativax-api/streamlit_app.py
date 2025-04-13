import os
import requests
import streamlit as st
from elevenlabs.client import ElevenLabs

# API Keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
eleven_client = ElevenLabs(api_key=ELEVEN_API_KEY)

# Voice options
VOICES = {
    "Rachel": "EXAVITQu4vr4xnSDxMaL",
    "Bella": "29vD33N1CtxCmqQRPOHJ",
    "Antoni": "ErXwobaYiN019PkySvjV",
    "Elli": "MF3mGyEYCl7XYWbV9V6O",
    "Josh": "TxGEqnHWrfWFTfGW9XjX"
}

# Format prompt with tone
TONE_MODIFIERS = {
    "Romantic": "Write a tender, emotional, sensual romantic story. Do not include explicit sexual language.",
    "NSFW": "Write a detailed erotic story with mature scenes and emotional depth. Allow sexually explicit content.",
    "Hardcore": "Write a raw, intense pornographic story. Be extremely graphic, use vulgar sexual language freely. No filters."
}

def format_prompt(user_input, tone):
    return f"{TONE_MODIFIERS[tone]}\n\n{user_input}"

# Generate story via OpenRouter

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
        "temperature": 1.0,
        "max_tokens": 1200
    }
    res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]

# Generate DALL·E image

def generate_cover(prompt):
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    data = {"prompt": prompt, "n": 1, "size": "1024x1024"}
    res = requests.post("https://api.openai.com/v1/images/generations", headers=headers, json=data)
    res.raise_for_status()
    return res.json()["data"][0]["url"]

# ElevenLabs Narration

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

# UI
st.set_page_config(page_title="NarrativaX NSFW", layout="centered")
st.title("NarrativaX: Unfiltered Erotic Story Generator")

prompt = st.text_area("Your NSFW story idea:", height=200)
tone_level = st.selectbox("Select story explicitness", ["Romantic", "NSFW", "Hardcore"])
voice_label = st.selectbox("Narrator voice", list(VOICES.keys()))
voice_id = VOICES[voice_label]

if st.button("Generate Story"):
    with st.spinner("Writing raw content..."):
        try:
            full_prompt = format_prompt(prompt, tone_level)
            story = generate_story(full_prompt)
            st.session_state.story = story
            st.success("Here's your story:")
            st.markdown(story)
        except Exception as e:
            st.error(f"Story generation failed: {e}")

if st.button("Generate Cover Image"):
    if "story" in st.session_state:
        with st.spinner("Creating steamy cover..."):
            try:
                img_url = generate_cover(st.session_state.story[:300])
                st.image(img_url, caption="NSFW DALL·E Cover", use_column_width=True)
            except Exception as e:
                st.error(f"Cover generation failed: {e}")
    else:
        st.warning("Generate a story first.")

if st.button("Narrate Story"):
    if "story" in st.session_state:
        with st.spinner("Moaning into mp3..."):
            try:
                audio_path = narrate_story(st.session_state.story, voice_id)
                st.audio(audio_path)
            except Exception as e:
                st.error(f"Narration failed: {e}")
    else:
        st.warning("Generate a story first.")

if st.button("Continue Story"):
    if "story" in st.session_state:
        with st.spinner("Extending your tale..."):
            try:
                extended_prompt = st.session_state.story + "\n\nContinue the story in the same tone and style."
                continuation = generate_story(extended_prompt)
                st.session_state.story += "\n\n" + continuation
                st.success("Extended:")
                st.markdown(continuation)
            except Exception as e:
                st.error(f"Story continuation failed: {e}")
    else:
        st.warning("Generate a story first.")
