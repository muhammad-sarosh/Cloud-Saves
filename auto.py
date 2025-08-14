import asyncio
import os
import psutil
import supabase
import logging
from logging.handlers import RotatingFileHandler
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from common import log, send_notification

class GamesFileHandler(FileSystemEventHandler):
    def __init__(self, reload_callback):
        self.reload_callback = reload_callback

    def on_modified(self, event):
        from settings import GAMES_FILE
        if event.src_path.endswith(GAMES_FILE):
            self.reload_callback()

def safe_lower(s):
    return (s or "").lower()

def is_match(target_patterns, proc):
    try:
        name = safe_lower(proc.info.get("name"))
        exe = proc.info.get("exe") or ""
        exe_base = safe_lower(os.path.basename(exe))
        exe_full = safe_lower(exe)
        cmdline = proc.info.get("cmdline") or []
        cmd_lower = [safe_lower(x) for x in cmdline]
        cmd_bases = [safe_lower(os.path.basename(x)) for x in cmdline]

        for game, patt in target_patterns.items():
            p = patt.lower()
            if not p:
                continue
            if p in name:
                return True, game
            if p in exe_base or p in exe_full:
                return True, game
            if any(p in arg for arg in cmd_lower):
                return True, game
            if any(p in base for base in cmd_bases):
                return True, game
        return False, None
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False, None

def get_target_patterns():
    from common import get_platform
    from files import get_games_file
    from settings import SKIP_GAMES

    platform = get_platform()
    if platform == 'unsupported':
        log("Unsupported platform. Aborting", 'error')
        return {}

    games = get_games_file()
    target_patterns = {}
    for game, data in games.items():
        if game not in SKIP_GAMES:
            process = data.get(f'{platform}_process', None)
            if process:
                target_patterns[game] = process
            else:
                log(f'No process name configured for {game} on {platform}', 'warning')
    
    log(f'Loaded {len(target_patterns)} target patterns for {platform} platform')
    return target_patterns

async def get_latest(game):
    from config import load_cfg
    from files import get_games_file
    from common import internet_check
    from status import get_status

    config = load_cfg()
    games = get_games_file()
    
    internet_check()

    try:
        client = supabase.create_client(config.url, config.api_key)
    except Exception as e:
        send_notification(title='Error', message='Failed to create supabase client. Check your supabase url and api key')
        log(f'Failed to create supabse client: {e}', 'error')
        return -1

    
    data = await asyncio.to_thread(get_status, config=config, client=client, games=games, game_choice=game)
    if data['error']:
        send_notification(title=game, message=data['error'])
        log(f'Error when checking sync status for {game}: {data['error']}', 'error')
        return -1
    
    return data['latest']

def snapshot_matches(target_patterns):
    matches = {}
    for proc in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
        match_found, game = is_match(target_patterns=target_patterns, proc=proc)
        if match_found:
            pid = proc.info["pid"]
            matches[pid] = game
    return matches

async def on_process_start(state, pid, current):
    game = current[pid]

    send_notification(title=game, message='Cloud saves is watching')
    log(f'Watching {game}')

    latest = await get_latest(game=game)
    if latest == -1:
        return

    if latest == 'cloud':
        send_notification(title=game, message='Cloud save is ahead. Please close the game for the save syncing to begin')
        log('Cloud save is ahead, waiting for game to close')
    elif latest == 'local':
        log('Local save is ahead, waiting for game to close')
    elif latest == 'synced':
        log(f'{game} save is already in sync')
    else:
        send_notification(title='Error', message=f'Unable to determine sync status for {game}')
        log(f'Unable to determine sync status for {game}', 'error')
        return
    
    state[pid] = {'game': current[pid], 'latest': latest}

async def on_process_exit(info):
    from config import load_cfg
    from supabase_client import upload_save, download_save
    from files import get_games_file

    # info -> {game: game, latest: latest}
    await asyncio.sleep(2)

    game = info['game']

    # If game was marked as synced when process started, get status again and check if the save updated
    if info['latest'] == 'synced':
        latest = await get_latest(game=game)
        if latest == -1:
            return
        # If game is still synced, return. Otherwise update the status
        if latest == 'synced':
            log(f'{game} save is already in sync')
            return
        else:
            info['latest'] = latest
    
    config = load_cfg()
    games = get_games_file()
    
    send_notification(title=game, message='Save syncing started')
    log(f'Save syncing for {game} started')

    if info['latest'] == 'cloud':
        log(f'Downloading data for {game}...')
        success = await asyncio.to_thread(download_save, config=config, games=games, entry=game, user_called=False)
    elif info['latest'] == 'local':
        log(f'Uploading data for {game}...')
        success = await asyncio.to_thread(upload_save, config=config, games=games, entry=game, user_called=False)

    if success:
        send_notification(title=game, message='Save Synced')
        log(f'Save for {game} synced')
    else:
        send_notification(title='Error', message=f'Failed to sync save for {game}')
        log(f'Failed to sync save for {game}', 'error')

