import re

def chunk_code(file: dict) -> list[dict]:
    """
    Split code files into meaningful chunks.
    For code: chunk by function/class boundaries.
    For markdown/text: chunk by section or fixed size with overlap.
    """
    ext = file["extension"]
    content = file["content"]
    path = file["path"]

    if ext in {".py", ".js", ".ts", ".go", ".java", ".cpp", ".c", ".cs", ".rb", ".rs"}:
        chunks = split_by_functions(content, path, file["filename"])
    else:
        # markdown, yaml, json, configs — fixed size with overlap
        chunks = split_by_fixed_size(content, path, file["filename"])

    return chunks


def split_by_functions(content: str, path: str, filename: str) -> list[dict]:
    """Split code by function/class definitions."""
    
    # Regex patterns that catch function/class starts across languages
    pattern = re.compile(
        r'^(?:def |class |func |function |public |private |protected |async def )',
        re.MULTILINE
    )

    matches = list(pattern.finditer(content))

    if not matches:
        # No function boundaries found — fall back to fixed size
        return split_by_fixed_size(content, path, filename)

    chunks = []
    for i, match in enumerate(matches):
        start = match.start()
        # End is where the next function starts (or end of file)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        chunk_text = content[start:end].strip()

        if not chunk_text:
            continue

        # Extract the function/class name for metadata
        first_line = chunk_text.split("\n")[0]

        chunks.append({
            "content": chunk_text,
            "metadata": {
                "path": path,
                "filename": filename,
                "type": "code",
                "first_line": first_line,
                "chunk_index": i
            }
        })

    return chunks


def split_by_fixed_size(content: str, path: str, filename: str, 
                         chunk_size: int = 1000, overlap: int = 200) -> list[dict]:
    """
    Fixed size chunking WITH overlap.
    Overlap means consecutive chunks share some text — critical for context continuity.
    """
    chunks = []
    start = 0
    i = 0

    while start < len(content):
        end = start + chunk_size
        chunk_text = content[start:end].strip()

        if chunk_text:
            chunks.append({
                "content": chunk_text,
                "metadata": {
                    "path": path,
                    "filename": filename,
                    "type": "text",
                    "chunk_index": i
                }
            })

        # Move forward by chunk_size minus overlap
        # So next chunk starts 200 chars back — capturing shared context
        start += chunk_size - overlap
        i += 1

    return chunks


if __name__ == "__main__":
    # Test it
    sample = {
        "path": "auth/user.py",
        "filename": "user.py",
        "extension": ".py",
        "content": """
def authenticate_user(token: str) -> bool:
    decoded = jwt.decode(token)
    return decoded is not None

def get_user_by_id(user_id: int) -> User:
    return db.query(User).filter(User.id == user_id).first()

class UserService:
    def __init__(self, db):
        self.db = db
    
    def create_user(self, email: str, password: str) -> User:
        hashed = bcrypt.hash(password)
        user = User(email=email, password=hashed)
        self.db.add(user)
        return user
"""
    }

    chunks = chunk_code(sample)
    for c in chunks:
        print("---")
        print(c["metadata"]["first_line"])
        print(c["content"][:100])