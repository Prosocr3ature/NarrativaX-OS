import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_cover_image(prompt, size="1024x1024"):
    response = openai.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,
        n=1
    )
    return response.data[0].url
