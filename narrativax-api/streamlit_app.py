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
