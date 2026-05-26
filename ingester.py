import os
import tempfile
import git

SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".go", ".java", ".cpp", ".c",
    ".h", ".cs", ".rb", ".rs", ".md", ".yaml", ".yml",
    ".json", ".toml"
}

IMPORTANT_FILENAMES = {
    "Dockerfile", "Makefile", "Procfile",
    "docker-compose.yml", "docker-compose.yaml",
    ".env.example", "requirements.txt",
    "go.mod", "go.sum", "Cargo.toml", "pom.xml"
}

IGNORED_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv",
    "venv", "dist", "build", ".next"
}

IGNORED_FILES = {
    ".gitignore", ".gitattributes", ".dockerignore",
    "package-lock.json", "yarn.lock", "poetry.lock",
    ".prettierrc", ".eslintrc", ".DS_Store"
}

MAX_FILE_SIZE = 500_000  # 500KB

def clone_repo(github_url: str) -> str:
    tmp_dir = tempfile.mkdtemp()
    print(f"Cloning {github_url} into {tmp_dir}...")
    git.Repo.clone_from(github_url, tmp_dir)
    return tmp_dir

def walk_files(repo_path: str) -> list[dict]:
    files = []

    for root, dirs, filenames in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

        for filename in filenames:
            # Skip known noise files
            if filename in IGNORED_FILES:
                continue

            filepath = os.path.join(root, filename)

            # Skip large files
            if os.path.getsize(filepath) > MAX_FILE_SIZE:
                print(f"Skipping large file: {filepath}")
                continue

            ext = os.path.splitext(filename)[1].lower()

            # Index if extension is supported OR filename is important
            if ext not in SUPPORTED_EXTENSIONS and filename not in IMPORTANT_FILENAMES:
                continue

            relative_path = os.path.relpath(filepath, repo_path)

            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                if not content.strip():
                    continue

                files.append({
                    "path": relative_path,
                    "content": content,
                    "extension": ext,
                    "filename": filename
                })

            except Exception as e:
                print(f"Skipping {filepath}: {e}")

    print(f"Found {len(files)} files worth indexing.")
    return files


if __name__ == "__main__":
    repo_path = clone_repo("https://github.com/tiangolo/fastapi")
    files = walk_files(repo_path)
    for f in files[:5]:
        print(f["path"], "—", len(f["content"]), "chars")