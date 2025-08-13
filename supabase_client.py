import os
from datetime import datetime, timezone
from pathlib import Path
from rich import print
from rich.prompt import Prompt
from rich.progress import Progress
from concurrent.futures import ThreadPoolExecutor, as_completed
import supabase
import time

from file_utils import hash_save_folder, get_last_modified, move_files
from config import edit_supabase_info
from common import get_platform, internet_check, log, is_auto_mode, send_notification
from game_entry import take_entry_input
from constants import CONFIG_FILE

# Returns True if everthing is valid. Returns False and updates info if anything was invalid
# Returns -1 if unexpected error
def supabase_validation(config):
    internet_check()
    try:
        # Checks URL and API key
        client = supabase.create_client(config.url, config.api_key)

        # Checking if the table exists
        client.table(config.table_name).select("*").limit(1).execute()

        # Send query to get required columns and their data types
        required_columns_list = list(config.required_columns.values())
        result = client.table("table_column_info")\
            .select("column_name", "data_type")\
            .eq("table_name", config.table_name)\
            .in_("column_name", required_columns_list)\
            .execute()

        expected_types = {
            config.required_columns['game_name']: 'text',
            config.required_columns['hash']: 'text',
            config.required_columns['last_modified']: 'timestamp with time zone',
            config.required_columns['updated_at']: 'timestamp with time zone'
        }
        
        # Checks missing columns and mismatching data types
        actual_types = {row['column_name']: row['data_type'] for row in result.data}
        found_columns = set(actual_types)
        missing_columns = set(required_columns_list) - found_columns

        if missing_columns:
            print(f"[yellow]The column(s) [underline]{str(missing_columns)}[/] are missing from your supabase table[/]")
            send_notification(title='Error', message=f"The column(s) {str(missing_columns)} are missing from your supabase table")
            log(f"The column(s) {str(missing_columns)} are missing from your supabase table", 'error')
                
            return -1
        
        for column in required_columns_list:
            if actual_types[column] != expected_types[column]:
                print(f"[yellow]Column '{column}' has wrong type: expected '{expected_types[column]}', got '{actual_types[column]}'[/]")
                send_notification(title='Error', message=f"Column(s) in your supabase table have the wrong type. Check the log file for more details")
                log(f"Column '{column}' has wrong type: expected '{expected_types[column]}', got '{actual_types[column]}'", 'error')
                return -1

        # Checks Bucket
        all_buckets = client.storage.list_buckets()
        bucket_exists = any(b.name == config.games_bucket for b in all_buckets)
        if not bucket_exists:
            # Bucket doesnt exist, attemp to create
            try:
                log('Supabase bucket not found, attempting to create', 'warning')
                client.storage.create_bucket(config.games_bucket)
            except Exception as e:
                log(f'Could not create supabase bucket: {e}', 'error')
                send_notification(title='Error', message='Could not create supabase bucket, check logs for details')
                print(f'[yellow]Supabase storage bucket {config.games_bucket} does not exist. [/]'\
                        f'[yellow]The program encountered this error when trying to create it: {e}[/]')
                return -1
        return True
    except Exception as e:
        e_str = getattr(e, "message", None)
        e_str = e_str.lower() if e_str else str(e).lower()
        details = str(getattr(e, "details", "").lower())

        if e_str == 'invalid url':
            send_notification(title='Error', message=f'The supabase data api url in {CONFIG_FILE} is incorrect')
            log(f'The supabase data api url in {CONFIG_FILE} is incorrect', 'error')
            if not is_auto_mode():
                print(f'[yellow]The Supabase data api url in your {CONFIG_FILE} is incorrect. You will be repeatedly prompted to update it until you enter it correctly[/]')
                edit_supabase_info(choice='url', config=config, user_called=False)
                return False
            else:
                return -1
        elif e_str == 'invalid compact jws' or e_str == 'jws protected header is invalid' or 'invalid api key' in details:
            send_notification(title='Error', message=f'The supabase service role api key in {CONFIG_FILE} is incorrect')
            log(f'The supabase service role api key in {CONFIG_FILE} is incorrect', 'error')
            if not is_auto_mode():
                print(f'[yellow]The Supabase service_role api key in your {CONFIG_FILE} is incorrect. You will be repeatedly prompted to update it until you enter it correctly[/]')
                edit_supabase_info(choice='api key', config=config, user_called=False)
                return False
            else: 
                return -1
        elif 'relation' in e_str and 'does not exist' in e_str:
            send_notification(title='Error', message=f'The supabase table name in {CONFIG_FILE} is incorrect')
            log(f'The supabase table name in {CONFIG_FILE} is incorrect', 'error')
            if not is_auto_mode():
                print(f'[yellow]The Supabase table name in your {CONFIG_FILE} is incorrect as a table with this name does not exist. You will be repeatedly prompted to update it until you enter it correctly[/]') 
                edit_supabase_info(choice='table name', config=config, user_called=False)
                return False
            else:
                return -1
        else:
            send_notification(title='Error', message='An unexpected error occured while trying to validate supabase. Check logs for details')
            log(f'Unexpected error when trying to validate supabase: {e}')
            print(f"[red]ERROR:[/] {e}")
            return -1
        
