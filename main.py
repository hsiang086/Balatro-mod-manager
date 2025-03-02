import os
import json
import platform
import zipfile
import tarfile
import tempfile
import shutil
import requests
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.widget import Widget
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.factory import Factory
from kivy.properties import BooleanProperty
from kivy.uix.button import Button

# ----- Determine Default Paths for Each OS -----
if platform.system() == "Windows":
    default_target_dll = r"C:\Program Files (x86)\Steam\steamapps\common\Balatro"
    default_mod_target = os.path.expandvars(r"%AppData%\Balatro\Mods")
elif platform.system() == "Darwin":
    default_target_dll = "/Applications/Balatro"
    default_mod_target = os.path.expanduser("~/Library/Application Support/Balatro/Mods")
else:
    default_target_dll = os.path.expanduser("~/Balatro")
    default_mod_target = os.path.expanduser("~/.balatro/mods")

# ----- Hover Behavior and Custom Button Classes -----
class HoverBehavior(object):
    hovered = BooleanProperty(False)
    def __init__(self, **kwargs):
        super(HoverBehavior, self).__init__(**kwargs)
        Window.bind(mouse_pos=self.on_mouse_pos)
    def on_mouse_pos(self, window, pos):
        if not self.get_root_window():
            return
        self.hovered = self.collide_point(*self.to_widget(*pos))

class HoverButton(HoverBehavior, Button):
    pass

# ----- KV Language Styling (Elegant Look) -----
Builder.load_string('''
#:import dp kivy.metrics.dp

<HeaderLabel@Label>:
    color: 1, 1, 1, 1
    font_size: '20sp'
    bold: True
    size_hint_y: None
    height: dp(50)
    padding: dp(10), 0
    canvas.before:
        Color:
            rgba: 0.1, 0.1, 0.2, 1
        Rectangle:
            pos: self.pos
            size: self.size

<StatusBar@BoxLayout>:
    size_hint_y: None
    height: dp(40)
    padding: dp(10)
    canvas.before:
        Color:
            rgba: 0.15, 0.15, 0.2, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(8)]

<SectionHeaderLabel@Label>:
    color: 1, 1, 1, 1
    font_size: '16sp'
    bold: True
    size_hint_y: None
    height: dp(30)
    padding: dp(5), 0

<ThemedLabel@Label>:
    color: 0.95, 0.95, 0.95, 1
    font_size: '14sp'
    halign: 'left'
    valign: 'middle'
    text_size: self.size

<ThemedInput@TextInput>:
    hint_text: "Enter path here..."
    background_color: 0.2, 0.2, 0.25, 1
    foreground_color: 0.95, 0.95, 0.95, 1
    cursor_color: 1, 1, 1, 1
    padding: [10, 10, 10, 10]
    font_size: '14sp'

<ThemedButton@HoverButton>:
    background_normal: ''
    background_color: 0.25, 0.5, 0.8, 1
    color: 1, 1, 1, 1
    font_size: '14sp'
    size_hint_y: None
    height: dp(40)
    canvas.before:
        Color:
            rgba: self.background_color if not self.hovered else (min(self.background_color[0]+0.1, 1), min(self.background_color[1]+0.1, 1), min(self.background_color[2]+0.1, 1), 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(10)]

<DangerButton@HoverButton>:
    background_normal: ''
    background_color: 0.8, 0.3, 0.3, 1
    color: 1, 1, 1, 1
    font_size: '14sp'
    size_hint_y: None
    height: dp(40)
    canvas.before:
        Color:
            rgba: self.background_color if not self.hovered else (min(self.background_color[0]+0.1, 1), min(self.background_color[1]+0.1, 1), min(self.background_color[2]+0.1, 1), 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(10)]

<ThemedSpinner@Spinner>:
    background_color: 0.25, 0.5, 0.8, 1
    color: 1, 1, 1, 1
    font_size: '14sp'
    size_hint_y: None
    height: dp(40)

<ThemedProgressBar@ProgressBar>:
    canvas.before:
        Color:
            rgba: 0.1, 0.1, 0.1, 1
        Rectangle:
            pos: self.pos
            size: self.size

<ModCard@BoxLayout>:
    orientation: 'vertical'
    padding: dp(8)
    spacing: dp(8)
    size_hint_y: None
    height: dp(64)
    canvas.before:
        Color:
            rgba: 0.2, 0.22, 0.25, 1
        Rectangle:
            pos: self.pos
            size: self.size
''')

