
import os
import sys
import re
import subprocess
import shutil
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
MAIN_FILE = PROJECT_ROOT / "src" / "main.py"

def run_command(command, cwd=None, exit_on_error=True):
    """Run a shell command."""
    print(f"Running: {command}")
    try:
        result = subprocess.run(
            command,
            cwd=cwd or PROJECT_ROOT,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            print(result.stdout)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}")
        print(e.stderr)
        if exit_on_error:
            sys.exit(1)
        raise e

def get_current_version():
    """Extract version from main.py."""
    content = MAIN_FILE.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    if match:
        return match.group(1)
    print(f"Error: Could not find __version__ in {MAIN_FILE}")
    sys.exit(1)

def update_version(new_version):
    """Update version in main.py."""
    content = MAIN_FILE.read_text(encoding="utf-8")
    new_content = re.sub(
        r'__version__\s*=\s*"[^"]+"',
        f'__version__ = "{new_version}"',
        content
    )
    MAIN_FILE.write_text(new_content, encoding="utf-8")
    print(f"Updated {MAIN_FILE} to version {new_version}")

def bump_version(current_version, part="patch"):
    """Bump version string."""
    major, minor, patch = map(int, current_version.split("."))
    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    else:
        patch += 1
    return f"{major}.{minor}.{patch}"

def git_sync():
    """Sync with remote."""
    print("\n--- Syncing with Remote ---")
    run_command("git pull origin HEAD")
    print("Sync complete.")

def main():
    print("=== ADB Manager Release Helper ===")
    
    # Check for arguments
    if len(sys.argv) > 1 and sys.argv[1] == "sync":
        git_sync()
        return

    # 0. Sync first?
    if input("Sync with remote first? (y/N): ").lower() == 'y':
        git_sync()

    # 1. Get current version
    current_version = get_current_version()
    print(f"\nCurrent Version: {current_version}")
    
    # 2. Determine new version
    next_patch = bump_version(current_version, "patch")
    next_minor = bump_version(current_version, "minor")
    next_major = bump_version(current_version, "major")
    
    print(f"1. Patch ({next_patch})")
    print(f"2. Minor ({next_minor})")
    print(f"3. Major ({next_major})")
    print("4. Custom")
    
    choice = input("\nSelect version bump (default 1): ").strip() or "1"
    
    if choice == "1":
        new_version = next_patch
    elif choice == "2":
        new_version = next_minor
    elif choice == "3":
        new_version = next_major
    else:
        new_version = input("Enter custom version: ").strip()
        if not re.match(r"^\d+\.\d+\.\d+$", new_version):
            print("Invalid version format (X.Y.Z)")
            sys.exit(1)
            
    print(f"\nPreparing to release v{new_version}...")
    if input("Continue? (Y/n): ").lower() == 'n':
        print("Aborted.")
        sys.exit(0)

    # 3. Update File
    update_version(new_version)
    
    # 4. Commit and Tag
    run_command(f'git add "{MAIN_FILE}"')
    run_command(f'git commit -m "Bump version to v{new_version}"')
    
    # Check if tag exists (should not happened if we synced but safer)
    try:
        run_command(f"git rev-parse v{new_version}", exit_on_error=False)
        print(f"Warning: Tag v{new_version} already exists locally.")
    except:
        pass # Good, tag doesn't exist
        
    run_command(f"git tag v{new_version}")
    
    # 5. Push
    print("\n--- Pushing to Remote ---")
    if input(f"Push commit and tag v{new_version}? (Y/n): ").lower() != 'n':
        run_command("git push origin HEAD")
        run_command(f"git push origin v{new_version}")
        print("\nRelease Pushed! GitHub Actions should start building now.")
    else:
        print("\nChanges committed locally but not pushed.")

if __name__ == "__main__":
    main()
