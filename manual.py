import platform
import socket
import json
import os
import shutil
import supabase
from pathlib import Path
import copy
from rich import print
from rich.traceback import install
from rich.prompt import Prompt
from rich.progress import Progress
import hashlib
from types import SimpleNamespace
from datetime import datetime, timezone, timedelta

def regenerate_cfg(config_file, default_config):
    with open(config_file, "w") as f:
        print(f"[yellow]No valid {config_file} found. A new one will be created."\
              "\n(If this is your first time running the program, this is normal)[/]")
        url = get_supabase_info(choice='url')
        api_key = get_supabase_info(choice='api key')
        games_file = default_config['games_file']
        skip_extensions = default_config['skip_extensions']
        games_bucket = default_config['supabase']['games_bucket']
        table_name = default_config['supabase']['table_name']
        temp_config = copy.deepcopy(default_config)
        temp_config['supabase']['url'] = url
        temp_config['supabase']['api_key'] = api_key
        json.dump(temp_config, f, indent=4)
        print('\nConfig file successfully regenerated')
        return url, api_key, games_file, skip_extensions, games_bucket, table_name

def load_cfg(config_file, default_config):
    valid = is_json_valid(config_file)
    regenerate = False
    if valid:
        # Checking if any of the required values are missing
        with open(config_file, 'r') as f:
            loaded_config = json.load(f)
            try:
                url = loaded_config['supabase']['url']
                api_key = loaded_config['supabase']['api_key']
                games_file = loaded_config['games_file']
                skip_extensions = loaded_config['skip_extensions']
                games_bucket = loaded_config['supabase']['games_bucket']
                table_name = loaded_config['supabase']['table_name']
            except:
                regenerate = True

    # If config missing, empty or in invalid format
    if not valid or regenerate:
        url, api_key, games_file, skip_extensions, games_bucket, table_name = regenerate_cfg(config_file, default_config)
    else:
        # Otherwise load config
        with open(config_file, 'r') as f:
            # Checking if anything is empty
            changed = False
            if url == '':
                print(f'The url value in your {config_file} is empty')
                url = get_supabase_info(choice='url')
                loaded_config['supabase']['url'] = url
                changed = True
            if api_key == '':
                print(f'The api key value in your {config_file} is empty')
                api_key = get_supabase_info(choice='api key')
                loaded_config['supabase']['api_key'] = api_key      
                changed = True
            if games_file == '':
                loaded_config['games_file'] = default_config['games_file']
                changed = True
            if games_bucket == '':
                loaded_config['supabase']['games_bucket'] = default_config['supabase']['games_bucket']
                changed = True
            if table_name == '':
                loaded_config['supabase']['table_name'] = default_config['supabase']['table_name']
                changed = True
            if changed:
                with open(config_file, "w") as f:
                    json.dump(loaded_config, f, indent=4)
    return SimpleNamespace(
        config_file=config_file,
        url=url,
        api_key=api_key,
        games_bucket=games_bucket,
        table_name=table_name,
        games_file=games_file,
        skip_extensions=skip_extensions,
        required_columns={
            'game_name':'game_name',
            'hash':'hash',
            'updated_at':'updated_at'
        }
    )

# Takes integer input until valid
def int_range_input(input_message, min, max):
    while True:
        choice = Prompt.ask(input_message).strip()
        try: 
            choice = int(choice)
            if not (min <= choice <= max):
                print('Input out of range')
            else:
                return choice
        except ValueError:
            print('Input must be a valid number\n')

def str_input(input_message):
    data = ''
    while data == '':
        data = Prompt.ask(input_message).strip()
        if data == '':
            print('Input cannot be empty')
    return data

# Checks OS Type
def get_platform():
    system = platform.system()
    if system == "Windows": return "windows"
    elif system == "Linux": return "linux"
    else: return "unsupported"

# Doesn't let the user continue until they have internet access
def internet_check(host="8.8.8.8", port=53, timeout=3):
    while True:
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return
        except socket.error:
            print("No internet access detected. Press 'Enter' to retry or 'Ctrl + C' to exit")
            input()

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

