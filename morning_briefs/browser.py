from __future__ import annotations

import time
import subprocess
import webbrowser
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlencode

from .config import AppConfig


class BrowserPresenter:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.last_url = ""
        self._fullscreen_toolbar_toggled = False

    def open_dashboard(
        self,
        dashboard_path: Path,
        *,
        presentation: bool,
        external_audio: bool = False,
    ) -> List[str]:
        if not dashboard_path.exists():
            return [f"Dashboard file not found: {dashboard_path}"]
        url = dashboard_path.resolve().as_uri()
        if presentation:
            params = {"presentation": "1"}
            if external_audio:
                params["external_audio"] = "1"
            else:
                params["autoplay"] = "1"
            url = f"{url}?{urlencode(params)}"
        return self.open_url(url, presentation=presentation)

    def open_dashboard_url(
        self,
        base_url: str,
        *,
        presentation: bool,
        external_audio: bool = False,
    ) -> List[str]:
        url = base_url
        if presentation:
            params = {"presentation": "1"}
            if external_audio:
                params["external_audio"] = "1"
            else:
                params["autoplay"] = "1"
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{urlencode(params)}"
        return self.open_url(url, presentation=presentation)

    def open_url(self, url: str, *, presentation: bool) -> List[str]:
        self.last_url = url
        warnings: List[str] = []
        if presentation and self._should_use_chrome():
            try:
                chrome_path = self._chrome_executable()
                profile_dir = self._presentation_profile_dir()
                profile_dir.mkdir(parents=True, exist_ok=True)
                chrome_args = [
                    f"--user-data-dir={profile_dir}",
                    "--no-first-run",
                    "--disable-session-crashed-bubble",
                ]
                if self.config.browser_launch_with_autoplay_policy:
                    chrome_args.extend(
                        [
                            "--autoplay-policy=no-user-gesture-required",
                            "--disable-features=PreloadMediaEngagementData,MediaEngagementBypassAutoplayPolicies",
                        ]
                    )
                if self.config.browser_kiosk_mode:
                    chrome_args.append("--kiosk")
                elif self.config.browser_fullscreen:
                    chrome_args.append("--start-fullscreen")
                if not self.config.browser_kiosk_mode:
                    chrome_args.append("--new-window")
                chrome_args.append(url)
                subprocess.Popen([chrome_path, *chrome_args])
                warnings.extend(self._prepare_native_fullscreen())
            except Exception as exc:
                warnings.append(
                    f"Could not launch {self.config.browser_app} directly; using default browser: {exc}"
                )
                opened = webbrowser.open(url)
                if not opened:
                    warnings.append(f"Browser did not report a successful open for {url}")
        else:
            opened = webbrowser.open(url)
            if not opened:
                warnings.append(f"Browser did not report a successful open for {url}")
        if presentation and self.config.presentation_start_delay_seconds > 0:
            time.sleep(self.config.presentation_start_delay_seconds)
        return warnings

    def close_url(self, url: str = "") -> List[str]:
        warnings: List[str] = []
        if not self.config.browser_close_on_end:
            return warnings
        target = url or self.last_url
        if not target:
            return warnings
        if not self._should_use_chrome():
            return ["Automatic tab closing is only implemented for Google Chrome."]
        warnings.extend(self._restore_fullscreen_toolbar())
        target_escaped = self._applescript_quote(target)
        target_base = target.split("?", 1)[0].rstrip("/")
        target_base_escaped = self._applescript_quote(target_base)
        script = f'''
set targetUrl to "{target_escaped}"
set targetBase to "{target_base_escaped}"
tell application "{self.config.browser_app}"
  repeat with browserWindow in windows
    repeat with browserTab in tabs of browserWindow
      set tabUrl to URL of browserTab
      if (tabUrl starts with targetUrl) or (tabUrl starts with targetBase) then
        close browserWindow
        return
      end if
    end repeat
  end repeat
end tell
'''
        try:
            subprocess.run(
                ["osascript", "-e", script],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            warnings.append("osascript is not available; could not close the Chrome tab.")
        return warnings

    def _should_use_chrome(self) -> bool:
        return "chrome" in self.config.browser_app.lower()

    def _chrome_executable(self) -> str:
        app_name = self.config.browser_app.strip()
        candidates = [
            Path(f"/Applications/{app_name}.app/Contents/MacOS/{app_name}"),
            Path.home() / f"Applications/{app_name}.app/Contents/MacOS/{app_name}",
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return app_name

    def _presentation_profile_dir(self) -> Path:
        stamp = int(time.time() * 1000)
        return self.config.chrome_user_data_dir / f"presentation-{stamp}"

    def _prepare_native_fullscreen(self) -> List[str]:
        if not self.config.browser_fullscreen:
            return []
        script = f'''
set toolbarChanged to false
tell application "{self.config.browser_app}" to activate
delay 1.1
tell application "System Events"
  tell process "{self.config.browser_app}"
    set frontmost to true
    delay 0.2
    if {self._apple_bool(self.config.browser_hide_toolbar_in_fullscreen)} then
      try
        set toolbarItem to menu item "Always Show Toolbar in Full Screen" of menu "View" of menu bar 1
        set toolbarChecked to false
        try
          set markChar to value of attribute "AXMenuItemMarkChar" of toolbarItem
          if markChar is not missing value and markChar is not "" then set toolbarChecked to true
        end try
        if toolbarChecked then
          click toolbarItem
          set toolbarChanged to true
          delay 0.2
        end if
      end try
    end if
    keystroke "f" using {{command down, control down}}
  end tell
end tell
return toolbarChanged as text
'''
        completed = self._run_osascript(script)
        if completed is None:
            return ["osascript is not available; could not request native Chrome fullscreen."]
        if completed.returncode != 0:
            message = completed.stderr.strip() or "unknown AppleScript error"
            return [f"Could not request native Chrome fullscreen: {message}"]
        self._fullscreen_toolbar_toggled = completed.stdout.strip().lower() == "true"
        return []

    def _restore_fullscreen_toolbar(self) -> List[str]:
        if (
            not self._fullscreen_toolbar_toggled
            or not self.config.browser_restore_toolbar_on_close
        ):
            return []
        script = f'''
set restoredToolbar to false
tell application "{self.config.browser_app}" to activate
delay 0.2
tell application "System Events"
  tell process "{self.config.browser_app}"
    set frontmost to true
    delay 0.2
    try
      set toolbarItem to menu item "Always Show Toolbar in Full Screen" of menu "View" of menu bar 1
      set toolbarChecked to false
      try
        set markChar to value of attribute "AXMenuItemMarkChar" of toolbarItem
        if markChar is not missing value and markChar is not "" then set toolbarChecked to true
      end try
      if not toolbarChecked then
        click toolbarItem
        set restoredToolbar to true
      end if
    end try
  end tell
end tell
return restoredToolbar as text
'''
        completed = self._run_osascript(script)
        if completed is None:
            return ["osascript is not available; could not restore Chrome fullscreen toolbar setting."]
        if completed.returncode != 0:
            message = completed.stderr.strip() or "unknown AppleScript error"
            return [f"Could not restore Chrome fullscreen toolbar setting: {message}"]
        self._fullscreen_toolbar_toggled = False
        return []

    def _run_osascript(
        self, script: str
    ) -> Optional[subprocess.CompletedProcess[str]]:
        try:
            return subprocess.run(
                ["osascript", "-e", script],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return None

    @staticmethod
    def _apple_bool(value: bool) -> str:
        return "true" if value else "false"

    @staticmethod
    def _applescript_quote(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')
