import os
from elevenlabs import generate, save, set_api_key

set_api_key(os.getenv("ELEVENLABS_API_KEY"))

def narrate_story(text, voice="Rachel", output_path="story.mp3"):
    audio = generate(text=text, voice=voice)
    save(audio, output_path)
    return output_path
