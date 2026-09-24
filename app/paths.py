"""Resolves where the app's data file and output folder live.

Both must live next to the executable/script, not inside a bundled
package, so the data survives app updates and is easy for staff to
back up or move.
"""
import os
import sys


def base_dir() -> str:
    if getattr(sys, "frozen", False):
        # Running as a PyInstaller-built .exe
        return os.path.dirname(sys.executable)
    # Running from source: project root is one level above app/
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_file_path() -> str:
    return os.path.join(base_dir(), "data", "dttc_data.json")


def output_dir() -> str:
    path = os.path.join(base_dir(), "Generated Papers")
    os.makedirs(path, exist_ok=True)
    return path
