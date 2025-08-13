import json
from types import SimpleNamespace
from rich import print
import copy
from common import log, is_auto_mode

def load_cfg():
    from ui import get_supabase_info
    from file_utils import is_json_valid
    from constants import DEFAULT_CONFIG, CONFIG_FILE
    
    valid = is_json_valid(CONFIG_FILE)
    regenerate = False
    if valid:
        # Checking if any of the required values are missing
        with open(CONFIG_FILE, 'r') as f:
            loaded_config = json.load(f)
            try:
                url = loaded_config['url']
                api_key = loaded_config['api_key']
                games_bucket = loaded_config['games_bucket']
                table_name = loaded_config['table_name']
            except:
                regenerate = True

    # If config missing, empty or in invalid format
    if not valid or regenerate:
        url, api_key, games_bucket, table_name = regenerate_cfg()
    else:
        # Otherwise load config
        with open(CONFIG_FILE, 'r') as f:
            # Checking if anything is empty
            changed = False
            if url == '':
                log(f'Url in {CONFIG_FILE} is empty', 'error')       
                if not is_auto_mode():
                    print(f'The url value in your {CONFIG_FILE} is empty')
                    url = get_supabase_info(choice='url')
                    loaded_config['url'] = url
                    changed = True
            if api_key == '':
                log(f'Api key in {CONFIG_FILE} is empty', 'error')
                if not is_auto_mode():
                    print(f'The api key value in your {CONFIG_FILE} is empty')
                    api_key = get_supabase_info(choice='api key')
                    loaded_config['api_key'] = api_key      
                    changed = True
            if games_bucket == '':
                log(f'Games bucket name in {CONFIG_FILE} is empty, setting defaults')
                loaded_config['games_bucket'] = DEFAULT_CONFIG['games_bucket']
                changed = True
            if table_name == '':
                log(f'Table name in {CONFIG_FILE} is empty, setting defaults')
                loaded_config['table_name'] = DEFAULT_CONFIG['table_name']
                changed = True
            if changed:
                with open(CONFIG_FILE, "w") as f:
                    json.dump(loaded_config, f, indent=4)
    return SimpleNamespace(
        url=url,
        api_key=api_key,
        games_bucket=games_bucket,
        table_name=table_name,
        required_columns={
            'game_name':'game_name',
            'hash':'hash',
            'last_modified':'last_modified',
            'updated_at':'updated_at'
        }
    )

def regenerate_cfg():
    from ui import get_supabase_info
    from constants import DEFAULT_CONFIG, CONFIG_FILE
    
    log('Config file regenerating', 'warning')

    with open(CONFIG_FILE, "w") as f:
        print(f"[yellow]No valid {CONFIG_FILE} found. A new one will be created."\
              "\n(If this is your first time running the program, this is normal)[/]")
        url = get_supabase_info(choice='url')
        api_key = get_supabase_info(choice='api key')
        games_bucket = DEFAULT_CONFIG['games_bucket']
        table_name = DEFAULT_CONFIG['table_name']
        temp_config = copy.deepcopy(DEFAULT_CONFIG)
        temp_config['url'] = url
        temp_config['api_key'] = api_key
        json.dump(temp_config, f, indent=4)
        print('\nConfig file successfully regenerated')
        return url, api_key, games_bucket, table_name
    
def edit_supabase_info(config, choice=None, user_called=True):
    from ui import get_supabase_info, int_range_input
    from constants import CONFIG_FILE

    while True:
        with open(CONFIG_FILE, 'r') as f:
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
                loaded_config['url'] = get_supabase_info(choice='url')
                config.url = loaded_config['url']
            case 'api key':
                loaded_config['api_key'] = get_supabase_info(choice='api key')
                config.api_key = loaded_config['api_key']
            case 'bucket name':
                loaded_config['games_bucket'] = get_supabase_info(choice='bucket name')
                config.games_bucket = loaded_config['games_bucket']
            case 'table name':
                loaded_config['table_name'] = get_supabase_info(choice='table name')
                config.table_name = loaded_config['table_name']
            case 'exit':
                return
        with open(CONFIG_FILE, 'w') as f:
            json.dump(loaded_config, f, indent=4)
        if not user_called:
            return
        print('[green]Data successfully updated[/]\n')