def get_supabase_info(choice):
    if choice == 'url':
        input_message = 'Enter your supabase data api url'
    elif choice == 'api key':
        input_message = 'Enter your supabase service_role api key'
    elif choice == 'bucket name':
        input_message = 'Enter your supabase bucket name'
    elif choice == 'table name':
        input_message = 'Enter your supabase database table name'
    data = str_input(input_message)
    return data

def is_json_valid(file):
    try:
        with open(file, 'r') as f:
            loaded_file = json.load(f)
        # File is either fine or just '{}' in which case it returns False
        return bool(loaded_file)
    # File doesnt exist or is empty/invalid
    except (FileNotFoundError, json.JSONDecodeError):
        return False

# To update game entry paths
def write_new_path(config, games, entry_name_to_edit, system):
    if get_platform() != system:
        print(f'WARNING: Since you are currently not on {system} the program will not check to see if the entered {system} path is valid')
        system_path = Prompt.ask(f"\nEnter the new {system} save path for your game").strip()
    else:
        system_path = Prompt.ask(f"\nEnter the new {system} save path for your game").strip()
        while not os.path.exists(system_path):
            system_path = Prompt.ask(f"The entered {system} path is not valid. Please try again").strip()

    games[entry_name_to_edit][system] = system_path
    with open(config.games_file, 'w') as f:
        json.dump(games, f, indent=4)
    
    print('\nSave path successfully changed')

# To input game entry. Returns None if there are no entries
def take_entry_input(config, keyword, print_paths=True):
    if not is_json_valid(config.games_file):
        print('You have no game entries')
        return

    with open(config.games_file, 'r') as f:
        games = json.load(f)

    # Taking input
    list_games(config=config, print_paths=print_paths)
    input_message = f'Enter the entry number {keyword}'
    entry_num_to_modify = int_range_input(input_message, 1, len(games))

    # Converting name to index number
    games_keys = list(games)
    entry_name_to_modify = games_keys[entry_num_to_modify - 1]
    return games, entry_name_to_modify

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

# Returns True if everthing is valid. Returns False and updates info if anything was invalid
# Returns -1 if unexpected error
def supabase_validation(config):
    internet_check()
    try:
        # Checks URL and API key
        client = supabase.create_client(config.url, config.api_key)

        # Checks Bucket
        all_buckets = client.storage.list_buckets()
        bucket_exists = any(b.name == config.games_bucket for b in all_buckets)
        if not bucket_exists:
            print(f'[red]The Supabase games bucket name in your {config.config_file} is incorrect as no bucket exists with this name.'\
                  ' You will be repeatedly prompted to update it until you enter it correctly[/]') 
            edit_supabase_info(choice='bucket name', config=config, user_called=False)
            return False
        
        # Checks if table exists
        client.table(config.table_name).select("*").limit(1).execute()

        missing_columns = []
        type_mismatch_columns = []
        for column in config.required_columns:
            try:
                # Checks if table contains required columns
                client.table(config.table_name).select(column).limit(1).execute()
                # Check if type of each column is correct
                if column == config.required_columns['game_name'] or column == config.required_columns['hash']:
                        client.table(config.table_name).select(column).eq(column, "").limit(1).execute()
                elif column == config.required_columns['updated_at']:
                        # Giving a datetime query that would only work with a timestamp object
                        client.table(config.table_name).select(column).eq(column, datetime.now() + timedelta(days=1)).limit(1).execute()
            except Exception as e:
                e_str = getattr(e, "message", None)
                e_str = e_str.lower() if e_str else str(e).lower()
                if 'column' in e_str and 'does not exist' in e_str:
                    missing_columns.append(column)
                elif 'invalid input syntax' in  e_str:
                    type_mismatch_columns.append(column)
                else:
                    print(f"[red]ERROR:[/] {e}")
                    return -1
        if len(missing_columns) > 0 or len(type_mismatch_columns) > 0:
            if len(missing_columns) > 0:
                formatted = ", ".join(missing_columns)
                print(f"[red]The column(s) [underline]{formatted}[/] are missing from your table[/]")
            if len(type_mismatch_columns) > 0:
                formatted = ", ".join(type_mismatch_columns)
                print(f"[red]The column(s) [underline]{formatted}[/] have the wrong data type. These are the required data types for each column:[/]\n"\
                      f"[red]{config.required_columns['game_name']}: text\n{config.required_columns['hash']}: text\n{config.required_columns['updated_at']}: timestamptz[/]")
            print("[red]Please make the required changes and rerun the function[/]")
            return -1
        # Everything checks out
        return True
    except Exception as e:
        e_str = getattr(e, "message", None)
        e_str = e_str.lower() if e_str else str(e).lower()
        if e_str == 'invalid url':
            print(f'[red]The Supabase data api url in your {config.config_file} is incorrect. You will be repeatedly prompted to update it until you enter it correctly[/]')
            edit_supabase_info(choice='url', config=config, user_called=False)
            return False
            
        elif e_str == 'invalid compact jws' or e_str == 'jws protected header is invalid':
            print(f'[red]The Supabase service_role api key in your {config.config_file} is incorrect. You will be repeatedly prompted to update it until you enter it correctly[/]')
            edit_supabase_info(choice='api key', config=config, user_called=False)
            return False
        elif 'relation' in e_str and 'does not exist' in e_str:
            print(f'[red]The Supabase table name in your {config.config_file} is incorrect as a table with this name does not exist. You will be repeatedly prompted to update it until you enter it correctly[/]') 
            edit_supabase_info(choice='table name', config=config, user_called=False)
            return False
        else:
            print(f"[red]ERROR:[/] {e}")
            return -1

