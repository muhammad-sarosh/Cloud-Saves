from datetime import datetime
from rich import print
import rich
import json
import supabase
import os
from pathlib import Path

def check_save_status(config, func_choice=None, game_choice=None, user_called=True):
    from file_utils import is_json_valid
    from supabase_client import loop_supabase_validation
    from ui import int_range_input
    from game_entry import take_entry_input
    from constants import GAMES_FILE

    if not is_json_valid(GAMES_FILE):
        print('You have no game entries')
        return
    with open(GAMES_FILE, 'r') as f:
        games = json.load(f)

    if user_called:
        input_message = '1: All games\n2: Specific game\n3: Return to main menu\nSelect what you want to check the status of'
        choice_num = int_range_input(input_message, 1, 3)
        choice_map = {
            1: 'all',
            2: 'specific',
            3: 'return'
        }
        func_choice = choice_map[choice_num]

    if func_choice != 'return':
        if loop_supabase_validation(config=config) == -1:
            return
        client = supabase.create_client(config.url, config.api_key)
        
    match func_choice:
        case 'all':
            data = [get_status(config=config, client=client, games=games, game_choice=game) for game in games]
            if not user_called:
                return data
            for count, game in enumerate(data, 1):
                print_status(game, count)
        case 'specific':
            if user_called:
                _, game_choice = take_entry_input(keyword='to check the save status of', print_paths=False)
            data = get_status(config=config, client=client, games=games, game_choice=game_choice)
            if not user_called:
                return data
            print()
            print_status(data)
        case 'return':
            return
        
def get_status(config, client, games, game_choice):
    from file_utils import hash_save_folder, get_last_modified
    from common import get_platform

    platform = get_platform()
    folder = Path(games[game_choice][platform])
    if not os.path.exists(folder):
        return {
            'game': game_choice,
            'error': f'[yellow]The save directory provided for {game_choice} game is invalid[/]'
        }
        
    response = (
        client.table(config.table_name)
        .select('*')
        .eq(config.required_columns['game_name'], game_choice)
        .execute()
    )
    data = response.data[0] if response.data else None

    if not data:
        updated_at = None
        cloud_last_modified = None
        cloud_hash = None
    else:
        updated_at = datetime.fromisoformat(data[config.required_columns['updated_at']]) if data[config.required_columns['updated_at']] else None
        cloud_last_modified = datetime.fromisoformat(data[config.required_columns['last_modified']]) if data[config.required_columns['last_modified']] else None
        cloud_hash = data[config.required_columns['hash']] if data[config.required_columns['hash']] else None

    lm = get_last_modified(folder=Path(games[game_choice][platform]))
    local_last_modified = datetime.fromisoformat(lm) if lm else None
    local_hash = hash_save_folder(path=Path(games[game_choice][platform]))

    if cloud_last_modified is None and local_last_modified is None:
        latest = None
    elif cloud_hash != None and cloud_hash == local_hash:
        latest = 'synced'
    elif cloud_last_modified == None:
        latest = 'local'
    elif local_last_modified is None:
        latest = 'cloud'
    elif cloud_last_modified > local_last_modified:
        latest = 'cloud'
    else:
        latest = 'local'

    return {
        'game': game_choice,
        'latest': latest,
        'updated_at': updated_at,
        'cloud_last_modified': cloud_last_modified,
        'local_last_modified': local_last_modified,
        'error': None
    }
    
def print_status(data, count=1):
    if data['error']:
        print(f"[bold][underline]{count}: {data['game']}[/][/]\n{data['error']}\n")
        return
    for key, val in data.items():
        if val == None:
            data[key] = 'Unavailable'
        elif key == 'latest':
            if val == 'local':
                status_str = 'Local save is more recent'
            elif val == 'cloud':
                status_str = 'Cloud save is more recent'
            elif val == 'synced':
                status_str = 'Local and Cloud saves are synced'

    # Format: August 06 2025 at 6:35 PM
    if data['cloud_last_modified'] != 'Unavailable':
        data['cloud_last_modified'] = data['cloud_last_modified'].strftime("%B %d %Y at %I:%M %p")
    
    if data['updated_at'] != 'Unavailable':
        data['updated_at'] = data['updated_at'].strftime("%B %d %Y at %I:%M %p")
    
    data['local_last_modified'] = data['local_last_modified'].strftime("%B %d %Y at %I:%M %p")

    # Rich's default print wrapper doesnt allow the argument highlight so a console needs to be created
    console = rich.get_console()

    console.print(
        f"[bold][underline]{count}: {data['game']}[/][/]\n"\
        f"[bold]Status:[/] {status_str}\n"\
        f"[bold]Updated at:[/] {data['updated_at']}\n"\
        f"[bold]Cloud last modified:[/] {data['cloud_last_modified']}\n"\
        f"[bold]Local last modified:[/] {data['local_last_modified']}\n", highlight=False)