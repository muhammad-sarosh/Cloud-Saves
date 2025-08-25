# Cloud Saves

A cross-platform (Windows + Linux) command-line tool that syncs game save folders with Supabase Storage.

## Key Features

* **Auto Sync** - Automatically detects running games and syncs your saves
* **Smart sync** - Compares timestamps and file hashes to sync only when needed
* **Safe backups** - Creates timestamped backups before overwriting saves
* **Cross-platform** - Works on both Windows and Linux
* **Multi-threaded** - Fast parallel uploads/downloads
* **Status checking** - See which saves are newer (local vs cloud)
* **Notifications** - Visual and sound notifications (Linux) for sync events
* **Logging** - Writes detailed logs for Auto Sync
* **Auto-cleanup** - Manages old backups and log rotation
* **Playtime Tracking** - Records your game playtime and displays it in hours

## Quick Start

1. **Clone** the repository and navigate to the folder
2. **Setup** Python virtual environment (see [Installation](#install))
3. **Configure** Supabase (see [Supabase Setup](#supabase-setup-one-time))
4. **Run** `python main.py` to add your first game and start syncing!

> **Autostart scripts are included separately.** To run the auto sync (`auto.py`) on system startup, see **[Autostart/README.md](Autostart/README.md)** in this repo. This README focuses on setup, configuration, and manual usage.

---

## Table of Contents

1. [Requirements](#requirements)
2. [Install](#install)

   * [Windows](#windows)
   * [Linux](#linux)
3. [Supabase Setup (one-time)](#supabase-setup-one-time)
4. [First Run & Configuration Files](#first-run--configuration-files)
5. [How to Use](#how-to-use)

   * [Add a game entry](#add-a-game-entry)
   * [Upload / Download / Sync](#upload--download--sync)
   * [Check save status](#check-save-status)
   * [View Game Playtime](#view-game-playtime)
6. [Auto Sync](#auto-sync)
7. [Project Layout](#project-layout)
8. [Settings Reference](#settings-reference)
9. [Troubleshooting](#troubleshooting)
10. [Security & Git Hygiene](#security--git-hygiene)
11. [FAQ](#faq)

---

## Requirements

* **Python 3.10+** (3.11 recommended)
* Internet connectivity when syncing
* Optional for notifications:

  * **Windows:** PowerShell available by default (no extra install required)
  * **Linux:** `notify-send` from **libnotify** (e.g., `sudo apt install libnotify-bin` on Debian/Ubuntu, `sudo pacman -S libnotify` on Arch)
  * **Linux (sound notifications):** Audio player like `paplay` (PulseAudio), `aplay` (ALSA), `play` (SoX), or `ffplay` (FFmpeg)

The Python dependencies are pinned in `requirements.txt` and will be installed into a virtual environment during setup.

> **Note:** The tool works on Windows and Linux. macOS isn’t officially supported. If your OS is neither Windows nor Linux, the app will still run but with errors and will label your platform as “Unsupported”.

---

## Install

Clone or download the repository anywhere you like, then set up a Python virtual environment and install dependencies.

### Windows

Open **Command Prompt** (or PowerShell) in the project folder and run:

```bat
python -m venv windows_env
windows_env\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**What these do:**

* `python -m venv windows_env` — creates an isolated Python environment in the `windows_env` folder
* `windows_env\Scripts\activate` — activates that environment for your current shell session
* `python -m pip install --upgrade pip` — updates `pip` inside the venv
* `pip install -r requirements.txt` — installs all required packages for this project

> If `python` isn’t found, try `py -3 -m venv windows_env` and `py -3 -m pip install --upgrade pip` instead.

### Linux

Open your terminal in the project folder and run:

```bash
python3 -m venv linux_env
source linux_env/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**What these do:**

* `python3 -m venv linux_env` — creates a virtual environment named `linux_env`
* `source linux_env/bin/activate` — enables that venv for your shell
* `python -m pip install --upgrade pip` — updates `pip` inside the venv
* `pip install -r requirements.txt` — installs this project’s dependencies

> Keep this terminal open (or re‑activate the venv later) whenever you run the tool. To deactivate the environment: `deactivate`.

---

## Supabase Setup (one-time)

Follow these exact steps to configure your Supabase project:

1. Go to [https://supabase.com/](https://supabase.com/)
2. Click **Start your project**
3. Sign up and log in
4. You’ll be forwarded to **Create a new organization** — leave defaults (rename if you want) and click **Create organization**
5. **Set a password** for your database and leave other settings as default
6. In the left sidebar, click **Storage**
7. Click **New bucket** and set the name to `game-saves`
8. In the left sidebar, click **SQL Editor**
9. Paste the following and press **Run**:

```sql
-- 1. Create your main table (if it doesn't exist)
create table if not exists public."saves-data" (
    game_name text not null,
    hash text not null,
    last_modified timestamptz not null,
    updated_at timestamptz not null,
    primary key (game_name)
);
alter table public."saves-data" enable row level security;

-- 2. Create the virtual view for schema inspection
create or replace view public.table_column_info as
select table_name, column_name, data_type
from information_schema.columns
where table_schema = 'public';
```

10. Wait for **Success**
11. In the left sidebar, click **Project Settings**
12. In the settings sidebar, click **Data API** and copy the **Project URL** (you’ll need this soon)
13. In the settings sidebar, click **API keys** and reveal the **service\_role** API key (you’ll need this soon)

---

## First Run & Configuration Files

From your activated venv, run the main CLI once to generate config files and capture your Supabase credentials.

```bash
python main.py
```

During first run you’ll see prompts asking for your Supabase details. **Enter the exact values you copied earlier.**

After this, two important JSON files will live in the project root:

* `supabase_config.json` — your Supabase connection info

  ```json
  {
    "url": "https://YOUR-PROJECT-id.supabase.co",
    "api_key": "SERVICE_ROLE_KEY",
    "games_bucket": "game-saves",
    "table_name": "saves-data"
  }
  ```
* `games.json` — your list of games and their per-OS save paths and process names. This file is created/updated via the in-app menu.

---

## How to Use

Start the program from your venv:

```bash
python main.py
```

You’ll see the menu:

```
=== Cloud Saves ===
1: Sync Save
2: Upload Save
3: Download Save
4: Check Save Status
5: Add game entry
6: Remove game entry
7: Edit game entry
8: List games
9: Clear Trash
10: Edit Supabase info
```

### Add a game entry

`Add game entry` guides you through:

1. **Game name** — must be unique
2. **Primary OS save path** — the current OS you’re on; the path is validated
3. **Secondary OS save path (optional)** — not validated (handy if you’re on Windows but also play on Linux, or vice‑versa)
4. **Process names** — needed for auto sync (`auto.py`). Launch the game, open Task Manager/System Monitor, and provide the **exact process name** for **both** Windows and Linux.

   > **Important:** Provide process names when prompted if you want to use Auto Sync as it relies on them to detect the game process reliably.

Example `games.json` after adding **Cuphead**:

```json
{
  "Cuphead": {
    "windows_path": "C:/Users/you/AppData/Local/Cuphead/Saves",
    "windows_process": "Cuphead.exe",
    "linux_path": "/home/you/.local/share/Cuphead/Saves",
    "linux_process": "cuphead"
  }
}
```

### Upload / Download / Sync

* **Upload Save** — pushes files from your local save folder to Supabase Storage under `<GameName>/...`, and records metadata (`hash`, `last_modified`, `updated_at`) in the `saves-data` table.
* **Download Save** — pulls files from Supabase into your local save folder. Your existing local saves are moved into `Trash/<GameName>/<timestamp>/` first (safe backup), preserving subfolders.
* **Sync Save** — for **All games** or a **Specific game**:

  * Compares local vs cloud by timestamps and content hash
  * If cloud is newer, it downloads; if local is newer, it uploads; if equal, it does nothing

You’ll see a progress bar for multi‑file operations. If any file errors occur, they are logged and printed.

### Check save status

`Check save status` shows, per game:

* Whether **Local** or **Cloud** is more recent, or if **Synced**
* `Updated at` (the time the last sync was done)
* `Cloud last modified`
* `Local last modified`

Dates are printed in a friendly format (e.g., `August 06 2025 at 06:35 PM`).

### View game playtime

`List games` shows your configured games along with their paths and process names. If playtime tracking is enabled (`RECORD_PLAYTIME = True` in settings), it also displays the total playtime recorded for each game when using auto sync. Playtime is displayed in hours

---

## Auto Sync

`auto.py` monitors running processes and auto-syncs the moment you close the game:

* When a game starts, it checks which side is newer and waits
* When the game exits, it uploads or downloads automatically, then notifies you
* It sends informative notifications whenever needed, which can also be turned off
* It reloads your game entries if you make any changes to them
* It writes logs to `Logs/cloud_saves.log` [Settings](#settings-reference).

**To run on startup**, see **[Autostart/README.md](Autostart/README.md)**. That folder contains platform‑specific scripts and a dedicated guide.

You can also start it manually from your venv:

```bash
python auto.py
```

> Notifications:
>
> * Windows toasts are sent via PowerShell
> * Linux uses `notify-send` (install libnotify if you don’t see notifications)

---

## Project Layout

```
.
├─ auto.py                 # Process watcher and auto‑sync logic
├─ common.py               # Platform detection, logging, notifications
├─ config.py               # Load/regenerate/edit Supabase config
├─ files.py                # Hashing, moving files to Trash, backups cleanup
├─ game_entry.py           # Add/remove/edit/list game entries
├─ main.py                 # CLI menu entry point
├─ settings.py             # User‑tunable constants (paths, threads, logging)
├─ status.py               # Compute and print local/cloud status
├─ supabase_client.py      # Supabase operations (validate/upload/download/sync)
├─ ui.py                   # Rich prompts and input helpers
├─ requirements.txt        # Python dependencies
├─ Cloud_Saves.png         # Icon used by notifications (referenced in settings)
├─ Sound/                  # Notification sound files
│  └─ notification.ogg     # Default notification sound (user-provided)
├─ Autostart/
│  ├─ README.md            # Autostart guide (Windows & Linux)
│  ├─ Windows/             # Startup scripts
│  └─ Linux/               # Startup scripts
└─ (generated at runtime)
   ├─ supabase_config.json # Your Supabase URL + service_role key, etc.
   ├─ games.json           # Your games & paths
   ├─ Trash/               # Timestamped local backups
   └─ Logs/                # Rotating logs from auto.py
```

---

## Settings Reference

All tunables live in **`settings.py`**.

* `DEFAULT_CONFIG` — default values used to (re)generate `supabase_config.json`
* `CONFIG_FILE` — config file name (`supabase_config.json`)
* `GAMES_FILE` — games file name (`games.json`)
* `SKIP_EXTENSIONS` — file extensions to ignore when hashing/uploading (default: `[".tmp"]`)
* `MAX_DOWNLOAD_THREADS` — max parallel downloads per sync (increase for speed; too high may cause errors on some systems)
* `MAX_UPLOAD_THREADS` — max parallel uploads (start with `1` for reliability)
* `TRASH_FOLDER` — folder where local backups are stored before a download overwrites saves
* `SKIP_GAMES` — names to ignore in auto mode (e.g., `["Cuphead"]`)
* `APP_NAME` — label shown in notifications
* `ICON_PATH` — icon used by notifications (defaults to `Cloud_Saves.png` in repo)
* `POLL_INTERVAL` — seconds between process scans in auto mode
* `RECORD_PLAYTIME` — enable/disable playtime tracking for games (records in hours)
* **Logging:**

  * `LOG_FILE_NAME` — log file name (default `cloud_saves.log`)
  * `LOG_FOLDER` — log directory (empty string means current folder)
  * `MAX_LOG_BYTES` — size before log rotation (default 5 MB)
  * `LOG_BACKUP_COUNT` — how many rotated logs to keep
* **Backups & cleanup:**

  * `MAX_BACKUPS` — how many timestamped `Trash` backups to keep per game
  * `CLEAR_TRASH` — if `True`, auto prune backups on each `auto.py` run
* **Notifications:**

  * `SEND_NOTIFICATIONS` — enable/disable notifications in auto mode
  * `SOUND_ON_NOTIFICATION` — enable/disable sound with notifications on Linux
  * `NOTIFICATION_SOUND_PATH` — path to notification sound file (default: `Sound/notification.ogg`)

Changes take effect next time you run the program(s).

---

## Troubleshooting

**Supabase validation fails (on startup of an action):**

* *“Invalid URL”* — Check the **Data API** Project URL in Supabase settings and re‑enter it via **Edit Supabase info** (menu option 10).
* *“Invalid compact JWS / invalid API key”* — You entered the wrong **service\_role** key. Go to **Project Settings → API keys**, copy **service\_role**, and update it.
* *“Relation … does not exist”* — The table name in config doesn’t match. Use `saves-data` as created by the SQL snippet above.
* *Missing/wrong column types* — Re‑run the SQL snippet exactly and ensure the `table_column_info` view exists.
* *Bucket missing* — The app tries to create `game-saves`. If creation fails, create it manually under **Storage**.

**Download says files are blocked / partial failures:**

* Lower `MAX_DOWNLOAD_THREADS` in `settings.py` and retry. Some filesystems or antivirus can block parallel writes.

**No notifications on Linux:**

* Install libnotify (`sudo apt install libnotify-bin` or `sudo pacman -S libnotify`). Ensure a notification daemon is running (e.g., on KDE/GNOME this is built‑in).

**No notification sounds on Linux:**

* Install an audio player: PulseAudio (`sudo apt install pulseaudio-utils`), ALSA (`sudo apt install alsa-utils`), SoX (`sudo apt install sox`), or FFmpeg (`sudo apt install ffmpeg`).
* Ensure you have a sound file at `Sound/notification.ogg` (or update `NOTIFICATION_SOUND_PATH` in `settings.py`).
* Check that `SOUND_ON_NOTIFICATION = True` in `settings.py`.

**Auto sync didn’t trigger:**

* Verify you added **correct process names** for your OS in `games.json` (use Task Manager or `ps`/System Monitor). The watcher matches against `name`, `exe`, and command line.
* Confirm `auto.py` is running. Check `Logs/cloud_saves.log` for messages.

**Paths are invalid:**

* The app validates the path for the current OS when adding entries. Double‑check typical save locations (e.g., `%AppData%` or `~/.local/share`). You can always edit entries via menu option 7.

**Stuck waiting for Internet:**

* The app requires connectivity for any Supabase operation. If you start an action offline, it will wait until online.

---

## Security & Git Hygiene

* **Never publish your `service_role` key.** It has elevated privileges. Keep `supabase_config.json` private.

If you rotate the service_role key in Supabase, update it in the app via **Edit Supabase info**.

---

## FAQ

**Q: Do I need to be on the same OS to sync between them?**
No. You can upload on Windows and download on Linux (or vice‑versa). Just configure both paths for the same game name.

**Q: How are conflicts resolved?**
On sync, the tool compares timestamps and also hashes. If cloud is newer → download; if local is newer → upload; if equal → do nothing.

**Q: Where are my backups if something goes wrong?**
Before a download overwrites files, your current local saves are moved into `Trash/<GameName>/<timestamp>/`.

**Q: Can I exclude temp or cache files?**
Yes, add extensions to `SKIP_EXTENSIONS` in `settings.py` (e.g., `[".tmp", ".log"]`). They are ignored for upload and hashing.

**Q: Can I run auto sync at startup?**
Yes — see **[Autostart/README.md](Autostart/README.md)**. It contains platform‑specific scripts and instructions.
