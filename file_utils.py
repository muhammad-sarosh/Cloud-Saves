import hashlib
import json
from pathlib import Path
import shutil
from datetime import datetime, timezone

def hash_save_folder(config, path:Path):
    # Intitialise md5 hash object
    hasher = hashlib.md5()
    # File system ordering can be random, so we use
    # sorted so its the same everytime, imp for hashing
    for file in sorted(path.rglob("*")):
        if file.is_file() and file.suffix.lower() not in config.skip_extensions:
            # Including file name in hash, ensures hash is affected if files
            # are moved or renamed
            hasher.update(file.name.encode())
            with open(file, 'rb') as f:
                # := both assigns and checks if the file is finished
                # Reading file in chunks to avoid crashes on big files
                while chunk := f.read(8192):
                    hasher.update(chunk)
    # hexdigest() turns the hash into a string                
    return hasher.hexdigest()

def move_files(source_path, backup_path):
    # Creating trash, game and backup folders (if they don't already exist)
    backup_path.mkdir(parents=True, exist_ok=True)

    # Moving files to trash folder
    for file in source_path.rglob("*"):
        if file.is_file():
            # Preserving the directory structure by geting relative path
            relative_path = file.relative_to(source_path)
            destination_path = backup_path / relative_path

            # Making sure destination folders exist
            destination_path.parent.mkdir(parents=True, exist_ok=True)

            # Moving the file
            shutil.move(str(file), str(destination_path))

    # Remove all empty folders (deepest first)
    for folder in sorted(source_path.rglob("*"), reverse=True):
        # Making sure folder is empty
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()

def get_last_modified(config, folder: Path):
    latest_time = 0
    for file in folder.rglob("*"):
        if file.is_file() and file.suffix.lower() not in config.skip_extensions:
            mtime = file.stat().st_mtime
            latest_time = max(latest_time, mtime)
    return datetime.fromtimestamp(latest_time, timezone.utc).isoformat() if latest_time else None

def is_json_valid(file):
    try:
        with open(file, 'r') as f:
            loaded_file = json.load(f)
        # File is either fine or just '{}' in which case it returns False
        return bool(loaded_file)
    # File doesnt exist or is empty/invalid
    except (FileNotFoundError, json.JSONDecodeError):
        return False