from rich.traceback import install

from config import load_cfg
from game_entry import add_game_entry, remove_game_entry, edit_game_entry, list_games
from supabase_client import upload_save, download_save, sync_save
from status import check_save_status
from config import edit_supabase_info
from common import get_platform
from ui import int_range_input
from file_utils import clear_trash

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
    function_input_message = "\n[bold]=== Cloud Saves ===[/]\n1: Sync Save\n2: Upload Save\n3: Download Save\n" \
    "4: Check Save Status\n5: Add game entry\n6: Remove game entry\n7: Edit game entry\n8: List games\n" \
    "9: Clear Trash\n10: Edit Supabase info\nSelect your function or press 'Ctrl+C' to exit"
    while True:
        function_choice = int_range_input(function_input_message, 1, 10)
        print()
        match function_choice:
            case 1:
                sync_save(config=config)
            case 2:
                upload_save(config=config)
            case 3:
                download_save(config=config)
            case 4:
                check_save_status(config=config)
            case 5:
                add_game_entry()
            case 6:
                remove_game_entry(config=config)
            case 7:
                edit_game_entry(config=config)
            case 8:
                list_games()
            case 9:
                clear_trash()
            case 10:
                edit_supabase_info(config=config)

if __name__ == "__main__":
    main()