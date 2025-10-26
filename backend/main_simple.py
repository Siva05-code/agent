from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn
import os
from pathlib import Path
import json

app = FastAPI(title="Manufacturing Equipment Maintenance Query Agent - Simple Version")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="../static"), name="static")

# Simple document storage (in-memory for demo)
documents = {}

# Pydantic models
class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    relevant_sections: list
    confidence: float

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
    """Upload and process documents (simplified version)"""
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
            
            # Simple text extraction for TXT files
            if file.filename.endswith('.txt'):
                with open(upload_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
            else:
                # For PDF files, just store the filename for now
                text_content = f"PDF file: {file.filename}"
            
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
            "message": "Documents processed successfully (Simple Mode)",
            "processed_documents": processed_docs
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Query the document database (simplified version)"""
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
                    'content': doc['content'][:500] + "..." if len(doc['content']) > 500 else doc['content'],
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
        
        # Generate better answer based on content
        if relevant_docs:
            # Try to extract a more specific answer from the content
            best_match = relevant_docs[0]
            content = best_match['content'].lower()
            question_lower = request.question.lower()
            
            # Look for specific information in the content
            if any(word in content for word in ['troubleshoot', 'problem', 'issue', 'error']):
                answer = "Based on the troubleshooting information in your documents, here are the steps to resolve the issue:"
            elif any(word in content for word in ['maintenance', 'schedule', 'routine']):
                answer = "Here's the maintenance information from your equipment manuals:"
            elif any(word in content for word in ['safety', 'procedure', 'warning']):
                answer = "Here are the safety procedures and guidelines from your documents:"
            elif any(word in content for word in ['replace', 'part', 'component']):
                answer = "Here's the information about parts and replacement procedures:"
            else:
                answer = "Here's the relevant information from your equipment manuals:"
            
            # Add the most relevant content to the answer (show full content)
            answer += "\n\n" + best_match['content']
        else:
            answer = "I couldn't find specific information about your question in the uploaded documents. Please try rephrasing your question or upload more comprehensive manuals."
        
        return QueryResponse(
            answer=answer,
            relevant_sections=relevant_docs,
            confidence=0.0  # Remove confidence display
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

if __name__ == "__main__":
    print("Starting Manufacturing Maintenance Agent (Simple Mode)")
    print("Note: This is a simplified version without AI models")
    print("For full functionality, install the AI dependencies and use main.py")
    uvicorn.run(app, host="127.0.0.1", port=8000)