def loop_supabase_validation(config):
    print('\n[blue]Connecting to Supabase...[/]\n')
    # Loop until all supabase data is validated and updated
    while True:
        valid = supabase_validation(config)
        # Unexpected error
        if valid == -1:
            return valid
        # Data is completely valid
        if valid:
            return valid   

def upload_file(config, client, entry, file_path, local_path, retries=3):
    # Makes full path into relative path 
    relative_path = file_path.relative_to(local_path)
    upload_path = f"{entry}/{relative_path}".replace('\\', '/')

    # Checking if file already exists in Supabase, if yes then use
    # update() otherwise use .upload()
    attempt = 0
    while attempt < retries:
        try:
            # Works if not first time uploading
            with open(file_path, 'rb') as f:
                client.storage.from_(config.games_bucket).update(upload_path, f)
                return file_path, None
        except Exception as e:
            winerr = getattr(e, 'winerror', None)
            # Means this is the first time uploading
            if "Not found" in str(e) or "404" in str(e):
                try:
                    with open(file_path, 'rb') as f2:
                        client.storage.from_(config.games_bucket).upload(upload_path, f2)
                        return file_path, None
                except Exception as e2:
                    # Need same error checking  in both cases
                    winerr2 = getattr(e2, 'winerror', None)
                    if winerr2 == 10035:
                        time.sleep(0.2)
                        attempt += 1
                        continue
                    return file_path, str(e2)
            # Need same error checking  in both cases
            elif winerr == 10035:
                time.sleep(0.2)
                attempt += 1
                continue
            else:
                return  file_path, str(e)
    return file_path, "WinError 10035: Failed after retries"

def upload_save(config, games=None, entry=None, user_called=True):
    from constants import SKIP_EXTENSIONS

    if user_called:
        response = take_entry_input(keyword='to upload', print_paths=False)
        # True if there are no game entries
        if response == None:
            return
        games, entry = response

    if loop_supabase_validation(config=config) == -1:
        return
    
    client = supabase.create_client(config.url, config.api_key)

    operating_sys = get_platform()

    local_path = Path(games[entry][operating_sys])
    # Need to check for empty "" path entry too as that still forms a valid path to the current directory
    if not games[entry][operating_sys] or not os.path.exists(local_path):
        log(f'The save directory for {entry} is invalid: {games[entry][operating_sys]}', 'error')
        send_notification(title='Error', message=f'The save direcotry for {entry} is invalid. Check logs for details')
        print('\n[yellow]The save directory provided for this game is invalid[/]')
        return
    files_to_upload = [f for f in local_path.rglob('*') if f.is_file() and f.suffix.lower() not in SKIP_EXTENSIONS]
    if not files_to_upload:
        log(f'The save directory for {entry} contains no files', 'warning')
        print('\n[yellow]The save directory for this game contains no files[/]')
        return
    
    # Initialising progress bar
    with Progress() as progress:
        from constants import MAX_UPLOAD_THREADS
        task = progress.add_task("[cyan]Uploading files...", total=len(files_to_upload))
        # How many threads to create, tune as needed
        # Higher max_threads = faster uploads but higher chance for failiure
        max_workers = min(MAX_UPLOAD_THREADS, len(files_to_upload)) 
        
        # Submit all upload to the thread pool
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(upload_file, config, client, entry, file_path, local_path)
                for file_path in files_to_upload
            ]
        
            # As each file finishes, handle progress and errors
            for future in as_completed(futures):
                filename, error = future.result()
                if error:
                    print(f"[red]Error uploading {filename}: {error}[/]")
                progress.advance(task)

    folder_hash = hash_save_folder(path=local_path)
    last_modified = get_last_modified(folder=Path(local_path))
    row = {
        config.required_columns['game_name']: entry,
        config.required_columns['hash']: folder_hash,
        config.required_columns['last_modified']: last_modified,
        config.required_columns['updated_at']: datetime.now(timezone.utc).isoformat()
    }
    try:
        client.table(config.table_name).upsert(row).execute()
    except Exception as e:
        send_notification(title='Error', message=f'Failed to update table data for {entry}. Check logs for details')
        log(f'Failed to update table data for {entry}: {e}', 'error')
        print(f"[red]Failed to update table data for {entry}: {e}[/]")

    print('\n[green]All files successfully uploaded[/]')
    return True # So auto.py can detect success

def download_file(config, client, entry, file_path, source_path, retries=3):
    relative_path = Path(file_path.replace(f"{entry}/", "", 1))
    destination_path = source_path / relative_path

    attempt = 0
    while attempt < retries:
        try:
            downloaded_file = client.storage.from_(config.games_bucket).download(file_path)
            
            # Making sure destination folders exist
            destination_path.parent.mkdir(parents=True, exist_ok=True)

            with open(destination_path, 'wb') as f:
                f.write(downloaded_file)
            return relative_path.name, None
        except OSError as e:
            if getattr(e, 'winerror', None) == 10035:
                # Wait and retry
                time.sleep(0.2)
                attempt += 1
                continue
            return relative_path.name, str(e)
        except Exception as e:
            return relative_path.name, str(e)
    return relative_path.name, 'WinError 10035: Failed after retries'

