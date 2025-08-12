import os

# Do not change DEFAULT_CONFIG unless you know what you are doing
DEFAULT_CONFIG = {
        "supabase": {
            "url": "",
            "api_key": "",
            "games_bucket":"game-saves",
            "table_name":"saves-data"
        }
}
CONFIG_FILE = 'config.json'
GAMES_FILE = 'games.json'

SKIP_EXTENSIONS = ['.tmp'] # Files with these extensions will be skipped during uploads e.g ['.tmp', '.log']
APP_NAME = 'Cloud Saves' # App name that shows up in notifications
ICON_PATH = os.path.join(os.path.dirname(__file__), "Cloud_Saves.png") # Icon that shows up in notifications
POLL_INTERVAL = 2 # How many seconds between each check of running processes if auto.py running
MAX_DOWNLOAD_THREADS = 4 # Higher = faster downloads but higher chance for failiure
MAX_UPLOAD_THREADS = 1 # Higher max_threads = faster uploads but higher chance for failiure