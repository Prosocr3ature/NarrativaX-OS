import streamlit as st
import openai
import os

from narrate import narrate_story
from cover import generate_cover_image

openai.api_key = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="NarrativaX AI Story Generator")
st.title("NarrativaX AI Story Generator")

story_prompt = st.text_area("Describe your story idea:")

story_text = ""

if st.button("Generate Story"):
    with st.spinner("Summoning GPT..."):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You're a story-writing assistant."},
                    {"role": "user", "content": story_prompt},
                ],
                temperature=0.9,
                max_tokens=800,
            )
            story_text = response['choices'][0]['message']['content']
            st.subheader("Here's your story:")
            st.write(story_text)
        except Exception as e:
            st.error(f"Story generation failed: {e}")

if story_text:
    if st.button("Generate Cover Image"):
        with st.spinner("Creating cover with DALL·E..."):
            try:
                image_url = generate_cover_image(story_text[:150])
                st.image(image_url, caption="AI-Generated Cover", use_column_width=True)
            except Exception as e:
                st.error(f"Cover generation failed: {e}")

    if st.button("Narrate Story with ElevenLabs"):
        with st.spinner("Narrating with ElevenLabs..."):
            try:
                audio_path = narrate_story(story_text, voice="Rachel")
                st.audio(audio_path)
            except Exception as e:
                st.error(f"Narration failed: {e}")
