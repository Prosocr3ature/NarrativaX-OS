import os
from elevenlabs.client import ElevenLabs

client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

def narrate_story(text, voice="Rachel", output_path="story.mp3"):
    audio = client.generate(
        text=text,
        voice=voice,
        model="eleven_monolingual_v1"
    )
    with open(output_path, "wb") as f:
        f.write(audio)
    return output_path