def download_save(config, response=None, user_called=True):
    internet_check()
    
    operating_sys = get_platform()
    if user_called:
        response = take_entry_input(keyword="which's save you want to download", print_paths=False)
    # True if there are no game entries
    if response == None:
        return
    games, entry = response

    source_path = Path(games[entry][operating_sys])
    if not games[entry][operating_sys] or not os.path.exists(source_path):
        log(f'The save directory for {entry} is invalid: {games[entry][operating_sys]}', 'error')
        send_notification(title='Error', message=f'The save direcotry for {entry} is invalid. Check logs for details')
        print('[yellow]The save directory provided for this game is invalid[/]')
        return

    if loop_supabase_validation(config=config) == -1:
        return
    
    client = supabase.create_client(config.url, config.api_key)

    response = client.table(config.table_name).select("*").eq(config.required_columns['game_name'], entry).execute()
    row = response.data[0] if response.data else None
    if row is None:
        send_notification(title='Error', message=f'No table data found for {entry}')
        log(f'No table data found for {entry}', 'error')
        print(f'[yellow]No table data exists for the game {entry}[/]')
        return
    
    file_list = client.storage.from_(config.games_bucket).list(f"{entry}/")
    if not file_list:
        send_notification(title='Error', message=f'No cloud data found for {entry}')
        log(f'No cloud data found for {entry}', 'error')
        print(f'[yellow]No cloud data exists for the game {entry}[/]')
        return
    
    source_hash = hash_save_folder(path=source_path)
    cloud_hash = row[config.required_columns['hash']]

    if source_hash == cloud_hash:
        choice = Prompt.ask(f"[yellow]Your local and cloud save files are currently the same. Do you still want to continue? (y/n)[/]").strip().lower()
        print()
        while True:
            if choice == 'y':
                break
            elif choice == 'n':
                return
            else:
                choice = Prompt.ask("Incorrect input. Please answer with 'y' or 'n'").strip().lower()

    trash_folder_path = Path(__file__).parent / "Trash"
    game_folder_path = trash_folder_path / entry
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = game_folder_path / timestamp

    print('[blue]Gathering data from Supabase...[/]')

    files_to_download = list_all_supabase_files(config=config, client=client, folder=f"{entry}/")
    if files_to_download == -1:
        return
    
    move_files(source_path=source_path, backup_path=backup_path)

    log(f'Downloading files for {entry}')
    with Progress() as progress:
        from constants import MAX_DOWNLOAD_THREADS
        task = progress.add_task("[cyan]Downloading files...", total=len(files_to_download))
        max_workers = min(MAX_DOWNLOAD_THREADS, len(files_to_download)) 

        # Submit all downloads to the thread pool
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(download_file, config, client, entry, file_path, source_path)
                for file_path in files_to_download
            ]
        
            # As each file finishes, handle progress and errors
            for future in as_completed(futures):
                filename, error = future.result()
                if error:
                    extra_message = "Try reducing MAX_DOWNLOAD_THREADS" if "blocking" in error.lower() else ""
                    send_notification(title='Error', message=f'Error downloading {filename} for {entry}. Check logs for details')
                    log(f'Error downloading {filename} for {entry}: {error}. {extra_message}', 'error')
                    print(f"[yellow]Error downloading {filename}: {error}. {extra_message}[/]")
                progress.advance(task)

    print('\n[green]All files successfully downloaded[/]')
    return True # So auto.py can detect success

def remove_supabase_files(config, client, entry_name_to_del):
    files_to_delete = list_all_supabase_files(config=config, client=client, folder=f"{entry_name_to_del}/")
    if files_to_delete == -1:
        return
    if files_to_delete:
        internet_check()
        try:
            client.storage.from_(config.games_bucket).remove(files_to_delete)
        except Exception as e:
            print(f"[red]ERROR: {e}[/]")

# Returns -1 if error
def list_all_supabase_files(config, client, folder):
    try:
        internet_check()
        full_file_paths = []

        items = client.storage.from_(config.games_bucket).list(folder)

        for item in items:
            name = item["name"]
            full_path = f"{folder}{name}"

            # Check if item is a folder
            if not item["metadata"]:
                # Recursive call into subfolder
                subfiles = list_all_supabase_files(config=config, client=client, folder=f"{full_path}/")
                full_file_paths.extend(subfiles)
            else:
                full_file_paths.append(full_path)
        return full_file_paths
    except Exception as e:
        send_notification(title='Error', message='An error occured while retrieving data from supabase. Check logs for details')
        log(f'Error while retrieving files from supabase: {e}', 'error')
        print(f"[red]ERROR: {e}[/]")
        return -1