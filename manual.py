import platform
import socket
import json
import os
import supabase
from pathlib import Path
import copy
from rich import print
from rich.traceback import install 

def regenerate_cfg():
    with open(config_file, "w") as f:
        print(f"No valid {config_file} found. A new one will be created.\n(If this is your first time running the program, this is normal)")
        url = get_supabase_info(0)
        api_key = get_supabase_info(1)
        games_file = default_config['games_file']
        skip_extensions = default_config['skip_extensions']
        temp_config = copy.deepcopy(default_config)
        temp_config['supabase']['url'] = url
        temp_config['supabase']['api_key'] = api_key
        json.dump(temp_config, f, indent=4)
        print('\nConfig file successfully regenerated!')
        return url, api_key, games_file, skip_extensions

def load_cfg():
    valid = is_json_valid(config_file)
    regenerate = False
    if valid:
        with open(config_file, 'r') as f:
            config = json.load(f)
            try:
                url = config['supabase']['url']
                api_key = config['supabase']['api_key']
                games_file = config['games_file']
                skip_extensions = config['skip_extensions']
            except:
                regenerate = True

    # If config missing, empty or in invalid format
    if not valid or regenerate == True:
        url, api_key, games_file, skip_extensions = regenerate_cfg()
    else:
        # Otherwise load config
        with open(config_file, 'r') as f:
            # Checking if anything is empty
            changed = False
            if url == '':
                print(f'The url value in your {config_file} is empty')
                url = get_supabase_info(0)
                config['supabase']['url'] = url
                changed = True
            if api_key == '':
                print(f'The api key value in your {config_file} is empty')
                api_key = get_supabase_info(1)
                config['supabase']['api_key'] = api_key      
                changed = True
            if games_file == '':
                config['games_file'] = 'games.json'
                changed = True
            
            if changed:
                with open(config_file, "w") as f:
                    json.dump(config, f, indent=4)
    return games_file, url, api_key, skip_extensions

# Takes integer input until valid
def int_range_input(input_message, min, max):
    while True:
        choice = input(input_message).strip()
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
        data = input(input_message).strip()
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

# If choice is 0 program inputs url. If choice is 1 program inputs api_key
def get_supabase_info(choice):
    if choice == 0:
        input_message = 'Enter your supabase data api url: '
    elif choice == 1:
        input_message = 'Enter your supabase service_role api key: '
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
def write_new_path(games, entry_name_to_edit, system):
    if get_platform() != system:
        print(f'WARNING: Since you are currently not on {system} the program will not check to see if the entered {system} path is valid')
        system_path = input(f"\nEnter the new {system} save path for your game: ").strip()
    else:
        system_path = input(f"\nEnter the new {system} save path for your game: ").strip()
        while not os.path.exists(system_path):
            system_path = input(f"The entered {system} path is not valid. Please try again: ").strip()

    games[entry_name_to_edit][system] = system_path
    with open(games_file, 'w') as f:
        json.dump(games, f, indent=4)
    
    print('\nSave path successfully changed!')

# To input game entry 
def take_entry_input(keyword, print_paths=True):
    if not is_json_valid(games_file):
        print('You have no game entries\n')
        return

    with open(games_file, 'r') as f:
        games = json.load(f)

    # Taking input
    list_games(print_paths)
    input_message = f'Enter the entry number to {keyword}: '
    entry_num_to_modify = int_range_input(input_message, 1, len(games))

    # Converting name to index number
    games_keys = list(games)
    entry_name_to_modify = games_keys[entry_num_to_modify - 1]
    return games, entry_name_to_modify
        
    
def upload_save(games=None, entry_name_to_modify=None):
    internet_check()
    client = supabase.create_client(url, api_key)
    if games==None and entry_name_to_modify==None:
        games, entry_name_to_modify = take_entry_input('upload', print_paths=False)

    local_path = Path(games[entry_name_to_modify][operating_sys])
    
    # .rglob recursively goes through every file and directory while maintaining subdirectories
    for file_path in local_path.rglob("*"):
        # Only need to upload files not folders, subdirectories will reamain intact because of .rglob
        if file_path.is_file():
            if file_path.suffix.lower() in skip_extensions:
                continue
            # Makes full path into relative path 
            relative_path = file_path.relative_to(local_path)
            upload_path = f"{entry_name_to_modify}/{relative_path}".replace('\\', '/')
            
            with open(file_path, 'rb') as f:
                client.storage.from_("game-saves").upload(upload_path, f)
                print(f"Uploaded: {upload_path}")

def download_save():
    pass

def check_save_status():
    pass

