import streamlit as st
import openai
from narrate import narrate_story
from cover import generate_cover_image
import os

# Set your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="NarrativaX AI Story Generator")
st.title("NarrativaX AI Story Generator")

story_prompt = st.text_area("Describe your story idea:")

story_text = ""  # default empty

if st.button("Generate Story"):
    with st.spinner("Summoning GPT..."):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You're a world-class fiction writer."},
                    {"role": "user", "content": story_prompt}
                ]
            )
            story_text = response.choices[0].message.content.strip()
            st.success("Here's your story:")
            st.write(story_text)

            # Download story button
            st.download_button("Download Story (.txt)", story_text, file_name="story.txt")

            # Cover image generation
            if st.button("Generate Cover Image"):
                with st.spinner("Creating cover with DALL·E..."):
                    try:
                        image_url = generate_cover_image(story_text[:150])
                        st.image(image_url, caption="AI-Generated Cover", use_column_width=True)
                    except Exception as e:
                        st.error(f"Cover generation failed: {e}")

            # Narration
            voice = st.selectbox(
                "Choose a voice for narration:",
                ["Rachel", "Domi", "Bella", "Antoni", "Elli"]
            )
            if st.button("Narrate Story with ElevenLabs"):
                with st.spinner(f"Narrating with ElevenLabs voice: {voice}..."):
                    try:
                        audio_path = narrate_story(story_text, voice=voice)
                        st.audio(audio_path)
                    except Exception as e:
                        st.error(f"Narration failed: {e}")

        except Exception as e:
            st.error(f"Story generation failed: {e}")
