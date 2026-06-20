from huggingface_hub import HfApi
import os

api = HfApi()

repo_id = "BaranArda/firat-mevzuat-rag"
repo_type = "space"

files_to_upload = [
    ("backend/api.py", "backend/api.py"),
    ("frontend/app.js", "frontend/app.js"),
    ("frontend/style.css", "frontend/style.css"),
]

for local_path, path_in_repo in files_to_upload:
    print(f"Uploading {local_path} to {path_in_repo}...")
    api.upload_file(
        path_or_fileobj=local_path,
        path_in_repo=path_in_repo,
        repo_id=repo_id,
        repo_type=repo_type,
        commit_message=f"feat(ui): add like/dislike buttons ({path_in_repo})"
    )
    print("Done!")