async def watch_loop():
    from settings import POLL_INTERVAL, LOG_FILE_NAME, LOG_FOLDER, MAX_LOG_BYTES, LOG_BACKUP_COUNT, CLEAR_TRASH
    
    # Logger setup
    if LOG_FOLDER:
        os.makedirs(LOG_FOLDER, exist_ok=True)

    log_handler = RotatingFileHandler(
        filename=os.path.join(LOG_FOLDER, LOG_FILE_NAME),
        maxBytes=MAX_LOG_BYTES,
        backupCount=LOG_BACKUP_COUNT
    )

    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    log_handler.setFormatter(formatter)

    # Configuring root logger so these settings are global
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(log_handler)    # Setting env var for logging
    os.environ['AUTO_MODE'] = "1"
    
    log('Cloud Saves auto-sync starting up')
    log(f'Configuration: Poll interval {POLL_INTERVAL}s, Log rotation at {MAX_LOG_BYTES} bytes, {LOG_BACKUP_COUNT} backup files')
    
    # Clear trash if enabled
    if CLEAR_TRASH:
        from files import clear_trash
        clear_trash(user_called=False)
        log("Cleared excess trash backups")

    target_patterns = get_target_patterns()
    log(f"Watching for: {list(target_patterns.values())}")

    seen = {}  # {pid: game}
    state = {} # {pid: {game: game, latest: latest}}
    start_tasks = {} # {pid: asyncio task}
    syncing_games = set()  # Track games currently being synced

    # Watchdog setup
    reload_flag = {'reload': False}
    def reload_callback():
        reload_flag['reload'] = True

    observer = Observer()
    log_handler = GamesFileHandler(reload_callback)
    observer.schedule(log_handler, path=os.getcwd(), recursive=False)
    observer.start()

    try:
        while True:
            # Reload game entries
            if reload_flag['reload']:
                target_patterns = get_target_patterns()
                log(f"Reloaded target patterns: {list(target_patterns.values())}")
                reload_flag['reload'] = False
                
            if target_patterns:
                try:
                    current = snapshot_matches(target_patterns=target_patterns)
                except Exception as e:
                    log(f'Error during process monitoring: {e}', 'error')
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                started_pids = current.keys() - seen.keys()
                ended_pids   = seen.keys() - current.keys()

                for pid in started_pids:
                    log(f'Process started: PID {pid} ({current[pid]})')

                    # Checking if on_process_start for this task is done if it was already running
                    task = start_tasks.pop(pid, None)
                    if task is not None and not task.done():
                        try:
                            await task
                        except Exception as e:
                            log(f'Error waiting for previous start task (PID {pid}): {e}', 'error')
                            continue                    # If we're not already waiting for the game to close, then add it to the list
                    # of games that we wanna wait for
                    if pid not in state.keys():
                        start_tasks[pid] = asyncio.create_task(on_process_start(state=state, pid=pid, current=current))

                for pid in ended_pids:
                    game = seen[pid]
                    log(f'Process ended: PID {pid} ({game})')
                    # Check if on_process_start for that task is done
                    task = start_tasks.pop(pid, None)
                    if task is not None and not task.done():
                        try:
                            await task
                        except Exception as e:
                            log(f'Error waiting for start task to complete (PID {pid}): {e}', 'error')
                            continue
                    
                    # state data for that task will now be availible if conditions were met
                    if pid in state.keys():
                        # Skip if this game is already being synced
                        if game in syncing_games:
                            log(f'Sync already in progress for {game}, skipping PID {pid}')
                            state.pop(pid, None)
                            continue
                        
                        syncing_games.add(game)
                        info = state[pid]
                        state.pop(pid, None)
                        
                        # Create wrapper task that removes game from syncing_games when done
                        async def sync_wrapper(info, syncing_games):
                            try:
                                await on_process_exit(info=info)
                            finally:
                                syncing_games.discard(info['game'])
                        
                        asyncio.create_task(sync_wrapper(info=info, syncing_games=syncing_games))

                seen = current
                await asyncio.sleep(POLL_INTERVAL)
            else:
                # No target patterns found, wait longer before checking again
                await asyncio.sleep(POLL_INTERVAL * 2)
    except KeyboardInterrupt:
        log('Received keyboard interrupt, shutting down...')
        pass
    except Exception as e:
        log(f'Unexpected error in watch loop: {e}', 'error')
        raise
    finally:
        observer.stop()
        observer.join()
        log('Watch loop shut down complete')
    

def main():
    asyncio.run(watch_loop())


if __name__ == "__main__":
    main()