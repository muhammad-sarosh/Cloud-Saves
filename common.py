import platform
import os
import logging
import time
import subprocess

# Checks OS Type
def get_platform():
    system = platform.system()
    if "windows" in system.lower().strip(): return "windows"
    elif "linux" in system.lower().strip(): return "linux"
    else: return "unsupported"


# Doesn't let the user continue until they have internet access
def internet_check(host="8.8.8.8", port=53, timeout=3):
    import socket
    from rich import print 

    if is_auto_mode():
        internet_logged = False

    while True:
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            log('Internet connection confirmed')
            return
        except socket.error:
            if is_auto_mode():
                if not internet_logged:
                    log('No internet detected, waiting...', 'warning')
                    internet_logged = True
                time.sleep(3)
            else:
                print("No internet access detected. Press 'Enter' to retry or 'Ctrl + C' to exit")
                input()

def is_auto_mode():
    return os.environ.get('AUTO_MODE') == "1"

def log(message, level='info'):
    if is_auto_mode():
        logger = logging.getLogger()
        if level == 'error':
            logger.error(message)
        elif level == 'info':
            logger.info(message)
        elif level == 'warning':
            logger.warning(message)

def send_notification(title, message):
    from settings import APP_NAME, ICON_PATH, SEND_NOTIFICATIONS
    from common import get_platform

    if not is_auto_mode() or not SEND_NOTIFICATIONS:
        return

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
            log("'notify-send' not found. Install 'libnotify-bin'", 'error')
        except Exception as e:
            log(f"Failed to send Linux notification: {e}", 'error')
    elif platform_name == "windows":
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

        # Ensure no window flashes
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-WindowStyle", "Hidden",
                "-ExecutionPolicy", "Bypass",
                "-Command", ps_script
            ],
            check=True,
            startupinfo=startupinfo,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
    else:
        log(f"Unsupported platform for notifications", 'error')