"""Platform compatibility utilities for mgit."""

import os
import platform
from pathlib import Path


def is_wsl_ntfs_without_metadata(path: Path) -> bool:
    """Detect if *path* is on a Windows NTFS mount inside WSL that lacks chmod support.

    Returns True only when the target is on a drvfs (``/mnt/``) mount under
    WSL **and** ``chmod`` actually fails.  This correctly returns False when
    the user has configured ``[automount] options = "metadata"`` in
    ``/etc/wsl.conf``, on native Windows, macOS, or native Linux.
    """
    if platform.system() != "Linux":
        return False
    try:
        resolved = str(path.resolve())
        if not resolved.startswith("/mnt/"):
            return False
        if Path("/proc/version").read_text().lower().find("microsoft") == -1:
            return False
        # Probe whether chmod actually works on this mount
        import tempfile

        probe = Path(tempfile.mktemp(dir=str(path), prefix=".mgit_probe_"))
        try:
            probe.write_text("")
            os.chmod(str(probe), 0o644)
            return False  # chmod works — metadata is enabled
        except PermissionError:
            return True  # chmod fails — NTFS without metadata
        finally:
            probe.unlink(missing_ok=True)
    except Exception:
        return False
