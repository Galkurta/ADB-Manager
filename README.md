# ADB Manager

A modern, cross-platform desktop application that provides a user-friendly GUI wrapper for Android Debug Bridge (ADB). Manage your Android devices with ease through an intuitive interface.

## Features

### 🔌 Device Management

- Auto-detection of USB-connected devices
- Wireless ADB connection support
- Multi-device management
- Real-time device status monitoring

### 📱 Screen Mirroring

- **Mirror Device Screen**: View and interact with your Android device from your computer
- **Touch Input**: Control device through mouse clicks and keyboard
- **High Performance**: Low-latency streaming via scrcpy
- **Configurable Quality**: Adjust bitrate and resolution

### 💻 Terminal Emulator

- **Shell Access**: Direct shell command execution on device
- **Command History**: Navigate through previous commands
- **Auto-Complete**: Tab completion for paths and commands
- **Color-Coded Output**: Enhanced readability

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

## ✨ Features

### 📱 Device Management

- **Auto-Detection**: Automatically discovers connected Android devices
- **Real-Time Monitoring**: Live device connection/disconnection notifications
- **Wireless ADB**: Connect to devices over WiFi network
- **Multi-Device Support**: Manage multiple devices simultaneously

### 📁 File Manager

- **File Browser**: Navigate device file system with ease
- **File Transfer**: Push/pull files with progress tracking
- **File Operations**: Create folders, delete files, change permissions
- **Batch Operations**: Transfer multiple files at once

### 📦 Application Manager

- **Package Listing**: View all installed apps (user/system)
- **APK Installation**: Install APK files with progress tracking
- **App Control**: Launch, uninstall, enable/disable apps
- **Data Management**: Clear app data and cache
- **Filtering**: Filter by app type and status

### 📋 Logcat Viewer

- **Real-Time Streaming**: Live logcat output with color coding
- **Advanced Filtering**: Filter by log level, tag, or package
- **Log Export**: Save logs to text file
- **Color-Coded Levels**: Easy identification of errors and warnings

### ℹ️ Device Information

- **Hardware Info**: CPU, RAM, screen resolution, battery status
- **System Info**: Android version, SDK level, model, manufacturer
- **Storage Info**: Internal/external storage usage
- **Network Info**: WiFi IP address, MAC address

## 🚀 Installation

### Prerequisites

- Python 3.10 or higher
- Android Debug Bridge (ADB) installed
- USB debugging enabled on Android device

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Application

```bash
python src/main.py
```

## 📖 Usage

### Connecting a Device

#### USB Connection

1. Enable USB debugging on your Android device
2. Connect device via USB cable
3. Accept the USB debugging authorization prompt
4. Device will appear in the device selector

#### Wireless Connection

1. Go to **Tools** → **Wireless Connection**
2. Enter device IP address and port (default: 5555)
3. Click **Connect**

### File Operations

1. Select **Files** tab
2. Navigate using the path bar or double-click folders
3. **Push File**: Click "Push File" to upload from computer
4. **Pull File**: Select file and click "Pull File" to download
5. **Delete**: Select item and click "Delete"
6. **New Folder**: Click "New Folder" to create directory

### Managing Applications

1. Select **Apps** tab
2. Use filter dropdown to show specific app types
3. **Install APK**: Click "Install APK" and select file
4. **Uninstall**: Select app and click "Uninstall"
5. **Launch**: Select app and click "Launch"
6. **Clear Data**: Select app and click "Clear Data"

### Viewing Logs

1. Select **Logcat** tab
2. Click **Start** to begin streaming logs
3. Use filters to narrow down log output:
   - **Level**: Filter by log level (V, D, I, W, E, F)
   - **Tag**: Filter by log tag
   - **Package**: Filter by package name
4. Click **Export** to save logs to file

### Device Information

1. Select **Info** tab
2. View comprehensive device information
3. Click **Refresh Info** to update data

## 🏗️ Project Structure

```
ADB Manager/
├── src/
│   ├── main.py                 # Application entry point
│   ├── config.py               # Configuration manager
│   ├── utils/
│   │   ├── adb_wrapper.py      # ADB command wrapper
│   │   ├── logger.py           # Logging configuration
│   │   └── crypto.py           # Credential encryption
│   ├── core/
│   │   ├── device_manager.py   # Device detection & monitoring
│   │   ├── file_manager.py     # File operations
│   │   ├── app_manager.py      # Application management
│   │   └── logcat_streamer.py  # Logcat streaming
│   └── gui/
│       ├── main_window.py      # Main application window
│       ├── widgets/
│       │   ├── file_explorer.py
│       │   ├── app_list.py
│       │   ├── logcat_viewer.py
│       │   └── device_info.py
│       └── dialogs/
│           └── wireless_dialog.py
├── requirements.txt
├── setup.py
└── README.md
```

## 🛠️ Technology Stack

- **Framework**: PySide6 (Qt for Python)
- **Async**: asyncio + qasync for non-blocking operations
- **ADB**: Android Debug Bridge integration
- **Encryption**: cryptography (Fernet) for credentials
- **Logging**: Python logging with rotating file handler

## 📋 Requirements

See `requirements.txt` for complete list:

- PySide6 >= 6.6.0
- qasync >= 0.24.0
- aiofiles >= 23.2.1
- cryptography >= 41.0.0
- And more...

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👤 Author

**Galkurta**

## 🙏 Acknowledgments

- Android Debug Bridge (ADB) by Google
- PySide6 by The Qt Company
- All open-source contributors

## 📝 Development Status

### ✅ Completed Features

- Device detection and monitoring
- File manager with transfer capabilities
- Application manager with APK installation
- Logcat viewer with filtering
- Device information display
- Wireless ADB connection
- Configuration persistence
- Screen mirroring (scrcpy integration)
- Terminal emulator with shell access

### 🚧 Planned Features

- Dark/Light theme toggle
- Backup/restore functionality
- Screenshot/screen recording
- Unit tests
- Auto-update mechanism

## 📞 Support

For issues and feature requests, please use the GitHub issue tracker.

---

**Made with ❤️ using Python and PySide6**

- Inspired by [scrcpy](https://github.com/Genymobile/scrcpy)
