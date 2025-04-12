import streamlit as st
import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="NarrativaX Demo", layout="centered")
st.title("NarrativaX AI Story Demo")

story_prompt = st.text_area("Describe your story idea:", "A lonely hacker falls in love with an AI")

if st.button("Generate Story"):
    with st.spinner("Summoning GPT..."):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{
                    "role": "user",
                    "content": f"Write a short story based on: {story_prompt}"
                }]
            )
            st.success("Here’s your story:")
            st.write(response.choices[0].message.content)
        except Exception as e:
            st.error(f"Error: {str(e)}")
