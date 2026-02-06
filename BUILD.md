# Building ADB Manager

This document explains how to build ADB Manager as a standalone executable.

## Prerequisites

- Python 3.10 or higher
- All dependencies installed from `requirements.txt`

## Building Locally

### Install PyInstaller

```bash
pip install pyinstaller
```

### Build Executable

```bash
pyinstaller ADB-Manager.spec
```

The executable will be created in `dist/ADB-Manager/`

### Run

Windows:

```bash
dist\ADB-Manager\ADB-Manager.exe
```

## Automated Builds (GitHub Actions)

The project includes a GitHub Actions workflow that automatically builds and releases the application.

### How it Works

1. **Trigger**: Push a version tag (e.g., `v1.0.0`)

   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **Build Process**:
   - Checks out code
   - Sets up Python 3.10
   - Installs dependencies
   - Builds Windows executable using PyInstaller
   - Creates portable ZIP archive

3. **Release**:
   - Creates GitHub release with the tag
   - Uploads Windows executable ZIP
   - Auto-generates release notes

### Manual Workflow Trigger

You can also manually trigger the build from the GitHub Actions tab without creating a tag.

## Build Configuration

The build is configured in `ADB-Manager.spec` which includes:

- All Python source files
- Resource files (icons, styles, UI)
- Binary dependencies (ADB, scrcpy)
- Hidden imports for Qt and async libraries
- Windows icon

## Troubleshooting

### Missing DLLs

If the executable fails due to missing DLLs, add them to the `binaries` section in `ADB-Manager.spec`.

### Import Errors

Add missing modules to `hiddenimports` list in `ADB-Manager.spec`.

### Large File Size

The executable includes the full Python runtime and all dependencies. This is normal for PyInstaller builds.

To reduce size:

- Remove unused dependencies from `requirements.txt`
- Use `--exclude-module` flag for unnecessary modules