def add_game_entry():
    system = get_platform()
    
    # Loading file if exists else create new
    if os.path.exists(games_file):
        try:
            with open (games_file, "r") as f:
                games = json.load(f)
        except json.JSONDecodeError:
            games = {}
    else:
        games = {}

    # Getting game name and validating
    game_name = ''
    while game_name == '':
        game_name = input("Enter the name of your game: ").strip()
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
    system_path = input(f"\nEnter the {system} save path for your game: ").strip()
    while not os.path.exists(system_path):
        system_path = input(f"The entered {system} path is not valid. Please try again: ").strip()
    
    choice = input(f"\nDo you want to add the {secondary_system} save path? Please note that if you choose yes, the program will not check if the entered path is valid (y/n): ").strip().lower()
    while True:
        if choice == 'y':
            secondary_path = input(f"Enter the {secondary_system} save path for your game: ").strip()
            break
        elif choice == 'n':
            secondary_path = ''
            break
        else:
            choice = input("Incorrect input. Please answer with 'y' or 'n': ").strip().lower()

    # Adding entry to file        
    games[game_name] = {
        f"{system}": system_path,
        f"{secondary_system}": secondary_path 
    }

    # Writing changes to file
    with open(games_file, 'w') as f:
        json.dump(games, f, indent=4)

    print(f"\n{game_name} has been added successfully!")


def remove_game_entry():
    games,entry_name_to_del = take_entry_input('delete', False)
    del games[entry_name_to_del]

    with open(games_file, 'w') as f:
        json.dump(games, f, indent=4)

    print(f'\n{entry_name_to_del} has been removed from your games')



def edit_game_entry():
    games, entry_name_to_edit = take_entry_input('edit')
    input_message = "\n1: Entry name\n2: Windows path\n3: Linux path\n4: Return to main menu\nSelect what to edit: "
    
    while True:
        choice = int_range_input(input_message, 1, 4)
        match choice:
            case 1:
                while True:
                    # Taking input
                    new_name = input('Enter new entry name: ').strip()
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
                
                with open(games_file, 'w') as f:
                    json.dump(new_games, f, indent=4)
                print(f'\nEntry name successfully changed from {entry_name_to_edit} to {new_name}!')
            case 2:
                write_new_path(games, entry_name_to_edit, "windows")
            case 3:
                write_new_path(games, entry_name_to_edit, "linux")
            case 4:
                return
            case _:
                print("Invalid option. Please try again\n")

# print_paths determines whether the games save paths are printed along with the names
def list_games(print_paths=True):
    system = get_platform()
    if not is_json_valid(games_file):
        print('You have no game entries\n')
        return

    with open(games_file, 'r') as f:
        games = json.load(f)
    
    count = 1
    for game, paths in games.items():
        print(f"[bold]{count}: {game}[/]")
        if print_paths:
            for system, path in paths.items():
                if path.strip():
                    print(f"[underline]{system.capitalize()} Path:[/] {path}")
        count += 1
        if print_paths:
            print()

def edit_supabase_info():
    while True:
        input_message = '1: Supabase Data API URL\n2: Supabase service_role API Key\n3: Return to main menu\nSelect what to edit: '
        choice = int_range_input(input_message, 1, 3)
        match choice:
            case 1:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                url = get_supabase_info(0)
                config['supabase']['url'] = url
            case 2:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                api_key = get_supabase_info(1)
                config['supabase']['api_key'] = api_key
            case 3:
                return
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)
        print('Data successfully updated!\n')
        
# Main

# Rich traceback install
install()

print("[bold]=== Cloud Save Manager ===[/]")

default_config = {
    "supabase": {
        "url": "",
        "api_key": ""
    },
    "games_file": "games.json",
    "upload_on_startup": False,
    "skip_extensions": ['.tmp'],
}

config_file = 'config.json'
games_file, url, api_key, skip_extensions = load_cfg()    

# Checking OS
operating_sys = get_platform()
if operating_sys == "unsupported":
    print("This program has detected your OS type as Unsupported. Press 'Enter' if you wish to continue")
    input()

internet_check()

# Menu
function_input_message = "\n1: Upload Save(s)\n2: Download Save(s)\n3: Check Save(s) Status\n4: Add game entry\n5: Remove game entry\n6: Edit game entry\n7: List games\n8: Edit Supabase info\nSelect your function or press 'Ctrl+C' to exit: "
while True:
    function_choice = int_range_input(function_input_message, 1, 8)
    print()
    match function_choice:
        case 1:
            upload_save()
        case 2:
            pass
        case 3:
            pass
        case 4:
            add_game_entry()
        case 5:
            remove_game_entry()
        case 6:
            edit_game_entry()
        case 7:
            list_games()
        case 8:
            edit_supabase_info()