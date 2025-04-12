import openai
from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/classify-story")
async def classify(request: Request):
    data = await request.json()
    story = data.get("text", "")

    prompt = f"""
    Analyze this story and return:
    - Genre
    - NSFW: yes/no
    - Ideal publishing platform
    - Vibe ("for fans of...")
    
    Story:
    {story[:1500]}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    return {"result": response.choices[0].message["content"]}
