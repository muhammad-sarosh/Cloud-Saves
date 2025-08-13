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
        from constants import GAMES_FILE
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
    from file_utils import get_games_file
    from constants import SKIP_GAMES

    platform = get_platform()
    if platform == 'unsupported':
        log("Unsupported platform. Aborting", 'error')
        return

    games = get_games_file()
    target_patterns = {}
    for game, data in games.items():
        if game not in SKIP_GAMES:
            process = data.get(f'{platform}_process', None)
            if process:
                target_patterns[game] = process
    return target_patterns

def snapshot_matches(target_patterns):
    matches = {}
    for proc in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
        match_found, game = is_match(target_patterns=target_patterns, proc=proc)
        if match_found:
            pid = proc.info["pid"]
            matches[pid] = game
    return matches

async def on_process_start(state, pid, current):
    from config import load_cfg
    from file_utils import get_games_file
    from status import get_status
    from common import internet_check

    game = current[pid]

    send_notification(title=game, message='Cloud saves is watching')
    log(f'Watching {game}')

    config = load_cfg()
    games = get_games_file()
    
    internet_check()

    try:
        client = supabase.create_client(config.url, config.api_key)
    except Exception as e:
        send_notification(title='Error', message='Failed to create supabase client. Check your supabase url and api key')
        log(f'Failed to create supaabse client: {e}', 'error')
        return

    
    data = await asyncio.to_thread(get_status, config=config, client=client, games=games, game_choice=game)
    if data['error']:
        send_notification(title=game, message=data['error'])
        log(f'Error when checking sync status for {game}: {data['error']}', 'error')
        return
    
    latest = data['latest']

    if latest != 'synced':
        if latest == 'cloud':
            send_notification(title=game, message='Cloud save is ahead. Please close the game for the save syncing to begin')
            log('Cloud save is ahead, waiting for game to close')
        elif latest == 'local':
            log('Local save is ahead, waiting for game to close')
        else:
            send_notification(title='Error', message=f'Unable to determine sync status for {game}')
            log(f'Unable to determine sync status for {game}', 'error')
            return
        state[pid] = {'game': current[pid], 'latest': latest}
    else:
        log(f'{game} save is already in sync')

async def on_process_exit(info):
    from config import load_cfg
    from supabase_client import upload_save, download_save
    from file_utils import get_games_file

    # info -> {game: game, latest: latest}
    await asyncio.sleep(2)

    config = load_cfg()
    games = get_games_file()
    game = info['game']

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

async def watch_loop():
    from constants import POLL_INTERVAL, LOG_FILE_NAME, MAX_LOG_BYTES, LOG_BACKUP_COUNT
    
    # Logger setup
    handler = RotatingFileHandler(
        filename=LOG_FILE_NAME,
        maxBytes=MAX_LOG_BYTES,
        backupCount=LOG_BACKUP_COUNT
    )

    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    handler.setFormatter(formatter)

    # Configuring root logger so these settings are global
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    # Setting env var for logging
    os.environ['AUTO_MODE'] = "1"

    target_patterns = get_target_patterns()
    log(f"Watching for: {list(target_patterns.values())}")

    seen = {}  # {pid: game}
    state = {} # {pid: {game: game, latest: latest}}
    start_tasks = {} # {pid: asyncio task}

    # Watchdog setup
    reload_flag = {'reload': False}
    def reload_callback():
        reload_flag['reload'] = True

    observer = Observer()
    handler = GamesFileHandler(reload_callback)
    observer.schedule(handler, path=os.getcwd(), recursive=False)
    observer.start()

    try:
        while True:
            # Reload game entries
            if reload_flag['reload']:
                target_patterns = get_target_patterns()
                log(f"Reloaded target patterns: {list(target_patterns.values())}")
                reload_flag['reload'] = False
                
            if target_patterns:
                current = snapshot_matches(target_patterns=target_patterns)

                started_pids = current.keys() - seen.keys()
                ended_pids   = seen.keys() - current.keys()

                for pid in started_pids:
                    # Checking if on_process_start for this task is done if it was already running
                    task = start_tasks.pop(pid, None)
                    if task is not None and not task.done():
                        try:
                            await task
                        except:
                            continue
                    # If we're not already waiting for the game to close, then add it to the list
                    # of games that we wanna wait for
                    if pid not in state.keys():
                        start_tasks[pid] = asyncio.create_task(on_process_start(state=state, pid=pid, current=current))

                for pid in ended_pids:
                    # Check if on_process_start for that task is done
                    task = start_tasks.pop(pid, None)
                    if task is not None and not task.done():
                        try:
                            await task
                        except:
                            continue
                    
                    # state data for that task will now be availible if conditions were met
                    if pid in state.keys():
                        info = state[pid]
                        state.pop(pid, None)
                        asyncio.create_task(on_process_exit(info=info))

                seen = current
                await asyncio.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
    

def main():
    asyncio.run(watch_loop())


if __name__ == "__main__":
    main()