import os

def ensure_directory(directory_path: str):
    """Ensure that the specified directory exists."""
    os.makedirs(directory_path, exist_ok=True)
