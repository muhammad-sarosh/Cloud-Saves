from rich.traceback import install

from config import load_cfg
from game_entry import add_game_entry, remove_game_entry, edit_game_entry, list_games
from supabase_client import upload_save, download_save
from status import check_save_status
from config import edit_supabase_info
from common import get_platform
from ui import int_range_input

def main():
    # Rich traceback install
    install()

    config = load_cfg()

    # Checking OS
    operating_sys = get_platform()
    if operating_sys == "unsupported":
        print("This program has detected your OS type as Unsupported. Press 'Enter' if you wish to continue")
        input()

    # Menu
    function_input_message = "\n[bold]=== Cloud Saves ===[/]\n1: Upload Save\n2: Download Save\n" \
    "3: Check Save Status\n4: Add game entry\n5: Remove game entry\n6: Edit game entry\n7: List games\n" \
    "8: Edit Supabase info\nSelect your function or press 'Ctrl+C' to exit"
    while True:
        function_choice = int_range_input(function_input_message, 1, 8)
        print()
        match function_choice:
            case 1:
                upload_save(config=config)
            case 2:
                download_save(config=config)
            case 3:
                check_save_status(config=config)
            case 4:
                add_game_entry()
            case 5:
                remove_game_entry(config=config)
            case 6:
                edit_game_entry(config=config)
            case 7:
                list_games()
            case 8:
                edit_supabase_info(config=config)

if __name__ == "__main__":
    main()