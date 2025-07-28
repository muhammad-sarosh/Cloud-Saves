import platform
import socket
import json
import os
import supabase
from pathlib import Path
import copy
from rich import print
from rich.traceback import install
from rich.prompt import Prompt
from rich.progress import Progress
import hashlib
from types import SimpleNamespace

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
        print('\nConfig file successfully regenerated!')
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
    if not valid or regenerate == True:
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
        required_columns=['game_name', 'hash', 'updated_at']
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
    # Does file exist
    if not os.path.exists(file):
        return False
    try:
        with open(file, 'r') as f:
            loaded_file = json.load(f)
    except json.JSONDecodeError:
    # File is completely empty
        return False
    # File is just '{}'
    if not loaded_file:
        return False
    return True

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
    
    print('\nSave path successfully changed!')

# To input game entry. Returns None if there are no entries
def take_entry_input(config, keyword, print_paths=True):
    if not is_json_valid(config.games_file):
        print('You have no game entries')
        return

    with open(config.games_file, 'r') as f:
        games = json.load(f)

    # Taking input
    list_games(config=config, print_paths=print_paths)
    input_message = f'Enter the entry number to {keyword}'
    entry_num_to_modify = int_range_input(input_message, 1, len(games))

    # Converting name to index number
    games_keys = list(games)
    entry_name_to_modify = games_keys[entry_num_to_modify - 1]
    return games, entry_name_to_modify

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
            edit_supabase_info(choice='bucket name', config=config)
            return False
        
        # Checks if table exists
        client.table(config.table_name).select("*").limit(1).execute()

        # Checks if table contains required columns
        missing_columns = []
        for column in config.required_columns:
            try:
                client.table(config.table_name).select(column).limit(1).execute()
            except Exception as e:
                e_str = getattr(e, "message", None)
                e_str = e_str.lower() if e_str else str(e).lower()
                if 'column' in e_str and 'does not exist' in e_str:
                    missing_columns.append(column)
                else:
                    print(f"[red]ERROR:[/] {e}")
                    return -1
        if len(missing_columns) > 0:
            formatted = ", ".join(missing_columns)
            print(f"[red]The column(s) [underline]{formatted}[/] are missing from your table. Please create these columns and rerun the program[/]")
            return -1
        # Everything checks out
        return True
    except Exception as e:
        e_str = getattr(e, "message", None)
        e_str = e_str.lower() if e_str else str(e).lower()
        if e_str == 'invalid url':
            print(f'[red]The Supabase data api url in your {config.config_file} is incorrect. You will be repeatedly prompted to update it until you enter it correctly[/]')
            edit_supabase_info(choice='url', config=config)
            return False
        elif e_str == 'invalid compact jws' or e_str == 'jws protected header is invalid':
            print(f'[red]The Supabase service_role api key in your {config.config_file} is incorrect. You will be repeatedly prompted to update it until you enter it correctly[/]')
            edit_supabase_info(choice='api key', config=config)
            return False
        elif 'relation' in e_str and 'does not exist' in e_str:
            print(f'[red]The Supabase table name in your {config.config_file} is incorrect as a table with this name does not exist. You will be repeatedly prompted to update it until you enter it correctly[/]') 
            edit_supabase_info(choice='table name', config=config)
            return False
        else:
            print(f"[red]ERROR:[/] {e}")
            return -1

def upload_save(config, games=None, entry_name_to_modify=None):
    # Loop until all supabase data is validated and updated
    while True:
        valid = supabase_validation(config)
        # Unexpected error
        if valid == -1:
            return
        # Data is completely valid
        elif valid:
            break
    client = supabase.create_client(config.url, config.api_key)
    if games == None and entry_name_to_modify == None:
        user_called = True
        response = take_entry_input(config=config, keyword='upload', print_paths=False)
        # True if there are no game entries
        if response == None:
            return
        games, entry_name_to_modify = response
    else:
        user_called = False

    local_path = Path(games[entry_name_to_modify][operating_sys])
    files_to_upload = [f for f in local_path.rglob('*') if f.is_file() and f.suffix.lower() not in config.skip_extensions]
    if not files_to_upload:
        print('\n[yellow]The save directory for this game contains no files[/]')
        return
    
    # Initialising progress bar
    with Progress() as progress:
        task = progress.add_task("[cyan]Uploading files...", total=len(files_to_upload))
        # .rglob recursively goes through every file and directory while maintaining subdirectories
        for file_path in files_to_upload:
            # Makes full path into relative path 
            relative_path = file_path.relative_to(local_path)
            upload_path = f"{entry_name_to_modify}/{relative_path}".replace('\\', '/')

            # Updating current file name in progress bar
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
            progress.advance(task)
    if user_called:
        print('\n[green]All files successfully uploaded![/]')

def download_save():
    pass

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

    print(f"\n{game_name} has been added successfully!")


def remove_game_entry(config):
    games,entry_name_to_del = take_entry_input(config=config, keyword='delete', print_paths=False)
    del games[entry_name_to_del]

    with open(config.games_file, 'w') as f:
        json.dump(games, f, indent=4)

    print(f'\n{entry_name_to_del} has been removed from your games')



def edit_game_entry(config):
    games, entry_name_to_edit = take_entry_input(config=config, keyword='edit')
    input_message = "\n1: Entry name\n2: Windows path\n3: Linux path\n4: Return to main menu\nSelect what to edit"
    
    while True:
        choice = int_range_input(input_message, 1, 4)
        match choice:
            case 1:
                while True:
                    # Taking input
                    new_name = Prompt.ask('Enter new entry name').strip()
                    if new_name == '':
                        print('Entry name cannot be empty. Please try again\n')
                    elif new_name in games:
                        print('This entry already exists. Please try again\n')
                    else:
                        break
                
                # Copying old items without changing order
                new_games = {}
                for key, value in games.items():
                    if key == entry_name_to_edit:
                        new_games[new_name] = value
                    else:
                        new_games[key] = value
                
                with open(config.games_file, 'w') as f:
                    json.dump(new_games, f, indent=4)
                print(f'\nEntry name successfully changed from {entry_name_to_edit} to {new_name}!')
            case 2:
                write_new_path(config, games, entry_name_to_edit, "windows")
            case 3:
                write_new_path(config, games, entry_name_to_edit, "linux")
            case 4:
                return
            case _:
                print("Invalid option. Please try again\n")

# print_paths determines whether the games save paths are printed along with the names
def list_games(config, print_paths=True):
    if not is_json_valid(config.games_file):
        print('You have no game entries\n')
        return

    with open(config.games_file, 'r') as f:
        games = json.load(f)
    
    count = 1
    for game, paths in games.items():
        print(f"[bold]{count}: {game}[/]")
        if print_paths:
            for system, path in paths.items():
                if path.strip():
                    print(f"[underline]{system.capitalize()} Path:[/] [purple]{path}[/]")
        count += 1
        if print_paths:
            print()

def edit_supabase_info(config, choice=None):
    # To track whether user called or function called as the value of choice will change
    if choice == None:
        user_called = True
    else:
        user_called = False
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
        print('[green]Data successfully updated![/]\n')


        
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
operating_sys = get_platform()
if operating_sys == "unsupported":
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