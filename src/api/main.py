from fastapi import FastAPI

app = FastAPI(
    title="GitHub Multimodal RAG API",
    description="Intelligent Q&A system for GitHub repositories combining text, code, and images.",
    version="0.1.0"
)

@app.get("/")
def read_root():
    return {"message": "Welcome to GitHub Multimodal RAG API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
