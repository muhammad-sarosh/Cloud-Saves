import platform
import socket
import json
import os
import supabase

# Checks OS Type
def get_platform():
    system = platform.system()
    if system == "Windows": return "windows"
    elif system == "Linux": return "linux"
    else: return "unsupported"

# Attempts to connect to google servers
def has_internet(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False
    
# Doesn't let the user continue until they have internet access
def internet_check():
    while not has_internet():
        print("No internet access detected. Press 'Enter' to retry or 'Ctrl + C' to exit")
        input()

def is_gamesjson_valid():
    # Does file exist
    if not os.path.exists(json_file):
        return False
    try:
        with open(json_file, 'r') as f:
            games = json.load(f)
    except json.JSONDecodeError:
    # File is completely empty
        return False
    # File is just '{}'
    if not games:
        return False
    return True

def write_new_path(games, entry_name_to_edit, json_file, system):
    if get_platform() != system:
        print(f'WARNING: Since you are currently not on {system} the program will not check to see if the entered {system} path is valid')
        system_path = input(f"\nEnter the new {system} save path for your game: ").strip()
    else:
        system_path = input(f"\nEnter the new {system} save path for your game: ").strip()
        while not os.path.exists(system_path):
            system_path = input(f"The entered {system} path is not valid. Please try again: ").strip()

    games[entry_name_to_edit][system] = system_path
    with open(json_file, 'w') as f:
        json.dump(games, f, indent=4)
    
    print('\nSave path successfully changed!')

def take_entry_input(keyword, print_paths=True):
    if not is_gamesjson_valid():
        print('You have no game entries\n')
        return

    with open(json_file, 'r') as f:
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
    return games, entry_name_to_modify, json_file

def upload_save():
    pass

def download_save():
    pass

def check_save_status():
    pass

def add_game_entry():
    system = get_platform()
    
    # Loading file if exists else create new
    if os.path.exists(json_file):
        try:
            with open (json_file, "r") as f:
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
    with open(json_file, 'w') as f:
        json.dump(games, f, indent=4)

    print(f"\n{game_name} has been added successfully!\n")


def remove_game_entry():
    games,entry_name_to_del,json_file = take_entry_input('delete', False)
    del games[entry_name_to_del]

    with open(json_file, 'w') as f:
        json.dump(games, f, indent=4)

    print(f'\n{entry_name_to_del} has been removed from your games\n')



def edit_game_entry():
    games, entry_name_to_edit, json_file = take_entry_input('edit')

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
                
                with open(json_file, 'w') as f:
                    json.dump(new_games, f, indent=4)
                print(f'\nEntry name successfully changed from {entry_name_to_edit} to {new_name}!\n')
            case "2":
                write_new_path(games, entry_name_to_edit, json_file, "windows")
            case "3":
                write_new_path(games, entry_name_to_edit, json_file, "linux")
            case "4":
                return
            case _:
                print("Invalid option. Please try again\n")


def list_games(print_paths=True):
    system = get_platform()
    if not is_gamesjson_valid():
        print('You have no game entries\n')
        return

    with open(json_file, 'r') as f:
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



json_file = "games.json"

# Checking OS
operating_sys = get_platform()
if operating_sys == "unsupported":
    print("This program has detected your OS type as Unsupported. Press 'Enter' if you wish to continue")
    input()

internet_check()

# Menu
while True:
    function_choice = input("Select your function or press 'Ctrl+C' to exit:\n1: Upload Save(s)\n2: Download Save(s)\n3: Check Save(s) Status\n4: Add game entry\n5: Remove game entry\n6: Edit game entry\n7: List games\n").strip()
    match function_choice:
        case "1":
            pass
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
            

