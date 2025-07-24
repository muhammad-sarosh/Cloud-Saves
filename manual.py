import platform
import socket
import json
import os
import sys
import supabase
from pathlib import Path

def load_cfg():
    if not is_json_valid("config.json"):
        with open("config.json", "w") as f:
            json.dump(default_config, f, indent=4)
            print('Your config.json file was either missing (if this is your first time running the program then this is normal), empty, or corrupted. It has been regenerated with the defaults. Please edit it and enter your supabase data api url and service_role api key and rerun the program.')
            sys.exit()

    with open("config.json", 'r') as f:
        config = json.load(f)
        url = config['supabase']['url']
        api_key = config['supabase']['api_key']
        gamesjson_file = config['gamesjson_file']
        if url == '' or api_key == '':
            print('The url and/or api_key values in your config.json file are empty. Please fill them with your supabase data api url and service_role api key and rerun the program.')
            sys.exit()
        return gamesjson_file, url, api_key


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

def write_new_path(games, entry_name_to_edit, gamesjson_file, system):
    if get_platform() != system:
        print(f'WARNING: Since you are currently not on {system} the program will not check to see if the entered {system} path is valid')
        system_path = input(f"\nEnter the new {system} save path for your game: ").strip()
    else:
        system_path = input(f"\nEnter the new {system} save path for your game: ").strip()
        while not os.path.exists(system_path):
            system_path = input(f"The entered {system} path is not valid. Please try again: ").strip()

    games[entry_name_to_edit][system] = system_path
    with open(gamesjson_file, 'w') as f:
        json.dump(games, f, indent=4)
    
    print('\nSave path successfully changed!')

def take_entry_input(keyword, print_paths=True):
    if not is_json_valid(gamesjson_file):
        print('You have no game entries\n')
        return

    with open(gamesjson_file, 'r') as f:
        games = json.load(f)

    # Taking input
    list_games(print_paths)
    while True:
        entry_num_to_modify = input(f'Entry number to {keyword}: ').strip()
        try: 
            entry_num_to_modify = int(entry_num_to_modify)
            if not (1 <= entry_num_to_modify <= len(games)):
                if len(games) > 1:
                    print(f'Input must be between 1 and {len(games)}\n')
                else:
                    print('Input out of range')
            else:
                break
        except ValueError:
            print('Input must be a valid number\n')

    # Converting name to index number
    games_keys = list(games)
    entry_name_to_modify = games_keys[entry_num_to_modify - 1]
    return games, entry_name_to_modify

    #for file_path in local_path.rglob("*"):
    #    if file_path.is_file():
        



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
    if os.path.exists(gamesjson_file):
        try:
            with open (gamesjson_file, "r") as f:
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
    with open(gamesjson_file, 'w') as f:
        json.dump(games, f, indent=4)

    print(f"\n{game_name} has been added successfully!\n")


def remove_game_entry():
    games,entry_name_to_del = take_entry_input('delete', False)
    del games[entry_name_to_del]

    with open(gamesjson_file, 'w') as f:
        json.dump(games, f, indent=4)

    print(f'\n{entry_name_to_del} has been removed from your games\n')



def edit_game_entry():
    games, entry_name_to_edit = take_entry_input('edit')

    while True:
        choice = input("\nSelect what to edit\n1: Entry name\n2: Windows path\n3: Linux path\n4: Return to main menu\n").strip()
        match choice:
            case "1":
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
                
                with open(gamesjson_file, 'w') as f:
                    json.dump(new_games, f, indent=4)
                print(f'\nEntry name successfully changed from {entry_name_to_edit} to {new_name}!\n')
            case "2":
                write_new_path(games, entry_name_to_edit, gamesjson_file, "windows")
            case "3":
                write_new_path(games, entry_name_to_edit, gamesjson_file, "linux")
            case "4":
                return
            case _:
                print("Invalid option. Please try again\n")

# print_paths determines whether the games save paths are printed along with the names
def list_games(print_paths=True):
    system = get_platform()
    if not is_json_valid(gamesjson_file):
        print('You have no game entries\n')
        return

    with open(gamesjson_file, 'r') as f:
        games = json.load(f)
    
    count = 1
    for game, paths in games.items():
        print(f"\033[1m{count}: {game}\033[0m")
        if print_paths:
            for system, path in paths.items():
                if path.strip():
                    print(f"\033[4m{system.capitalize()} Path:\033[0m {path}")
        count += 1
        if print_paths:
            print()

# Main

default_config = {
    "supabase": {
        "url": "",
        "api_key": ""
    },
    "gamesjson_file": "games.json",
    "upload_on_startup": False,
    "skip_extensions": ['.tmp'],
}

cfg = load_cfg()    
gamesjson_file, url, api_key = cfg

# Checking OS
operating_sys = get_platform()
if operating_sys == "unsupported":
    print("This program has detected your OS type as Unsupported. Press 'Enter' if you wish to continue")
    input()

internet_check()

local_path = "S:\\Miscellaneous\\Random\\test"
local_path = Path(local_path)

# Menu
while True:
    function_choice = input("Select your function or press 'Ctrl+C' to exit:\n1: Upload Save(s)\n2: Download Save(s)\n3: Check Save(s) Status\n4: Add game entry\n5: Remove game entry\n6: Edit game entry\n7: List games\n").strip()
    match function_choice:
        case "1":
            upload_save()
        case "2":
            pass
        case "3":
            pass
        case "4":
            add_game_entry()
        case "5":
            remove_game_entry()
        case "6":
            edit_game_entry()
        case "7":
            list_games()
        case _:
            print("Invalid option. Please try again")