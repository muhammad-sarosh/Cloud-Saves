import asyncio
import os
import psutil
import supabase
import subprocess

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

def send_notification(title, message):
    from constants import APP_NAME, ICON_PATH
    from common import get_platform

    platform_name = get_platform()

    if platform_name == "linux":
        # Build notify-send command
        cmd = [
            "notify-send",
            title,
            message,
            "--app-name", APP_NAME
        ]
        if ICON_PATH:
            cmd.extend(["--icon", ICON_PATH])

        try:
            subprocess.run(cmd, check=True)
        except FileNotFoundError:
            print("[error] 'notify-send' not found. Install 'libnotify-bin'.")
        except Exception as e:
            print(f"[error] Failed to send Linux notification: {e}")

    elif platform_name == "windows":
        # Use PowerShell toast notification
        try:
            # Escape double quotes in message parts
            title_esc = title.replace('"', '\\"')
            message_esc = message.replace('"', '\\"')
            icon_uri = f"file:///{os.path.abspath(ICON_PATH)}" if ICON_PATH else ""

            ps_script = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastImageAndText02);
            $template.SelectSingleNode("//text[@id=1]").InnerText = "{title_esc}";
            $template.SelectSingleNode("//text[@id=2]").InnerText = "{message_esc}";
            if ("{icon_uri}" -ne "") {{
                $template.SelectSingleNode("//image").SetAttribute("src", "{icon_uri}");
            }}
            $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{APP_NAME}");
            $toast = [Windows.UI.Notifications.ToastNotification]::new($template);
            $notifier.Show($toast);
            '''
            subprocess.run(["powershell", "-Command", ps_script], check=True)
        except Exception as e:
            print(f"[error] Failed to send Windows notification: {e}")
    else:
        print(f"[warn] Unsupported platform for notifications. Title: {title} | Message: {message}")

def get_target_patterns():
    from common import get_platform
    from file_utils import get_games_file

    platform = get_platform()
    if platform == 'unsupported':
        print('Unsupported platform')
        return

    games = get_games_file()
    target_patterns = {}
    for game, data in games.items():
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

    game = current[pid]

    send_notification(title=game, message='Cloud saves is watching')

    config = load_cfg()

    # Add check later if required platform path exists

    games = get_games_file()

    client = supabase.create_client(config.url, config.api_key)

    data = await asyncio.to_thread(get_status, config=config, client=client, games=games, game_choice=game)
    latest = data['latest']

    if latest != 'synced':
        if latest == 'cloud':
            send_notification(title=game, message='Cloud save is ahead. Please close the game for the save syncing to begin')
        state[pid] = {'game': current[pid], 'latest': latest}
    else:
        print('Already Synced')

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

    print(info)
    if info['latest'] == 'cloud':
        print('Downloading')
        await asyncio.to_thread(download_save, config=config, response=(games, game), user_called=False)
    elif info['latest'] == 'local':
        print('Uploading')
        await asyncio.to_thread(upload_save, config=config, games=games, entry=game, user_called=False)

    send_notification(title=game, message='Save Synced')

async def watch_loop(target_patterns, POLL_INTERVAL):
    print("[info] Watching for:", list(target_patterns.values()))
    seen = {}  # {pid: game}
    state = {} # {pid: {game: game, latest: latest}}
    start_tasks = {} # {pid: asyncio task}
    while True: 
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

def main():
    from constants import POLL_INTERVAL
    try:
        target_patterns = get_target_patterns()
        if target_patterns:
            asyncio.run(watch_loop(target_patterns=target_patterns, POLL_INTERVAL=POLL_INTERVAL))
    except KeyboardInterrupt:
        print("\n[info] Stopped.")

if __name__ == "__main__":
    main()
    #send_notification('Testing', 'Test successful')