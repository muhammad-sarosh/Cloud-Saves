import os
import json
from rich import print
from rich.prompt import Prompt
import supabase

def add_game_entry():
    from common import get_platform
    from files import get_games_file
    from settings import GAMES_FILE

    games = get_games_file()

    # Getting game name and validating
    game_name = ''
    while game_name == '':
        game_name = Prompt.ask("Enter the name of your game").strip()
        if game_name == '':
            print("Game name cannot be empty. Please try again\n")

    if game_name in games:
        print(f"{game_name} already exists in your list\n")
        return

    primary_system = get_platform()
    secondary_system = "linux" if primary_system == "windows" else "windows"

    # Inputting save paths
    system_path = Prompt.ask(f"\nEnter the {primary_system} save path for your game").strip()
    while not os.path.exists(system_path):
        system_path = Prompt.ask(f"The entered {primary_system} path is not valid. Please try again").strip()
    
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

    choice = Prompt.ask("Do you want to add the process name for this game? "\
                             "This is needed if you want to use auto.py to auto sync save files (y/n)")
    while True:
        if choice == 'y':
            primary_process = Prompt.ask(f"Launch your game, open task manager/system monitor and enter the [underline]{primary_system}[/] process name for the game").strip()
            secondary_process = Prompt.ask(f"Launch your game, open task manager/system monitor and enter the [underline]{secondary_system}[/] process name for the game "\
                    "(or press 'Enter' to skip)").strip()
            break
        elif choice == 'n':
            break
        else:
            choice = Prompt.ask("Incorrect input. Please answer with 'y' or 'n'").strip().lower()

    # Adding entry to file        
    games[game_name] = {
        f"{primary_system}_path": system_path,
        f"{primary_system}_process": primary_process,
        f"{secondary_system}_path": secondary_path,
        f"{secondary_system}_process": secondary_process
    }

    # Writing changes to file
    with open(GAMES_FILE, 'w') as f:
        json.dump(games, f, indent=4)

    print(f"\n{game_name} has been added successfully")

def remove_game_entry(config, games=None, entry_name_to_del=None):
    from supabase_client import loop_supabase_validation, remove_supabase_files
    from settings import GAMES_FILE

    if loop_supabase_validation(config=config) == -1:
        return
    games, entry_name_to_del = take_entry_input(keyword='to delete', extra_info=False)

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

    with open(GAMES_FILE, 'w') as f:
        json.dump(games, f, indent=4)

    print(f'\n[green]{entry_name_to_del} has been removed from your games[/]')

def edit_entry_process(games, entry_name_to_edit, system):
    from settings import GAMES_FILE

    new_process = Prompt.ask(f"Launch your game, open task manager/system monitor and enter the [underline]{system}[/] process name for the game "\
        "(or press 'Enter' to make it empty)").strip()
    games[entry_name_to_edit][f'{system}_process'] = new_process

    with open(GAMES_FILE, 'w') as f:
        json.dump(games, f, indent=4)
    
    print(f'\n[green]{system.capitalize()} process name changed[/]')

def edit_game_entry(config):
    from ui import int_range_input

    games, entry_name_to_edit = take_entry_input(keyword='to edit')
    input_message = "\n1: Entry name\n2: Windows path\n3: Windows process name\n4: Linux path\n5: Linux process name\n6: Return to main menu\nSelect what to edit"
    
    while True:
        choice = int_range_input(input_message, 1, 6)
        print()
        match choice:
            case 1:
                edit_game_name(config=config, games=games, entry_name_to_edit=entry_name_to_edit)
            case 2:
                write_new_path(games=games, entry_name_to_edit=entry_name_to_edit, system="windows")
            case 3:
                edit_entry_process(games=games, entry_name_to_edit=entry_name_to_edit, system="windows")
            case 4:
                write_new_path(games=games, entry_name_to_edit=entry_name_to_edit, system="linux")
            case 5:
                edit_entry_process(games=games, entry_name_to_edit=entry_name_to_edit, system="linux")
            case 6:
                return
            
