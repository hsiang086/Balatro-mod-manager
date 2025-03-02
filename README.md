# Balatro Mod & Injector Manager

Balatro Mod & Injector Manager is a cross-platform application built with Python and Kivy that helps users manage mods and install the "Lovely" DLL for Balatro. The application features a modern, elegant UI with convenient Paste and Clear buttons for path fields and automatically stores configuration data (including the last used mod path) in a JSON file.

## Features

- **Lovely Installer:**  
  - Download, extract, and install the "Lovely" DLL into a target directory.
  - Uninstall function to remove the installed DLL.
  
- **Mods Manager:**  
  - Install mods from ZIP files or folders.
  - Browse for mod files and target directories.
  - Automatically refresh and display a list of installed mods.
  - Easily remove mods via the UI.

- **Cross-Platform Compatibility:**  
  - Default paths automatically adjust for Windows, macOS, and Linux.

- **Configuration Persistence:**  
  - Saves and loads configuration (Target DLL Directory, Mods Target Directory, and last used Mod Path) using a JSON file (`config.json`).

- **User-Friendly Interface:**  
  - Paste buttons for quick insertion of clipboard text.
  - Clear buttons that reset fields and display the last used value as a hint.
  - Scrollable content and elegant styling with hover effects.

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/balatro-mod-manager.git
   cd balatro-mod-manager
   ```

2. **Create a virtual environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install the required dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Prepare Assets:**

   Create an `assets` folder in the project root and place your `icon.jpg` file there. This image will be used as the application icon.

## Usage

Run the application with:

```bash
python main.py
```

When the application launches, you'll see two main sections:
- **Lovely Installer:** Use the Browse, Paste, and Clear buttons to set the Target DLL Directory.
- **Mods Manager:** Easily manage mods by selecting, pasting, or clearing paths for mod files and target directories. The last used mod path is saved to help speed up future selections.

Your settings are automatically saved to a `config.json` file in the project directory.

## Project Structure

```
balatro-mod-manager/
├── assets/
│   └── icon.jpg
├── config.json         # Auto-generated configuration file
├── main.py
├── requirements.txt
└── .gitignore
```

## Contributing

Contributions are welcome! If you have suggestions or bug fixes, please open an issue or submit a pull request.