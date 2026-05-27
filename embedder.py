import os
import chromadb
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

# Load embedding model once globally
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Initialize ChromaDB locally
chroma_client = chromadb.PersistentClient(path="./chroma_db")


def get_or_create_collection(repo_name: str):
    """Each repo gets its own collection in ChromaDB."""
    safe_name = repo_name.replace("/", "_").replace(".", "_")
    collection = chroma_client.get_or_create_collection(
        name=safe_name,
        metadata={"hnsw:space": "cosine"}
    )
    return collection


def embed_text(text: str) -> list[float]:
    """Embed a single string — used for query embedding."""
    return embedding_model.encode(text).tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of strings — used for indexing chunks."""
    return embedding_model.encode(texts).tolist()


def index_chunks(chunks: list[dict], repo_name: str):
    """Embed all chunks and store in ChromaDB."""
    collection = get_or_create_collection(repo_name)

    print(f"Indexing {len(chunks)} chunks...")

    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]

        texts = [c["content"] for c in batch]
        metadatas = [c["metadata"] for c in batch]
        ids = [f"{repo_name}_{i+j}" for j, _ in enumerate(batch)]

        # Embed entire batch at once — much faster than one by one
        embeddings = embed_batch(texts)

        collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )

        print(f"  Indexed batch {i//batch_size + 1}/{-(-len(chunks)//batch_size)}")

    print(f"Done! {len(chunks)} chunks indexed.")


def search(query: str, repo_name: str, top_k: int = 5) -> list[dict]:
    """Find the most relevant chunks for a query."""
    collection = get_or_create_collection(repo_name)

    # Embed the question using the SAME model used for indexing
    query_embedding = embed_text(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        chunks.append({
            "content": doc,
            "metadata": meta,
            "similarity": round(1 - dist, 3)
        })

    return chunks


if __name__ == "__main__":
    from ingester import clone_repo, walk_files
    from chunker import chunk_code

    # Full pipeline test
    repo_path = clone_repo("https://github.com/tiangolo/fastapi")
    files = walk_files(repo_path)

    all_chunks = []
    for file in files:
        all_chunks.extend(chunk_code(file))

    print(f"Total chunks to index: {len(all_chunks)}")
    index_chunks(all_chunks, "tiangolo_fastapi")

    # Search test
    results = search("how is authentication handled?", "tiangolo_fastapi")
    for r in results:
        print(f"\n📄 {r['metadata']['path']} (similarity: {r['similarity']})")
        print(r['content'][:200])