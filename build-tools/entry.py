"""The script PyInstaller freezes into LibrePhoneCam.exe.

Running from source goes through run.bat / run.sh instead.
"""

import sys
from pathlib import Path

# Frozen builds resolve this through the bundle; a plain run needs the repo
# root on the path because this file lives one level down.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from librephonecam.gui import main  # noqa: E402

if __name__ == "__main__":
    main()
