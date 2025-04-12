from fastapi import FastAPI
from classify import router as classify_router

app = FastAPI()

@app.get("/")
def health_check():
    return {"message": "NarrativaX API is running"}

app.include_router(classify_router)
