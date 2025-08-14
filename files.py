import hashlib
import json
from pathlib import Path
import shutil
from datetime import datetime, timezone
import os
from rich import print
from common import log
from ui import int_range_input
from game_entry import take_entry_input

def hash_save_folder(path:Path):
    from settings import SKIP_EXTENSIONS
    from common import log

    # Intitialise md5 hash object
    hasher = hashlib.md5()
    file_count = 0
    # File system ordering can be random, so we use
    # sorted so its the same everytime, imp for hashing
    for file in sorted(path.rglob("*")):
        if file.is_file() and file.suffix.lower() not in SKIP_EXTENSIONS:
            # Including file name in hash, ensures hash is affected if files
            # are moved or renamed
            hasher.update(file.name.encode())
            with open(file, 'rb') as f:
                # := both assigns and checks if the file is finished
                # Reading file in chunks to avoid crashes on big files
                while chunk := f.read(8192):
                    hasher.update(chunk)
            file_count += 1
    # hexdigest() turns the hash into a string   
    hash_result = hasher.hexdigest()
    log(f'Calculated hash for {file_count} files in {path}: {hash_result[:8]}...')             
    return hash_result

def move_files(source_path, backup_path):
    from common import log
    
    log(f'Moving files from {source_path} to backup at {backup_path}')
    
    # Creating trash, game and backup folders (if they don't already exist)
    backup_path.mkdir(parents=True, exist_ok=True)

    file_count = 0
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
            file_count += 1

    # Remove all empty folders (deepest first)
    for folder in sorted(source_path.rglob("*"), reverse=True):
        # Making sure folder is empty
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
    
    log(f'Moved {file_count} files to backup')

def get_last_modified(folder: Path):
    from settings import SKIP_EXTENSIONS
    from common import log

    latest_time = 0
    file_count = 0
    for file in folder.rglob("*"):
        if file.is_file() and file.suffix.lower() not in SKIP_EXTENSIONS:
            mtime = file.stat().st_mtime
            latest_time = max(latest_time, mtime)
            file_count += 1
    
    result = datetime.fromtimestamp(latest_time, timezone.utc).isoformat() if latest_time else None
    log(f'Found latest modification time from {file_count} files in {folder}: {result}')
    return result

def is_json_valid(file):
    try:
        with open(file, 'r') as f:
            loaded_file = json.load(f)
        # File is either fine or just '{}' in which case it returns False
        return bool(loaded_file)
    # File doesnt exist or is empty/invalid
    except (FileNotFoundError, json.JSONDecodeError):
        return False

def get_games_file():
    from settings import GAMES_FILE

    # Loading file if exists else create new
    if os.path.exists(GAMES_FILE):
        try:
            with open (GAMES_FILE, "r") as f:
                games = json.load(f)
        except json.JSONDecodeError:
            log('Invalid games file, creating new', 'warning')
            games = {}
    else:
        log('Games file not found, creating new', 'warning')
        games = {}
    return games

def clear_trash(user_called=True):
    from settings import TRASH_FOLDER, MAX_BACKUPS, GAMES_FILE
    from common import log
    
    # If called programmatically (from auto.py), clear all games
    if not user_called:
        log('Starting automatic trash cleanup')
        if not is_json_valid(GAMES_FILE):
            log('No valid games file found for trash cleanup', 'warning')
            return
        with open(GAMES_FILE, 'r') as f:
            games = json.load(f)
        cleared_games = []
        for game in games:
            success = clear_single_trash(TRASH_FOLDER, MAX_BACKUPS, game)
            if success:
                cleared_games.append(game)
        if cleared_games:
            log(f'Automatic trash cleanup completed for {len(cleared_games)} games: {cleared_games}')
        else:
            log('No trash cleanup needed')
        return
    
    # If called from main menu, show options
    input_message = '1: All games\n2: Specific game\n3: Return to main menu\nSelect what trash to clear'
    choice_num = int_range_input(input_message, 1, 3)
    print()
    choice_map = {
        1: 'all',
        2: 'specific',
        3: 'return'
    }
    func_choice = choice_map[choice_num]
    
    match func_choice:
        case 'all':
            if not is_json_valid(GAMES_FILE):
                print('[yellow]You have no game entries[/]')
                return
            with open(GAMES_FILE, 'r') as f:
                games = json.load(f)
            
            successful_clears = []
            for count, game in enumerate(games, 1):
                print()
                print(f'[bold][underline]{count}: {game}[/][/]')
                success = clear_single_trash(TRASH_FOLDER, MAX_BACKUPS, game)
                if success:
                    print(f'[green]Trash cleared for {game}[/]')
                    successful_clears.append(game)
                else:
                    print('[yellow]No trash was cleared[/]')
            if successful_clears:
                print(f'\n[green]Trash cleared for {len(successful_clears)} games[/]')
        case 'specific':
            if not is_json_valid(GAMES_FILE):
                print('[yellow]You have no game entries[/]')
                return
            _, game_choice = take_entry_input(keyword='to clear trash for', extra_info=False)
            success = clear_single_trash(TRASH_FOLDER, MAX_BACKUPS, game_choice)
            if success:
                print(f'[green]Trash cleared for {game_choice}[/]')
            else:
                print('[yellow]No trash was cleared[/]')
        case 'return':
            return

def clear_single_trash(trash_folder, max_backups, game_name):
    from common import log
    
    trash_path = Path(trash_folder)
    if not trash_path.exists():
        print(f'[yellow]Trash folder {trash_folder} does not exist[/]')
        log(f'Trash folder {trash_folder} does not exist', 'warning')
        return False

    game_trash_path = trash_path / game_name
    if not game_trash_path.exists() or not game_trash_path.is_dir():
        print(f'[yellow]No trash found for game {game_name}[/]')
        log(f'No trash found for game {game_name}', 'warning')
        return False

    try:
        backups = sorted(
            [f for f in game_trash_path.iterdir() if f.is_dir()],
            key=lambda x: x.name,
            reverse=True
        )
        
        if len(backups) <= max_backups:
            print(f'[blue]Game {game_name} has {len(backups)} backup(s) (within limit of {max_backups})[/]')
            log(f'Game {game_name} has {len(backups)} backup(s) (within limit of {max_backups})')
            return False
        
        deleted_count = 0
        old_backups = backups[max_backups:]
        
        print(f'[blue]Clearing {len(old_backups)} excess backups for {game_name}...[/]')
        log(f'Clearing {len(old_backups)} excess backups for {game_name}')
        
        for old_backup in old_backups:
            try:
                # Remove all files first
                for file in old_backup.rglob("*"):
                    if file.is_file():
                        file.unlink()
                
                # Remove directories (deepest first)
                for folder in sorted(old_backup.rglob("*"), reverse=True):
                    if folder.is_dir():
                        folder.rmdir()
                
                # Remove the backup folder itself
                old_backup.rmdir()
                deleted_count += 1
                
                log(f'Deleted backup: {old_backup.name}')
                
            except Exception as e:
                log(f'Error deleting backup {old_backup}: {e}', 'error')
                print(f'[red]Error deleting backup {old_backup.name}: {e}[/]')
                continue
        
        if deleted_count > 0:
            log(f'Cleared {deleted_count} old backups for {game_name}', 'info')
        
        # Remove game folder if it's empty
        if game_trash_path.exists() and not any(game_trash_path.iterdir()):
            game_trash_path.rmdir()
            log(f'Removed empty game folder {game_name}', 'info')
        
        return deleted_count > 0
    except Exception as e:
        log(f'Error processing game folder {game_name}: {e}', 'error')
        print(f'[red]Error processing game folder {game_name}: {e}[/]')
        return False