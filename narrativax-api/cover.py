import os
import openai

openai.api_key = os.getenv("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")

def generate_cover_image(prompt, size="1024x1024"):
    response = openai.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,
        n=1
    )
    return response.data[0].url