# ----- Release URLs -----
RELEASE_URLS = {
    "Windows (x86_64-pc-windows-msvc)": "https://github.com/ethangreen-dev/lovely-injector/releases/download/v0.7.1/lovely-x86_64-pc-windows-msvc.zip",
    "macOS (x86_64-apple-darwin)": "https://github.com/ethangreen-dev/lovely-injector/releases/download/v0.7.1/lovely-x86_64-apple-darwin.tar.gz",
    "macOS (aarch64-apple-darwin)": "https://github.com/ethangreen-dev/lovely-injector/releases/download/v0.7.1/lovely-aarch64-apple-darwin.tar.gz"
}

# ----- Custom File Chooser -----
class CustomFileChooser(FileChooserListView):
    def __init__(self, **kwargs):
        super(CustomFileChooser, self).__init__(**kwargs)
    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return super(CustomFileChooser, self).on_touch_up(touch)
        touch.ungrab(self)
        if self.collide_point(*touch.pos):
            return True
        return super(CustomFileChooser, self).on_touch_up(touch)

# ----- Directory Chooser Popup -----
class DirectoryChooserPopup(Popup):
    def __init__(self, select_callback, **kwargs):
        super().__init__(**kwargs)
        self.title = "Select Directory"
        self.size_hint = (0.9, 0.9)
        self.select_callback = select_callback
        self.background_color = (0.15, 0.15, 0.2, 1)
        self.title_color = (1, 1, 1, 1)
        box = BoxLayout(orientation="vertical", spacing=dp(10))
        self.filechooser = CustomFileChooser(path='.', filters=[])
        box.add_widget(self.filechooser)
        btn_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10), padding=[0, dp(10), 0, 0])
        select_btn = Factory.ThemedButton(text="Select")
        select_btn.bind(on_press=self.select_dir)
        cancel_btn = Factory.ThemedButton(text="Cancel")
        cancel_btn.bind(on_press=self.dismiss)
        btn_layout.add_widget(select_btn)
        btn_layout.add_widget(cancel_btn)
        box.add_widget(btn_layout)
        self.add_widget(box)
    def select_dir(self, instance):
        if self.filechooser.selection:
            selected_path = self.filechooser.selection[0]
            if os.path.isdir(selected_path):
                self.select_callback(selected_path)
                self.dismiss()

# ----- File Chooser Popup -----
class FileChooserPopup(Popup):
    def __init__(self, select_callback, filters=None, **kwargs):
        super().__init__(**kwargs)
        self.title = "Select File"
        self.size_hint = (0.9, 0.9)
        self.select_callback = select_callback
        self.background_color = (0.15, 0.15, 0.2, 1)
        self.title_color = (1, 1, 1, 1)
        box = BoxLayout(orientation="vertical", spacing=dp(10))
        self.filechooser = CustomFileChooser(filters=filters if filters else [])
        box.add_widget(self.filechooser)
        btn_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10), padding=[0, dp(10), 0, 0])
        select_btn = Factory.ThemedButton(text="Select")
        select_btn.bind(on_press=self.select_file)
        cancel_btn = Factory.ThemedButton(text="Cancel")
        cancel_btn.bind(on_press=self.dismiss)
        btn_layout.add_widget(select_btn)
        btn_layout.add_widget(cancel_btn)
        box.add_widget(btn_layout)
        self.add_widget(box)
    def select_file(self, instance):
        if self.filechooser.selection:
            selected_path = self.filechooser.selection[0]
            self.select_callback(selected_path)
            self.dismiss()

