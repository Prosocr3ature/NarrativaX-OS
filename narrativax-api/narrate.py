import os
from elevenlabs.client import ElevenLabs

client = ElevenLabs(api_key=os.getenv("sk_2cc5e16d7dba729974d8b2c58bd562eb032060aa75fc849f"))

def narrate_story(text, voice="Rachel", output_path="story.mp3"):
    audio = client.generate(
        text=text,
        voice=voice,
        model="eleven_monolingual_v1"
    )
    with open(output_path, "wb") as f:
        f.write(audio)
    return output_path