def edit_game_name(config, games, entry_name_to_edit):
    from supabase_client import loop_supabase_validation, remove_supabase_files, list_all_supabase_files
    from settings import GAMES_FILE

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

    # Moving Supabase files and deleting old ones
    # Also editing table data
    print(f'\n[blue]Editing Supabase data...[/]')
    client = supabase.create_client(config.url, config.api_key)
    files_to_move = list_all_supabase_files(config=config, client=client, folder=f"{entry_name_to_edit}/")
    if files_to_move == -1:
        return
    # Cloud save files found
    if files_to_move:
        for file_path in files_to_move:
            try:
                file_data = client.storage.from_(config.games_bucket).download(file_path)
                new_path = file_path.replace(f"{entry_name_to_edit}/", f"{new_name}/")
                client.storage.from_(config.games_bucket).upload(new_path, file_data)
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
    
        print('\n[blue]Editing local data...[/]')

    # Copying old items without changing order
    new_games = {}
    for key, value in games.items():
        if key == entry_name_to_edit:
            new_games[new_name] = value
        else:
            new_games[key] = value
    
    with open(GAMES_FILE, 'w') as f:
        json.dump(new_games, f, indent=4)

    print(f'\n[green]Entry name successfully changed from {entry_name_to_edit} to {new_name}[/]')

# To update game entry paths
def write_new_path(games, entry_name_to_edit, system):
    from common import get_platform
    from settings import GAMES_FILE

    if get_platform() != system:
        print(f'WARNING: Since you are currently not on {system} the program will not check to see if the entered {system} path is valid')
        system_path = Prompt.ask(f"\nEnter the new {system} save path for your game").strip()
    else:
        system_path = Prompt.ask(f"\nEnter the new {system} save path for your game").strip()
        while not os.path.exists(system_path):
            system_path = Prompt.ask(f"The entered {system} path is not valid. Please try again").strip()

    games[entry_name_to_edit][f"{system}_path"] = system_path
    with open(GAMES_FILE, 'w') as f:
        json.dump(games, f, indent=4)
    
    print('\nSave path successfully changed')

# To input game entry. Returns None if there are no entries
def take_entry_input(keyword, extra_info=True):
    from files import is_json_valid
    from ui import int_range_input
    from settings import GAMES_FILE

    if not is_json_valid(GAMES_FILE):
        print('You have no game entries')
        return

    with open(GAMES_FILE, 'r') as f:
        games = json.load(f)

    # Taking input
    list_games(extra_info=extra_info)
    input_message = f'Enter the entry number {keyword}'
    entry_num_to_modify = int_range_input(input_message, 1, len(games))

    # Converting name to index number
    games_keys = list(games)
    entry_name_to_modify = games_keys[entry_num_to_modify - 1]
    return games, entry_name_to_modify

def get_key_str(key):
    if key == 'windows_process':
        return 'Windows Process'
    elif key == 'linux_process':
        return 'Linux Process'
    elif key == 'windows_path':
        return 'Windows Path'
    elif key == 'linux_path':
        return 'Linux Path'
    elif key == 'playtime':
        return 'Playtime'
    else:
        return key.capitalize()

def get_val_str(key, val):
    return val if key != 'playtime' else val + ' hours'

# print_paths determines whether the games save paths are printed along with the names
def list_games(extra_info=True):
    from files import is_json_valid
    from settings import GAMES_FILE

    if not is_json_valid(GAMES_FILE):
        print('You have no game entries\n')
        return

    with open(GAMES_FILE, 'r') as f:
        games = json.load(f)
    
    for count, (game, data) in enumerate(games.items(), 1):
        print(f"[bold]{count}: {game}[/]")
        if extra_info:
            for key, val in data.items():
                val = str(val)
                if val.strip():
                    print(f"[underline]{get_key_str(key=key)}:[/] [purple]{get_val_str(key=key, val=val)}[/]")
            print()
            
