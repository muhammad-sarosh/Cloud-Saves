# Autostart Files

This folder contains platform-specific scripts to automatically start the Cloud Saves application.

## Structure

- `Windows/` - Contains Windows-specific autostart files
  - `cloud_saves_autostart.bat` - Batch file for manual execution
  - `cloud_saves_autostart.vbs` - VBScript for silent execution (no console window)

- `Linux/` - Contains Linux-specific autostart files
  - `cloud_saves_autostart.sh` - Shell script for manual execution
  - `cloud-saves.service` - systemd service file for automatic startup

## Usage

### Windows

1. **Manual execution**: Double-click `cloud_saves_autostart.bat` or `cloud_saves_autostart.vbs`
2. **Autostart**: Make a shortcut to the `.vbs` file and put it in your Windows startup folder:
   - Press `Win + R`, type `shell:startup`, and press Enter
   - Cut and paste `cloud_saves_autostart - Shortcut.vbs` to this folder

### Linux

1. **Manual execution**: Run `./cloud_saves_autostart.sh` from the Linux folder
2. **Autostart**:
   - Edit `cloud-saves.service` and replace `/full/path/to/your/project` with the actual project path
   - Copy to systemd: `sudo cp cloud-saves.service ~/.config/systemd/user/`
   - Reload Services: `systemctl --user daemon-reload`
   - Enable and Start: `systemctl --user enable --now cloud-saves.service`

## Notes

- All scripts automatically detect and use the appropriate virtual environment (`windows_env` or `linux_env`). Change the envname variable in the scripts if your environment names are different
- The scripts calculate the project root directory based on their location in the folder structure
