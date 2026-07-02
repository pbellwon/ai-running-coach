from fastapi import FastAPI

app = FastAPI(
    title="PaceMind API",
    description="AI Running Coach API",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "message": "Welcome to PaceMind API 🚀"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }