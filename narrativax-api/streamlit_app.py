from elevenlabs import generate, play, save, set_api_key
import streamlit as st

set_api_key(os.getenv("ELEVENLABS_API_KEY"))

def narrate(text, voice="Rachel"):
    audio = generate(text=text, voice=voice)
    save(audio, "story.mp3")
    return "story.mp3"

if st.button("Narrate This Story"):
    audio_file = narrate(story_text)  # `story_text` is the generated story
    st.audio(audio_file)
import streamlit as st
import openai
import os

# Set your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="NarrativaX", layout="centered")
st.title("NarrativaX AI Story Generator")

story_prompt = st.text_area("Describe your story idea:", "A lonely hacker falls in love with an AI")

if st.button("Generate Story"):
    with st.spinner("Summoning GPT..."):
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a creative, emotional novelist."},
                    {"role": "user", "content": f"Write a short story about: {story_prompt}"}
                ]
            )
            story = response.choices[0].message.content
            st.success("Here's your story:")
            st.write(story)
        except Exception as e:
            st.error(f"Error: {e}")
