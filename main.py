import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from ingester import clone_repo, walk_files
from chunker import chunk_code
from embedder import index_chunks, search
from generator import generate_answer

load_dotenv()

app = FastAPI(
    title="RepoLens",
    description="Ask questions about any public GitHub repository in natural language.",
    version="1.0.0"
)

# ── Request/Response Models ──────────────────────────────────────

class IndexRequest(BaseModel):
    github_url: str

class IndexResponse(BaseModel):
    status: str
    repo_name: str
    files_found: int
    chunks_indexed: int

class QueryRequest(BaseModel):
    repo_name: str
    question: str

class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[dict]

# ── Routes ───────────────────────────────────────────────────────

@app.post("/index", response_model=IndexResponse)
def index_repo(request: IndexRequest):
    """
    Clone a public GitHub repo and index it into ChromaDB.
    Only needs to be called once per repo.
    """
    try:
        # Extract a clean repo name from the URL
        # "https://github.com/tiangolo/fastapi" → "tiangolo_fastapi"
        repo_name = request.github_url.rstrip("/").split("github.com/")[-1].replace("/", "_")

        print(f"Cloning {request.github_url}...")
        repo_path = clone_repo(request.github_url)

        print(f"Walking files...")
        files = walk_files(repo_path)

        print(f"Chunking {len(files)} files...")
        all_chunks = []
        for file in files:
            all_chunks.extend(chunk_code(file))

        print(f"Indexing {len(all_chunks)} chunks...")
        index_chunks(all_chunks, repo_name)

        return IndexResponse(
            status="indexed",
            repo_name=repo_name,
            files_found=len(files),
            chunks_indexed=len(all_chunks)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse)
def query_repo(request: QueryRequest):
    """
    Ask a natural language question about an indexed repo.
    """
    try:
        # Retrieve relevant chunks
        chunks = search(request.question, request.repo_name, top_k=5)

        if not chunks:
            raise HTTPException(
                status_code=404,
                detail=f"No indexed data found for repo '{request.repo_name}'. Index it first via /index."
            )

        # Generate answer
        answer = generate_answer(request.question, chunks)

        # Format sources cleanly for the response
        sources = [
            {
                "file": c["metadata"]["path"],
                "similarity": c["similarity"]
            }
            for c in chunks
        ]

        return QueryResponse(
            question=request.question,
            answer=answer,
            sources=sources
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok", "service": "RepoLens"}