def loop_supabase_validation(config):
    print('[blue]Connecting to Supabase...[/]\n')
    # Loop until all supabase data is validated and updated
    while True:
        valid = supabase_validation(config)
        # Unexpected error
        if valid == -1:
            return valid
        # Data is completely valid
        if valid:
            return valid   

def remove_supabase_files(config, client, entry_name_to_del):
    files_to_delete = list_all_supabase_files(config=config, client=client, folder=f"{entry_name_to_del}/")
    if files_to_delete == -1:
        return
    if files_to_delete:
        internet_check()
        try:
            client.storage.from_(config.games_bucket).remove(files_to_delete)
        except Exception as e:
            print(f"[red]ERROR: {e}[/]")

def edit_game_name(config, games, entry_name_to_edit):
    if loop_supabase_validation(config=config) == -1:
        return
    while True:
        # Taking input
        new_name = Prompt.ask('Enter new entry name').strip()
        if new_name == '':
            print('Entry name cannot be empty. Please try again\n')
        elif new_name in games:
            print('This entry already exists. Please try again\n')
        else:
            break
    
    print('\n[blue]Editing local data...[/]')
    # Copying old items without changing order
    new_games = {}
    for key, value in games.items():
        if key == entry_name_to_edit:
            new_games[new_name] = value
        else:
            new_games[key] = value
    
    with open(config.games_file, 'w') as f:
        json.dump(new_games, f, indent=4)

    # Moving Supabase files and deleting old ones
    # Also editing table data
    print(f'\n[blue]Editing Supabase data...[/]')
    client = supabase.create_client(config.url, config.api_key)
    files_to_move = list_all_supabase_files(config=config, client=client, folder=f"{entry_name_to_edit}/")
    if files_to_move == -1:
        return
    try:
        upload_save(config=config, games=new_games, entry_name_to_upload=new_name, user_called=False, update_table=False)
    except Exception as e:
        print(f'[red]ERROR: {e}[/]')

    try:
        remove_supabase_files(config=config, client=client, entry_name_to_del=entry_name_to_edit)
    except Exception as e:
        print(f'[red]ERROR: {e}[/]')

    try:
        client.table(config.table_name).update({
            config.required_columns['game_name']: new_name
        }).eq(config.required_columns['game_name'], entry_name_to_edit).execute()
    except Exception as e:
        print(f'[red]ERROR: {e}[/]')

    print(f'[green]Entry name successfully changed from {entry_name_to_edit} to {new_name}[/]')

# Returns -1 if error
def list_all_supabase_files(config, client, folder):
    try:
        internet_check()
        full_file_paths = []

        items = client.storage.from_(config.games_bucket).list(folder)
        for item in items:
            name = item["name"]
            full_path = f"{folder}{name}"

            # Check if item is a folder
            if "." not in name:
                # Recursive call into subfolder
                subfiles = list_all_supabase_files(config=config, client=client, folder=f"{full_path}/")
                full_file_paths.extend(subfiles)
            else:
                full_file_paths.append(full_path)
        return full_file_paths
    except Exception as e:
        print(f"[red]ERROR: {e}[/]")
        return -1