# ----- Main Application -----
class BalatroManagerApp(App):
    def build(self):
        self.icon = "assets/icon.jpg"  # Set the app icon
        Window.size = (900, 700)
        Window.clearcolor = (0.08, 0.08, 0.12, 1)
        Window.minimum_width = 700
        Window.minimum_height = 600

        main_layout = BoxLayout(orientation='vertical', spacing=0, padding=0)

        # Header.
        header = Factory.HeaderLabel(text="Balatro Mod & Injector Manager")
        main_layout.add_widget(header)

        # Always-visible Status Bar.
        status_bar = Factory.StatusBar()
        self.lovely_status_label = Factory.ThemedLabel(text="Lovely Status: Not Installed", color=(0.9, 0.7, 0.3, 1))
        status_bar.add_widget(self.lovely_status_label)
        main_layout.add_widget(status_bar)

        # Scrollable Content.
        scroll_view = ScrollView(size_hint=(1, 1))
        content_layout = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(15), size_hint_y=None)
        content_layout.bind(minimum_height=content_layout.setter('height'))

        # Section 1: Lovely Installer.
        installer_section = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10), size_hint_y=None, height=dp(300))
        with installer_section.canvas.before:
            Color(rgba=(0.16, 0.16, 0.2, 1))
            self.installer_rect = Rectangle(pos=installer_section.pos, size=installer_section.size)
        installer_section.bind(pos=lambda inst, val: setattr(self.installer_rect, 'pos', val),
                               size=lambda inst, val: setattr(self.installer_rect, 'size', val))
        installer_header = Factory.SectionHeaderLabel(text="Lovely Installer")
        installer_section.add_widget(installer_header)
        local_folder_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(10))
        local_folder_label = Factory.ThemedLabel(text="Local Lovely Folder:", size_hint_x=0.3)
        self.local_folder_input = Factory.ThemedInput(text='"{}"'.format(os.path.join(os.getcwd(), "lovely")), multiline=False, readonly=True)
        local_folder_layout.add_widget(local_folder_label)
        local_folder_layout.add_widget(self.local_folder_input)
        installer_section.add_widget(local_folder_layout)
        target_dll_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(10))
        target_dll_label = Factory.ThemedLabel(text="Target DLL Directory:", size_hint_x=0.3)
        self.target_dll_input = Factory.ThemedInput(text='"{}"'.format(default_target_dll), multiline=False)
        target_dll_browse = Factory.ThemedButton(text="Browse", size_hint_x=0.15)
        target_dll_browse.bind(on_press=self.browse_target_dll)
        target_dll_paste = Factory.ThemedButton(text="Paste", size_hint_x=0.15)
        target_dll_paste.bind(on_press=self.paste_target_dll)
        target_dll_clear = Factory.ThemedButton(text="Clear", size_hint_x=0.15)
        target_dll_clear.bind(on_press=self.clear_target_dll)
        target_dll_layout.add_widget(target_dll_label)
        target_dll_layout.add_widget(self.target_dll_input)
        target_dll_layout.add_widget(target_dll_browse)
        target_dll_layout.add_widget(target_dll_paste)
        target_dll_layout.add_widget(target_dll_clear)
        installer_section.add_widget(target_dll_layout)
        release_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(10))
        release_label = Factory.ThemedLabel(text="Injector Release:", size_hint_x=0.3)
        self.release_spinner = Factory.ThemedSpinner(
            text="Windows (x86_64-pc-windows-msvc)",
            values=list(RELEASE_URLS.keys()),
            size_hint_x=0.7)
        release_layout.add_widget(release_label)
        release_layout.add_widget(self.release_spinner)
        installer_section.add_widget(release_layout)
        installer_btn_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        download_btn = Factory.ThemedButton(text="Download Lovely")
        download_btn.bind(on_press=self.start_download_lovely)
        install_btn = Factory.ThemedButton(text="Install Lovely")
        install_btn.bind(on_press=self.install_lovely)
        uninstall_btn = Factory.DangerButton(text="Uninstall Lovely")
        uninstall_btn.bind(on_press=self.uninstall_lovely)
        installer_btn_layout.add_widget(download_btn)
        installer_btn_layout.add_widget(install_btn)
        installer_btn_layout.add_widget(uninstall_btn)
        installer_section.add_widget(installer_btn_layout)
        progress_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(50), spacing=dp(5))
        progress_label = Factory.ThemedLabel(text="Download Progress:", size_hint_y=None, height=dp(20))
        self.lovely_progress = Factory.ThemedProgressBar(max=100, value=0, size_hint_y=None, height=dp(20))
        progress_layout.add_widget(progress_label)
        progress_layout.add_widget(self.lovely_progress)
        installer_section.add_widget(progress_layout)
        content_layout.add_widget(installer_section)

        # Spacer.
        spacer = Widget(size_hint_y=None, height=dp(50))
        content_layout.add_widget(spacer)

        # Section 2: Mods Manager.
        mods_section = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10), size_hint_y=None)
        mods_section.height = dp(300)
        with mods_section.canvas.before:
            Color(rgba=(0.16, 0.16, 0.2, 1))
            self.mods_rect = Rectangle(pos=mods_section.pos, size=mods_section.size)
        mods_section.bind(pos=lambda inst, val: setattr(self.mods_rect, 'pos', val),
                          size=lambda inst, val: setattr(self.mods_rect, 'size', val))
        mods_header = Factory.SectionHeaderLabel(text="Mods Manager")
        mods_section.add_widget(mods_header)
        mod_select_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(10))
        mod_select_label = Factory.ThemedLabel(text="Mod (ZIP or Folder):", size_hint_x=0.3)
        self.mod_path_input = Factory.ThemedInput(text="", multiline=False)
        mod_browse = Factory.ThemedButton(text="Browse", size_hint_x=0.15)
        mod_browse.bind(on_press=self.browse_mod)
        mod_paste = Factory.ThemedButton(text="Paste", size_hint_x=0.15)
        mod_paste.bind(on_press=self.paste_mod_path)
        mod_clear = Factory.ThemedButton(text="Clear", size_hint_x=0.15)
        mod_clear.bind(on_press=self.clear_mod_path)
        mod_select_layout.add_widget(mod_select_label)
        mod_select_layout.add_widget(self.mod_path_input)
        mod_select_layout.add_widget(mod_browse)
        mod_select_layout.add_widget(mod_paste)
        mod_select_layout.add_widget(mod_clear)
        mods_section.add_widget(mod_select_layout)
        mod_target_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(10))
        mod_target_label = Factory.ThemedLabel(text="Mods Target Directory:", size_hint_x=0.3)
        self.mod_target_input = Factory.ThemedInput(text='"{}"'.format(default_mod_target), multiline=False)
        mod_target_browse = Factory.ThemedButton(text="Browse", size_hint_x=0.15)
        mod_target_browse.bind(on_press=self.browse_mod_target)
        mod_target_paste = Factory.ThemedButton(text="Paste", size_hint_x=0.15)
        mod_target_paste.bind(on_press=self.paste_mod_target)
        mod_target_clear = Factory.ThemedButton(text="Clear", size_hint_x=0.15)
        mod_target_clear.bind(on_press=self.clear_mod_target)
        mod_target_layout.add_widget(mod_target_label)
        mod_target_layout.add_widget(self.mod_target_input)
        mod_target_layout.add_widget(mod_target_browse)
        mod_target_layout.add_widget(mod_target_paste)
        mod_target_layout.add_widget(mod_target_clear)
        mods_section.add_widget(mod_target_layout)
        mod_btn_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        install_mod_btn = Factory.ThemedButton(text="Install Mod")
        install_mod_btn.bind(on_press=self.install_mod)
        refresh_mods_btn = Factory.ThemedButton(text="Refresh Mods List")
        refresh_mods_btn.bind(on_press=lambda x: self.refresh_mods_list())
        mod_btn_layout.add_widget(install_mod_btn)
        mod_btn_layout.add_widget(refresh_mods_btn)
        mods_section.add_widget(mod_btn_layout)
        installed_mods_header = Factory.SectionHeaderLabel(text="Installed Mods")
        mods_section.add_widget(installed_mods_header)
        mods_list_scroll = ScrollView(size_hint=(1, None), height=dp(150), do_scroll_x=False)
        self.installed_mods_box = GridLayout(cols=1, spacing=dp(5), size_hint_y=None, padding=[0, 0, dp(10), 0])
        self.installed_mods_box.bind(minimum_height=self.installed_mods_box.setter('height'))
        mods_list_scroll.add_widget(self.installed_mods_box)
        mods_section.add_widget(mods_list_scroll)
        content_layout.add_widget(mods_section)

        scroll_view.add_widget(content_layout)
        main_layout.add_widget(scroll_view)

        # Footer.
        footer = BoxLayout(size_hint_y=None, height=dp(30), padding=[dp(10), 0])
        with footer.canvas.before:
            Color(rgba=(0.1, 0.1, 0.15, 1))
            self.footer_rect = Rectangle(pos=footer.pos, size=footer.size)
        footer.bind(pos=lambda inst, val: setattr(self.footer_rect, 'pos', val),
                    size=lambda inst, val: setattr(self.footer_rect, 'size', val))
        footer_label = Factory.ThemedLabel(text="© 2025 Balatro Modding Community", font_size='12sp')
        footer.add_widget(footer_label)
        main_layout.add_widget(footer)

        # Bind changes so config is saved automatically.
        self.target_dll_input.bind(text=lambda inst, value: self.save_config())
        self.mod_target_input.bind(text=lambda inst, value: self.save_config())
        self.mod_path_input.bind(text=lambda inst, value: self.save_config())

        self.load_config()
        self.refresh_mods_list()
        self.update_lovely_status()
        return main_layout

    # ----- Helper to remove surrounding quotes.
    def clean_path(self, path):
        return path.strip().strip('"').strip("'")

    # ----- Paste Functions -----
    def paste_target_dll(self, instance):
        text = Clipboard.paste()
        clean = text.strip().strip('"').strip("'")
        self.target_dll_input.text = f'"{clean}"'
    def paste_mod_target(self, instance):
        text = Clipboard.paste()
        clean = text.strip().strip('"').strip("'")
        self.mod_target_input.text = f'"{clean}"'
    def paste_mod_path(self, instance):
        text = Clipboard.paste()
        clean = text.strip().strip('"').strip("'")
        self.mod_path_input.text = f'"{clean}"'

    # ----- Clear Functions -----
    def clear_target_dll(self, instance):
        old = self.clean_path(self.target_dll_input.text)
        self.target_dll_input.text = ""
        self.target_dll_input.hint_text = "Last used: " + old
        self.save_config()
    def clear_mod_target(self, instance):
        old = self.clean_path(self.mod_target_input.text)
        self.mod_target_input.text = ""
        self.mod_target_input.hint_text = "Last used: " + old
        self.save_config()
    def clear_mod_path(self, instance):
        old = self.clean_path(self.mod_path_input.text)
        self.mod_path_input.text = ""
        self.mod_path_input.hint_text = "Last used: " + old
        self.save_config()

    # ----- Browse Callbacks -----
    def browse_target_dll(self, instance):
        popup = DirectoryChooserPopup(select_callback=self.set_target_dll)
        popup.open()
    def set_target_dll(self, path):
        clean = path.strip().strip('"').strip("'")
        self.target_dll_input.text = f'"{clean}"'
        self.save_config()
        self.update_lovely_status()
    def browse_mod_target(self, instance):
        popup = DirectoryChooserPopup(select_callback=self.set_mod_target)
        popup.open()
    def set_mod_target(self, path):
        clean = path.strip().strip('"').strip("'")
        self.mod_target_input.text = f'"{clean}"'
        self.save_config()
        self.refresh_mods_list()
    def browse_mod(self, instance):
        popup = FileChooserPopup(select_callback=self.set_mod_path)
        popup.open()
    def set_mod_path(self, path):
        clean = path.strip().strip('"').strip("'")
        self.mod_path_input.text = f'"{clean}"'

    # ----- Config: Load/Save paths -----
    def config_path(self):
        return os.path.join(os.getcwd(), "config.json")
    def load_config(self):
        try:
            with open(self.config_path(), "r") as f:
                data = json.load(f)
            if "target_dll" in data:
                self.target_dll_input.text = f'"{data["target_dll"]}"'
            if "mod_target" in data:
                self.mod_target_input.text = f'"{data["mod_target"]}"'
            if "last_mod_path" in data:
                self.mod_path_input.text = f'"{data["last_mod_path"]}"'
        except Exception:
            pass
    def save_config(self):
        data = {
            "target_dll": self.clean_path(self.target_dll_input.text),
            "mod_target": self.clean_path(self.mod_target_input.text),
            "last_mod_path": self.clean_path(self.mod_path_input.text)
        }
        try:
            with open(self.config_path(), "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print("Error saving config:", e)

    # ----- Download Lovely in a separate thread -----
    def start_download_lovely(self, instance):
        self.lovely_progress.value = 0
        threading.Thread(target=self.download_lovely_thread, daemon=True).start()
    def download_lovely_thread(self):
        release = self.release_spinner.text
        url = RELEASE_URLS.get(release)
        if not url:
            Clock.schedule_once(lambda dt: self.update_lovely_status("Invalid release selection."), 0)
            return
        Clock.schedule_once(lambda dt: self.update_lovely_status("Downloading archive...", (0.25, 0.5, 0.8, 1)), 0)
        try:
            r = requests.get(url, stream=True)
            r.raise_for_status()
            total_length = r.headers.get('content-length')
            total_length = int(total_length) if total_length else 0
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            downloaded = 0
            chunk_size = 8192
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    temp_file.write(chunk)
                    downloaded += len(chunk)
                    if total_length:
                        percent = int(downloaded / total_length * 100)
                        Clock.schedule_once(lambda dt, p=percent: self.update_progress(p), 0)
            temp_file.close()
            archive_path = temp_file.name
        except Exception as e:
            Clock.schedule_once(lambda dt: self.update_lovely_status("Download error: " + str(e), (0.8, 0.3, 0.3, 1)), 0)
            return
        Clock.schedule_once(lambda dt: self.update_lovely_status("Extracting archive...", (0.25, 0.5, 0.8, 1)), 0)
        lovely_folder = os.path.join(os.getcwd(), "lovely")
        if os.path.exists(lovely_folder):
            shutil.rmtree(lovely_folder)
        os.makedirs(lovely_folder, exist_ok=True)
        success = self.extract_archive(archive_path, lovely_folder, url)
        os.remove(archive_path)
        if success:
            found = False
            for root_dir, dirs, files in os.walk(lovely_folder):
                if any(f.lower() == "version.dll" for f in files):
                    found = True
                    break
            if found:
                Clock.schedule_once(lambda dt: self.update_lovely_status("Lovely downloaded and extracted successfully.", (0.3, 0.8, 0.3, 1)), 0)
            else:
                Clock.schedule_once(lambda dt: self.update_lovely_status("Extraction complete, but version.dll not found.", (0.8, 0.6, 0.3, 1)), 0)
        else:
            Clock.schedule_once(lambda dt: self.update_lovely_status("Extraction failed.", (0.8, 0.3, 0.3, 1)), 0)

    def update_progress(self, value):
        self.lovely_progress.value = value

    def update_lovely_status(self, message=None, color=None):
        if color is None:
            color = (0.9, 0.7, 0.3, 1)
        if message:
            self.lovely_status_label.text = f"Lovely Status: {message}"
            self.lovely_status_label.color = color
        else:
            target_dir = self.clean_path(self.target_dll_input.text)
            target_dll_path = os.path.join(target_dir, "version.dll")
            if os.path.isfile(target_dll_path):
                self.lovely_status_label.text = "Lovely Status: Installed"
                self.lovely_status_label.color = (0.3, 0.8, 0.3, 1)
            else:
                self.lovely_status_label.text = "Lovely Status: Not Installed"
                self.lovely_status_label.color = (0.9, 0.7, 0.3, 1)

    def extract_archive(self, archive_path, target_folder, url):
        try:
            if "zip" in url:
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    zf.extractall(target_folder)
            elif "tar.gz" in url:
                with tarfile.open(archive_path, 'r:gz') as tar:
                    tar.extractall(target_folder)
            else:
                self.update_lovely_status("Unsupported archive format.", (0.8, 0.3, 0.3, 1))
                return False
            return True
        except Exception as e:
            self.update_lovely_status("Extraction error: " + str(e), (0.8, 0.3, 0.3, 1))
            return False

    def install_lovely(self, instance):
        lovely_folder = os.path.join(os.getcwd(), "lovely")
        if not os.path.exists(lovely_folder):
            self.update_lovely_status("Lovely not downloaded.", (0.8, 0.3, 0.3, 1))
            return
        version_dll_source = None
        for root_dir, dirs, files in os.walk(lovely_folder):
            for file in files:
                if file.lower() == "version.dll":
                    version_dll_source = os.path.join(root_dir, file)
                    break
            if version_dll_source:
                break
        if not version_dll_source:
            self.update_lovely_status("version.dll not found in downloaded files.", (0.8, 0.3, 0.3, 1))
            return
        target_dir = self.clean_path(self.target_dll_input.text)
        if not os.path.isdir(target_dir):
            self.update_lovely_status("Invalid target DLL directory.", (0.8, 0.3, 0.3, 1))
            return
        target_dll_path = os.path.join(target_dir, "version.dll")
        try:
            shutil.copy(version_dll_source, target_dll_path)
            self.update_lovely_status("Installation complete!", (0.3, 0.8, 0.3, 1))
        except Exception as e:
            self.update_lovely_status("Failed to install Lovely: " + str(e), (0.8, 0.3, 0.3, 1))

    def uninstall_lovely(self, instance):
        target_dir = self.clean_path(self.target_dll_input.text)
        target_dll_path = os.path.join(target_dir, "version.dll")
        if os.path.isfile(target_dll_path):
            try:
                os.remove(target_dll_path)
                self.update_lovely_status("Lovely successfully uninstalled.", (0.3, 0.7, 0.9, 1))
            except Exception as e:
                self.update_lovely_status(f"Uninstall failed: {e}", (0.8, 0.3, 0.3, 1))
        else:
            self.update_lovely_status("Lovely is not installed in target directory.", (0.8, 0.7, 0.3, 1))

    def flatten_mod_directory(self, mod_dir, target_parent):
        if not os.path.exists(mod_dir):
            return
        items = os.listdir(mod_dir)
        if items and all(os.path.isdir(os.path.join(mod_dir, item)) for item in items):
            for item in items:
                src = os.path.join(mod_dir, item)
                dst = os.path.join(target_parent, item)
                try:
                    shutil.move(src, dst)
                except Exception as e:
                    print(f"Error moving {src} to {dst}: {e}")
            shutil.rmtree(mod_dir)

    def install_mod(self, instance):
        mod_path = self.clean_path(self.mod_path_input.text)
        mod_target = self.clean_path(self.mod_target_input.text)
        if not os.path.exists(mod_target):
            os.makedirs(mod_target)
        if not mod_path or not os.path.exists(mod_path):
            self.show_notification("Invalid mod selection.")
            return
        if os.path.isfile(mod_path) and mod_path.lower().endswith(".zip"):
            mod_name = os.path.splitext(os.path.basename(mod_path))[0]
            dest_dir = os.path.join(mod_target, mod_name)
            try:
                with zipfile.ZipFile(mod_path, 'r') as zf:
                    zf.extractall(dest_dir)
                self.flatten_mod_directory(dest_dir, mod_target)
                self.show_notification(f"Mod '{mod_name}' installed from ZIP.", True)
            except Exception as e:
                self.show_notification(f"Failed to extract mod ZIP: {e}", False)
                return
        elif os.path.isdir(mod_path):
            mod_name = os.path.basename(mod_path.rstrip(os.sep))
            dest_dir = os.path.join(mod_target, mod_name)
            try:
                if os.path.exists(dest_dir):
                    shutil.rmtree(dest_dir)
                shutil.copytree(mod_path, dest_dir)
                self.flatten_mod_directory(dest_dir, mod_target)
                self.show_notification(f"Mod '{mod_name}' installed from folder.", True)
            except Exception as e:
                self.show_notification(f"Failed to copy mod folder: {e}", False)
                return
        else:
            self.show_notification("Invalid mod selection.")
            return
        self.refresh_mods_list()

    def uninstall_mod(self, mod_name):
        mod_target = self.clean_path(self.mod_target_input.text)
        mod_dir = os.path.join(mod_target, mod_name)
        if os.path.isdir(mod_dir):
            try:
                shutil.rmtree(mod_dir)
                self.show_notification(f"Mod '{mod_name}' uninstalled.", True)
            except Exception as e:
                self.show_notification(f"Failed to uninstall mod '{mod_name}': {e}", False)
        else:
            self.show_notification("Mod not found.")
        self.refresh_mods_list()

    def refresh_mods_list(self):
        self.installed_mods_box.clear_widgets()
        mod_target = self.clean_path(self.mod_target_input.text)
        if os.path.isdir(mod_target):
            for item in os.listdir(mod_target):
                item_path = os.path.join(mod_target, item)
                if os.path.isdir(item_path):
                    mod_card = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
                    mod_label = Factory.ThemedLabel(text=item, size_hint_x=0.7)
                    remove_btn = Factory.DangerButton(text="Remove", size_hint_x=0.3)
                    remove_btn.bind(on_press=lambda instance, mod=item: self.uninstall_mod(mod))
                    mod_card.add_widget(mod_label)
                    mod_card.add_widget(remove_btn)
                    self.installed_mods_box.add_widget(mod_card)
        else:
            self.installed_mods_box.add_widget(Factory.ThemedLabel(text="Mods target directory not found."))

    def show_notification(self, message, success=False):
        popup = Popup(
            title="Notification",
            content=Factory.ThemedLabel(text=message),
            size_hint=(None, None),
            size=(dp(300), dp(150))
        )
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), 2)

if __name__ == '__main__':
    BalatroManagerApp().run()
