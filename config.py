import json
from types import SimpleNamespace
from rich import print
import copy

def load_cfg(config_file, default_config):
    from ui import get_supabase_info
    from file_utils import is_json_valid

    valid = is_json_valid(config_file)
    regenerate = False
    if valid:
        # Checking if any of the required values are missing
        with open(config_file, 'r') as f:
            loaded_config = json.load(f)
            try:
                url = loaded_config['supabase']['url']
                api_key = loaded_config['supabase']['api_key']
                games_file = loaded_config['games_file']
                skip_extensions = loaded_config['skip_extensions']
                games_bucket = loaded_config['supabase']['games_bucket']
                table_name = loaded_config['supabase']['table_name']
            except:
                regenerate = True

    # If config missing, empty or in invalid format
    if not valid or regenerate:
        url, api_key, games_file, skip_extensions, games_bucket, table_name = regenerate_cfg(config_file, default_config)
    else:
        # Otherwise load config
        with open(config_file, 'r') as f:
            # Checking if anything is empty
            changed = False
            if url == '':
                print(f'The url value in your {config_file} is empty')
                url = get_supabase_info(choice='url')
                loaded_config['supabase']['url'] = url
                changed = True
            if api_key == '':
                print(f'The api key value in your {config_file} is empty')
                api_key = get_supabase_info(choice='api key')
                loaded_config['supabase']['api_key'] = api_key      
                changed = True
            if games_file == '':
                loaded_config['games_file'] = default_config['games_file']
                changed = True
            if games_bucket == '':
                loaded_config['supabase']['games_bucket'] = default_config['supabase']['games_bucket']
                changed = True
            if table_name == '':
                loaded_config['supabase']['table_name'] = default_config['supabase']['table_name']
                changed = True
            if changed:
                with open(config_file, "w") as f:
                    json.dump(loaded_config, f, indent=4)
    return SimpleNamespace(
        config_file=config_file,
        url=url,
        api_key=api_key,
        games_bucket=games_bucket,
        table_name=table_name,
        games_file=games_file,
        skip_extensions=skip_extensions,
        required_columns={
            'game_name':'game_name',
            'hash':'hash',
            'last_modified':'last_modified',
            'updated_at':'updated_at'
        }
    )

def regenerate_cfg(config_file, default_config):
    from ui import get_supabase_info
    
    with open(config_file, "w") as f:
        print(f"[yellow]No valid {config_file} found. A new one will be created."\
              "\n(If this is your first time running the program, this is normal)[/]")
        url = get_supabase_info(choice='url')
        api_key = get_supabase_info(choice='api key')
        games_file = default_config['games_file']
        skip_extensions = default_config['skip_extensions']
        games_bucket = default_config['supabase']['games_bucket']
        table_name = default_config['supabase']['table_name']
        temp_config = copy.deepcopy(default_config)
        temp_config['supabase']['url'] = url
        temp_config['supabase']['api_key'] = api_key
        json.dump(temp_config, f, indent=4)
        print('\nConfig file successfully regenerated')
        return url, api_key, games_file, skip_extensions, games_bucket, table_name
    
def edit_supabase_info(config, choice=None, user_called=True):
    from ui import get_supabase_info, int_range_input

    while True:
        with open(config.config_file, 'r') as f:
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
                loaded_config['supabase']['url'] = get_supabase_info(choice='url')
                config.url = loaded_config['supabase']['url']
            case 'api key':
                loaded_config['supabase']['api_key'] = get_supabase_info(choice='api key')
                config.api_key = loaded_config['supabase']['api_key']
            case 'bucket name':
                loaded_config['supabase']['games_bucket'] = get_supabase_info(choice='bucket name')
                config.games_bucket = loaded_config['supabase']['games_bucket']
            case 'table name':
                loaded_config['supabase']['table_name'] = get_supabase_info(choice='table name')
                config.table_name = loaded_config['supabase']['table_name']
            case 'exit':
                return
        with open(config.config_file, 'w') as f:
            json.dump(loaded_config, f, indent=4)
        if not user_called:
            return
        print('[green]Data successfully updated[/]\n')