def upload_save(config, games=None, entry_name_to_upload=None, user_called=True, update_table=True):
    # loop_supabase_validation() already called in edit_game_name() function if update_table is False
    if update_table:
        if loop_supabase_validation(config=config) == -1:
            return
    client = supabase.create_client(config.url, config.api_key)
    if user_called:
        response = take_entry_input(config=config, keyword='to upload', print_paths=False)
        # True if there are no game entries
        if response == None:
            return
        games, entry_name_to_upload = response

    operating_sys = get_platform()
    local_path = Path(games[entry_name_to_upload][operating_sys])
    if not os.path.exists(local_path):
        print('\n[yellow]The save directory provided for this game is invalid[/]')
        return
    files_to_upload = [f for f in local_path.rglob('*') if f.is_file() and f.suffix.lower() not in config.skip_extensions]
    if not files_to_upload:
        print('\n[yellow]The save directory for this game contains no files[/]')
        return
    
    # Initialising progress bar
    with Progress() as progress:
        if user_called:
            task = progress.add_task("[cyan]Uploading files...", total=len(files_to_upload))
        # .rglob recursively goes through every file and directory while maintaining subdirectories
        for file_path in files_to_upload:
            # Makes full path into relative path 
            relative_path = file_path.relative_to(local_path)
            upload_path = f"{entry_name_to_upload}/{relative_path}".replace('\\', '/')

            # Updating current file name in progress bar
            if user_called:
                progress.update(task, description=f"[cyan]Uploading:[/] {relative_path.name}")
            
            # Checking if file already exists in Supabase, if yes then use
            # update() otherwise use .upload()
            try:
                with open(file_path, 'rb') as f:
                    client.storage.from_(config.games_bucket).update(upload_path, f)
            except Exception as e:
                if "Not found" in str(e) or "404" in str(e):
                    with open(file_path, 'rb') as f2:
                        client.storage.from_(config.games_bucket).upload(upload_path, f2)
                else:
                    raise
            if user_called:
                progress.advance(task)

    if update_table:
        folder_hash = hash_save_folder(config=config, path=local_path)
        row = {
            config.required_columns['game_name']: entry_name_to_upload,
            config.required_columns['hash']: folder_hash,
            config.required_columns['updated_at']: datetime.now(timezone.utc).isoformat()
        }
        try:
            client.table(config.table_name).upsert(row).execute()
        except Exception as e:
            print(f"[red]Failed to update table data for {entry_name_to_upload}: {e}[/]")

    if user_called:
        print('\n[green]All files successfully uploaded[/]')

def download_save(config, response=None, user_called=True):
    internet_check()
    
    client = supabase.create_client(config.url, config.api_key)
    
    operating_sys = get_platform()
    if user_called:
        response = take_entry_input(config=config, keyword="which's save you want to download", print_paths=False)
    # True if there are no game entries
    if response == None:
        return
    games, entry = response

    source_path = Path(games[entry][operating_sys])
    if not os.path.exists(source_path):
        print('[yellow]The save directory provided for this game is invalid[/]')
        return

    print('\n[blue]Connecting to Supabase...[/]\n')

    if loop_supabase_validation(config=config) == -1:
        return

    response = client.table(config.table_name).select("*").eq(config.required_columns['game_name'], entry).execute()
    row = response.data[0] if response.data else None
    if row is None:
        print(f'[yellow]No table data exists for the game {entry}[/]')
        return
    
    file_list = client.storage.from_(config.games_bucket).list(f"{entry}/")
    if not file_list:
        print(f'[yellow]No cloud data exists for the game {entry}[/]')
        return
    
    source_hash = hash_save_folder(config=config, path=source_path)
    cloud_hash = row[config.required_columns['hash']]

    if source_hash == cloud_hash:
        choice = Prompt.ask(f"[yellow]Your local and cloud save files are currently the same. Do you still want to continue? (y/n)[/]").strip().lower()
        while True:
            if choice == 'y':
                break
            elif choice == 'n':
                return
            else:
                choice = Prompt.ask("Incorrect input. Please answer with 'y' or 'n'").strip().lower()

    trash_folder_path = Path(__file__).parent / "Trash"
    game_folder_path = trash_folder_path / entry
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = game_folder_path / timestamp

    print('[blue]Gathering data from Supabase...[/]')

    files_to_download = list_all_supabase_files(config=config, client=client, folder=f"{entry}/")
    if files_to_download == -1:
        return
    
    move_files(source_path=source_path, backup_path=backup_path)

    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]Downloading files...", total=len(files_to_download))
            
            for file_path in files_to_download:
                relative_path = Path(file_path.replace(f"{entry}/", "", 1))
                destination_path = source_path / relative_path

                progress.update(task, description=f"[cyan]Downloading:[/] {relative_path.name}")

                downloaded_file = client.storage.from_(config.games_bucket).download(file_path)
                
                # Making sure destination folders exist
                destination_path.parent.mkdir(parents=True, exist_ok=True)

                with open(destination_path, 'wb') as f:
                    f.write(downloaded_file)
                progress.advance(task)
    except Exception as e:
        print(f"[red]ERROR: {e}[/]")
        return

    print('\n[green]All files successfully downloaded[/]')

