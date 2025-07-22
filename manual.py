import platform
import socket
import json
import os

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

def upload_save():
    pass

def download_save():
    pass

def check_save_status():
    pass

def add_game_entry(system):
    json_file = "games.json"

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
    
    choice = input(f"\nDo you want to add the {secondary_system} save path as well? Please note that if you choose yes, the program will not check if the entered path is valid (y/n): ").strip().lower()
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
    pass

def edit_game_entry():
    pass

def list_games(system):
    json_file = "games.json"

    # Handling json file edge cases
    if not os.path.exists(json_file):
        print("You have no game entries")
        return
    
    try:
        with open(json_file, 'r') as f:
            games = json.load(f)
    except json.JSONDecodeError:
        print("You have no game entries")
        return
    
    if not games:
        print('YOu have no game entries')
        return
    
    count = 1
    for game, paths in games.items():
        print(f"\033[1m{count}: {game}\033[0m")
        for system, path in paths.items():
            if path.strip():
                print(f"\033[4m{system.capitalize()} Path:\033[0m {path}")
        print()

# Checking OS
system = get_platform()
if system == "unsupported":
    print("This program has detected your OS type as Unsupported. Press 'Enter' if you wish to continue")
    input()

internet_check()

# Menu
while True:
    function_choice = input("Select your function or press 'Ctrl+C' to exit:\n1: Upload Save(s)\n2: Download Save(s)\n3: Check Save(s) Status\n4: Add game entry\n5: Remove game entry\n6: Edit game entry\n7: List games\n")
    match function_choice:
        case "1":
            pass
        case "2":
            pass
        case "3":
            pass
        case "4":
            add_game_entry(system)
        case "5":
            pass
        case "6":
            pass
        case "7":
            list_games(system)
        case _:
            print("Invalid option. Please try again")

