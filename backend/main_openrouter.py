from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
# StaticFiles removed
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn
import os
from pathlib import Path
import json
import requests
import PyPDF2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Manufacturing Equipment Maintenance Query Agent - OpenRouter Version")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files removed - using inline serving

# Simple document storage (in-memory for demo)
documents = {}

# OpenRouter API configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Pydantic models
class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    relevant_sections: list
    confidence: float

def extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from PDF file"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
            
            return text.strip()
    except Exception as e:
        raise Exception(f"Error extracting PDF text: {str(e)}")

def query_openrouter(question: str, context: str) -> str:
    """Query OpenRouter API for better AI responses"""
    if not OPENROUTER_API_KEY:
        # Fallback to simple keyword matching if no API key
        return "Please set OPENROUTER_API_KEY environment variable for AI-powered responses. Using basic search instead."
    
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Manufacturing Maintenance Agent"
        }
        
        # Use a free model like llama-3.2-3b-instruct
        data = {
            "model": "meta-llama/llama-3.2-3b-instruct:free",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant for manufacturing equipment maintenance. Answer questions based on the provided equipment manuals and maintenance documents. Be specific and practical in your responses."
                },
                {
                    "role": "user",
                    "content": f"Context from equipment manuals:\n\n{context}\n\nQuestion: {question}\n\nPlease provide a detailed answer based on the context above."
                }
            ],
            "max_tokens": 1000,
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
            return f"AI service error: {response.status_code}. Using basic search instead."
            
    except Exception as e:
        return f"AI service unavailable: {str(e)}. Using basic search instead."

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page"""
    html_file = Path("../frontend/index.html")
    if html_file.exists():
        return FileResponse(html_file)
    return HTMLResponse(content="<h1>Manufacturing Maintenance Agent</h1><p>Frontend not found</p>", status_code=200)

@app.get("/app.js")
async def get_app_js():
    """Serve the JavaScript file"""
    js_file = Path("../frontend/app.js")
    if js_file.exists():
        return FileResponse(js_file, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="JavaScript file not found")

@app.post("/upload")
async def upload_documents(files: list[UploadFile] = File(...)):
    """Upload and process documents"""
    try:
        processed_docs = []
        
        for file in files:
            # Validate file type
            if not file.filename.endswith(('.pdf', '.txt')):
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.filename}")
            
            # Save uploaded file
            upload_path = Path("../uploads") / file.filename
            upload_path.parent.mkdir(exist_ok=True)
            
            with open(upload_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            # Extract text content
            if file.filename.endswith('.pdf'):
                text_content = extract_pdf_text(upload_path)
            else:
                with open(upload_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
            
            # Store in simple format
            documents[file.filename] = {
                'content': text_content,
                'size': len(text_content),
                'type': 'txt' if file.filename.endswith('.txt') else 'pdf'
            }
            
            processed_docs.append({
                "filename": file.filename,
                "chunks": 1,
                "size": len(text_content)
            })
        
        return {
            "message": "Documents processed successfully",
            "processed_documents": processed_docs
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Query the document database with AI enhancement"""
    try:
        if not documents:
            return QueryResponse(
                answer="No documents have been uploaded yet. Please upload some equipment manuals or maintenance documents first.",
                relevant_sections=[],
                confidence=0.0
            )
        
        # Simple keyword-based search
        question_lower = request.question.lower()
        relevant_docs = []
        
        for filename, doc in documents.items():
            content_lower = doc['content'].lower()
            
            # Simple keyword matching
            keywords = question_lower.split()
            matches = sum(1 for keyword in keywords if keyword in content_lower)
            
            if matches > 0:
                similarity = matches / len(keywords)
                relevant_docs.append({
                    'content': doc['content'],
                    'source': filename,
                    'similarity': similarity
                })
        
        # Sort by similarity
        relevant_docs.sort(key=lambda x: x['similarity'], reverse=True)
        relevant_docs = relevant_docs[:3]  # Top 3 results
        
        if not relevant_docs:
            return QueryResponse(
                answer="No relevant information found in the uploaded documents. Try using different keywords or upload more comprehensive manuals.",
                relevant_sections=[],
                confidence=0.0
            )
        
        # Prepare context for AI
        context = "\n\n".join([doc['content'] for doc in relevant_docs[:2]])  # Use top 2 for context
        
        # Get AI-enhanced answer
        ai_answer = query_openrouter(request.question, context)
        
        # Format relevant sections for display
        display_sections = [
            {
                'content': doc['content'][:500] + "..." if len(doc['content']) > 500 else doc['content'],
                'source': doc['source']
            }
            for doc in relevant_docs
        ]
        
        return QueryResponse(
            answer=ai_answer,
            relevant_sections=display_sections,
            confidence=0.0
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents")
async def list_documents():
    """List all uploaded documents"""
    try:
        docs_list = []
        for filename, doc in documents.items():
            docs_list.append({
                'filename': filename,
                'chunk_count': 1,
                'total_size': doc['size']
            })
        return {"documents": docs_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{filename}")
async def delete_document(filename: str):
    """Delete a specific document"""
    try:
        if filename in documents:
            del documents[filename]
            return {"message": f"Document {filename} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Document {filename} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api-status")
async def api_status():
    """Check API status and configuration"""
    return {
        "openrouter_configured": bool(OPENROUTER_API_KEY),
        "documents_count": len(documents),
        "models_available": [
            "meta-llama/llama-3.2-3b-instruct:free",
            "microsoft/phi-3-mini-128k-instruct:free",
            "google/gemma-2-9b-it:free"
        ]
    }

@app.get("/api/health")
def read_root():
    return {"status": "running on Hugging Face!"}

if __name__ == "__main__":
    print("🚀 Starting Manufacturing Equipment Maintenance Query Agent")
    uvicorn.run(app, host="127.0.0.1", port=8000)
