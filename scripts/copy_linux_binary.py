#!/usr/bin/env python3
"""Copy built binary to /opt/bin with permission check."""
import os
import shutil
import sys


def main():
    source = "dist/mgit"
    dest = "/opt/bin/mgit"

    # Check if build output exists
    if not os.path.exists(source):
        print("ERROR: Build failed - dist/mgit not found")
        sys.exit(1)

    # Check write permission to destination
    dest_dir = os.path.dirname(dest)
    if os.access(dest_dir, os.W_OK):
        try:
            shutil.copy2(source, dest)
            os.chmod(dest, 0o755)
            print(f"✓ Successfully copied mgit to {dest}")
        except Exception as e:
            print(f"ERROR: Failed to copy: {e}")
            sys.exit(1)
    else:
        print(f"INFO: Cannot copy to {dest_dir} - no write permission")
        print(f"      You can manually copy: sudo cp {source} {dest}")


if __name__ == "__main__":
    main()
