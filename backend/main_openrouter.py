from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn
import os
from pathlib import Path
import requests
import PyPDF2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(title="Manufacturing Equipment Maintenance Query Agent - OpenRouter Version")

# Allow CORS (Frontend <-> Backend communication)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Global In-Memory Storage
# ---------------------------
documents = {}

# ---------------------------
# OpenRouter Configuration
# ---------------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# ---------------------------
# Data Models
# ---------------------------
class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    relevant_sections: list
    confidence: float


# ---------------------------
# Utility Functions
# ---------------------------
def extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from PDF using PyPDF2"""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip()
    except Exception as e:
        raise Exception(f"Error extracting PDF text: {str(e)}")


def query_openrouter(question: str, context: str) -> str:
    """Query OpenRouter API for enhanced answers"""
    if not OPENROUTER_API_KEY:
        return "⚠️ No OpenRouter API key found. Please set OPENROUTER_API_KEY for AI-powered responses."

    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://huggingface.co/spaces/",
            "X-Title": "Manufacturing Maintenance Agent"
        }

        data = {
            "model": "meta-llama/llama-3.2-3b-instruct:free",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant for manufacturing equipment maintenance. "
                        "Answer questions based on the provided equipment manuals and documents. "
                        "Be specific, accurate, and practical."
                    )
                },
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuestion: {question}"
                }
            ],
            "max_tokens": 800,
            "temperature": 0.7
        }

        response = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            return f"AI service error ({response.status_code}): Using fallback logic."

    except Exception as e:
        return f"AI service unavailable: {str(e)}"


# ---------------------------
# Frontend Routes
# ---------------------------
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
UPLOAD_DIR = BASE_DIR.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True, parents=True)


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve frontend HTML"""
    html_file = FRONTEND_DIR / "index.html"
    if html_file.exists():
        return FileResponse(html_file)
    return HTMLResponse("<h1>Manufacturing Maintenance Agent</h1><p>Frontend not found</p>", status_code=200)


@app.get("/app.js")
async def serve_js():
    """Serve frontend JS"""
    js_file = FRONTEND_DIR / "app.js"
    if js_file.exists():
        return FileResponse(js_file, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="Frontend JS not found")


@app.get("/favicon.ico")
async def favicon():
    """Serve favicon to prevent 404 error"""
    icon_path = FRONTEND_DIR / "favicon.ico"
    if icon_path.exists():
        return FileResponse(icon_path)
    return HTMLResponse(content="", status_code=204)


# ---------------------------
# Upload Endpoint
# ---------------------------
@app.post("/upload")
async def upload_documents(files: list[UploadFile] = File(...)):
    """Upload and process documents"""
    try:
        processed = []

        for file in files:
            if not file.filename.endswith(('.pdf', '.txt')):
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.filename}")

            upload_path = UPLOAD_DIR / file.filename
            with open(upload_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            if file.filename.endswith(".pdf"):
                text_content = extract_pdf_text(upload_path)
            else:
                with open(upload_path, "r", encoding="utf-8") as f:
                    text_content = f.read()

            documents[file.filename] = {
                "content": text_content,
                "size": len(text_content),
                "type": "pdf" if file.filename.endswith(".pdf") else "txt"
            }

            processed.append({
                "filename": file.filename,
                "size": len(text_content),
                "chunks": 1
            })

        return {"message": "Documents processed successfully", "processed_documents": processed}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------
# Query Endpoint
# ---------------------------
@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Query uploaded documents"""
    try:
        if not documents:
            return QueryResponse(
                answer="No documents uploaded yet. Please upload manuals or maintenance files.",
                relevant_sections=[],
                confidence=0.0
            )

        question_lower = request.question.lower()
        relevant_docs = []

        for filename, doc in documents.items():
            content_lower = doc["content"].lower()
            keywords = question_lower.split()
            matches = sum(1 for k in keywords if k in content_lower)

            if matches > 0:
                similarity = matches / len(keywords)
                relevant_docs.append({
                    "content": doc["content"],
                    "source": filename,
                    "similarity": similarity
                })

        relevant_docs.sort(key=lambda x: x["similarity"], reverse=True)
        relevant_docs = relevant_docs[:3]

        if not relevant_docs:
            return QueryResponse(
                answer="No relevant content found. Try rephrasing your question.",
                relevant_sections=[],
                confidence=0.0
            )

        context = "\n\n".join([doc["content"] for doc in relevant_docs[:2]])
        ai_answer = query_openrouter(request.question, context)

        sections = [
            {
                "source": doc["source"],
                "content": doc["content"][:500] + "..." if len(doc["content"]) > 500 else doc["content"]
            }
            for doc in relevant_docs
        ]

        return QueryResponse(answer=ai_answer, relevant_sections=sections, confidence=0.9)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------
# Document Management
# ---------------------------
@app.get("/documents")
async def list_documents():
    """List uploaded documents"""
    try:
        return {"documents": [
            {"filename": f, "size": d["size"], "type": d["type"]}
            for f, d in documents.items()
        ]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{filename}")
async def delete_document(filename: str):
    """Delete document"""
    try:
        if filename in documents:
            del documents[filename]
            return {"message": f"Document '{filename}' deleted successfully"}
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------
# API Info & Health
# ---------------------------
@app.get("/api-status")
async def api_status():
    """Return system configuration info"""
    return {
        "openrouter_configured": bool(OPENROUTER_API_KEY),
        "documents_count": len(documents),
        "available_models": [
            "meta-llama/llama-3.2-3b-instruct:free",
            "microsoft/phi-3-mini-128k-instruct:free",
            "google/gemma-2-9b-it:free"
        ]
    }


@app.get("/api/health")
async def api_health():
    """Health check"""
    return {"status": "running on Hugging Face!", "documents_loaded": len(documents)}


# ---------------------------
# Main Entrypoint
# ---------------------------
if __name__ == "__main__":
    print("🚀 Starting Manufacturing Equipment Maintenance Query Agent on Hugging Face Space")
    uvicorn.run(app, host="0.0.0.0", port=7860)