def check_save_status():
    pass

def add_game_entry(config):
    system = get_platform()
    
    # Loading file if exists else create new
    if os.path.exists(config.games_file):
        try:
            with open (config.games_file, "r") as f:
                games = json.load(f)
        except json.JSONDecodeError:
            games = {}
    else:
        games = {}

    # Getting game name and validating
    game_name = ''
    while game_name == '':
        game_name = Prompt.ask("Enter the name of your game").strip()
        if game_name == '':
            print("Game name cannot be empty. Please try again\n")

    if game_name in games:
        print(f"{game_name} already exists in your list\n")
        return
    
    if system == "windows":
        secondary_system = "linux"
    else:
        secondary_system = "windows"

    # Inputting save paths
    system_path = Prompt.ask(f"\nEnter the {system} save path for your game").strip()
    while not os.path.exists(system_path):
        system_path = Prompt.ask(f"The entered {system} path is not valid. Please try again").strip()
    
    choice = Prompt.ask(f"\nDo you want to add the {secondary_system} save path? Please note that if you choose yes, the program will not check if the entered path is valid (y/n)").strip().lower()
    while True:
        if choice == 'y':
            secondary_path = Prompt.ask(f"Enter the {secondary_system} save path for your game").strip()
            break
        elif choice == 'n':
            secondary_path = ''
            break
        else:
            choice = Prompt.ask("Incorrect input. Please answer with 'y' or 'n'").strip().lower()

    # Adding entry to file        
    games[game_name] = {
        f"{system}": system_path,
        f"{secondary_system}": secondary_path 
    }

    # Writing changes to file
    with open(config.games_file, 'w') as f:
        json.dump(games, f, indent=4)

    print(f"\n{game_name} has been added successfully")


def remove_game_entry(config, games, entry_name_to_del):
    if loop_supabase_validation(config=config) == -1:
        return
    games, entry_name_to_del = take_entry_input(config=config, keyword='to delete', print_paths=False)

    choice = Prompt.ask(f"[yellow]Are you sure you want to remove [underline]{entry_name_to_del}[/] (y/n)[/]").strip().lower()
    while True:
        if choice == 'y':
            break
        elif choice == 'n':
            return
        else:
            choice = Prompt.ask("Incorrect input. Please answer with 'y' or 'n'").strip().lower()
    
    print('\n[blue]Removing files from Supabase...[/]')
    client = supabase.create_client(config.url, config.api_key)
    remove_supabase_files(config=config, client=client, entry_name_to_del=entry_name_to_del)

    # Removing table data
    try:
        client.table(config.table_name).delete().eq(config.required_columns['game_name'], entry_name_to_del).execute()
    except Exception as e:
        print(f"[red]ERROR: {e}[/]")

    print('\n[blue]Removing local entry...[/]')
    del games[entry_name_to_del]

    with open(config.games_file, 'w') as f:
        json.dump(games, f, indent=4)

    print(f'\n[green]{entry_name_to_del} has been removed from your games[/]')

