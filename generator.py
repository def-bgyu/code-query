import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def build_prompt(question: str, chunks: list[dict]) -> str:
    """
    Combine the question and retrieved chunks into a single prompt.
    This is called prompt engineering — how you structure this
    directly affects answer quality.
    """

    # Format each chunk with its source file clearly labeled
    context_blocks = []
    for i, chunk in enumerate(chunks):
        path = chunk["metadata"]["path"]
        similarity = chunk["similarity"]
        content = chunk["content"]

        context_blocks.append(
            f"### Source {i+1}: {path} (relevance: {similarity})\n{content}"
        )

    context = "\n\n".join(context_blocks)

    prompt = f"""You are an expert code reviewer analyzing a GitHub repository.
You will be given relevant code snippets and documentation retrieved from the codebase.
Answer the user's question based ONLY on the provided context.
If the context doesn't contain enough information, say so honestly — do not guess.
Always cite which file your answer comes from.

## Retrieved Context:
{context}

## Question:
{question}

## Answer:
"""
    return prompt


def generate_answer(question: str, chunks: list[dict]) -> str:
    """
    Send question + context to LLM and get a grounded answer.
    """
    if not chunks:
        return "No relevant code found for your question."
 
    prompt = build_prompt(question, chunks)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are an expert code reviewer. Answer questions about codebases accurately and concisely, always citing source files."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1,  # low temperature = more factual, less creative
        max_tokens=1000
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    from ingester import clone_repo, walk_files
    from chunker import chunk_code
    from embedder import index_chunks, search

    # NOTE: Comment these out after first run — no need to re-index every time
    # repo_path = clone_repo("https://github.com/tiangolo/fastapi")
    # files = walk_files(repo_path)
    # all_chunks = []
    # for file in files:
    #     all_chunks.extend(chunk_code(file))
    # index_chunks(all_chunks, "tiangolo_fastapi")

    # Just search + generate
    question = "how is authentication handled?"
    print(f"Question: {question}\n")

    chunks = search(question, "tiangolo_fastapi", top_k=5)
    answer = generate_answer(question, chunks)

    print("Answer:")
    print(answer)