def edit_game_entry(config):
    games, entry_name_to_edit = take_entry_input(config=config, keyword='to edit')
    input_message = "\n1: Entry name\n2: Windows path\n3: Linux path\n4: Return to main menu\nSelect what to edit"
    
    while True:
        choice = int_range_input(input_message, 1, 4)
        print()
        match choice:
            case 1:
                edit_game_name(config=config, games=games, entry_name_to_edit=entry_name_to_edit)
            case 2:
                write_new_path(config=config, games=games, entry_name_to_edit=entry_name_to_edit, system="windows")
            case 3:
                write_new_path(config=config, games=games, entry_name_to_edit=entry_name_to_edit, system="linux")
            case 4:
                return

# print_paths determines whether the games save paths are printed along with the names
def list_games(config, print_paths=True):
    if not is_json_valid(config.games_file):
        print('You have no game entries\n')
        return

    with open(config.games_file, 'r') as f:
        games = json.load(f)
    
    for count, (game, paths) in enumerate(games.items(), 1):
        print(f"[bold]{count}: {game}[/]")
        if print_paths:
            for system, path in paths.items():
                if path.strip():
                    print(f"[underline]{system.capitalize()} Path:[/] [purple]{path}[/]")
        if print_paths:
            print()

def edit_supabase_info(config, choice=None, user_called=True):
    while True:
        with open(config.config_file, 'r') as f:
            loaded_config = json.load(f)
        if user_called:
            input_message = '1: Supabase Data API URL\n2: Supabase service_role API Key\n3: Supabase bucket name\n4: Supabase database table name\n5: Return to main menu\nSelect what to edit'
            choice_num = int_range_input(input_message, 1, 5)
            choice_map = {
                1: 'url',
                2: 'api key',
                3: 'bucket name',
                4: 'table name',
                5: 'exit'
            }
            choice = choice_map[choice_num]
        match choice:
            case 'url':
                loaded_config['supabase']['url'] = get_supabase_info(choice='url')
                config.url = loaded_config['supabase']['url']
            case 'api key':
                loaded_config['supabase']['api_key'] = get_supabase_info(choice='api key')
                config.api_key = loaded_config['supabase']['api_key']
            case 'bucket name':
                loaded_config['supabase']['games_bucket'] = get_supabase_info(choice='bucket name')
                config.games_bucket = loaded_config['supabase']['games_bucket']
            case 'table name':
                loaded_config['supabase']['table_name'] = get_supabase_info(choice='table name')
                config.table_name = loaded_config['supabase']['table_name']
            case 'exit':
                return
        with open(config.config_file, 'w') as f:
            json.dump(loaded_config, f, indent=4)
        if not user_called:
            return
        print('[green]Data successfully updated[/]\n')


        
# Main

# Rich traceback install
install()

global_default_config = {
    "supabase": {
        "url": "",
        "api_key": "",
        "games_bucket":"game-saves",
        "table_name":"saves-data"
    },
    "games_file": "games.json",
    "upload_on_startup": False,
    "skip_extensions": ['.tmp'],
}

global_config_file = "config.json"
global_config = load_cfg(config_file=global_config_file, default_config=global_default_config)
# Checking OS
global_operating_sys = get_platform()
if global_operating_sys == "unsupported":
    print("This program has detected your OS type as Unsupported. Press 'Enter' if you wish to continue")
    input()

# Menu
function_input_message = "\n[bold]=== Cloud Saves ===[/]\n1: Upload Save(s)\n2: Download Save(s)\n" \
"3: Check Save(s) Status\n4: Add game entry\n5: Remove game entry\n6: Edit game entry\n7: List games\n" \
"8: Edit Supabase info\nSelect your function or press 'Ctrl+C' to exit"
while True:
    function_choice = int_range_input(function_input_message, 1, 8)
    print()
    match function_choice:
        case 1:
            upload_save(config=global_config)
        case 2:
            download_save(config=global_config)
            pass
        case 3:
            pass
        case 4:
            add_game_entry(config=global_config)
        case 5:
            remove_game_entry(config=global_config)
        case 6:
            edit_game_entry(config=global_config)
        case 7:
            list_games(config=global_config)
        case 8:
            edit_supabase_info(config=global_config)