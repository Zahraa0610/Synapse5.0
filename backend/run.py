import os
import sys

# `python run.py --demo` starts in demo mode: fictional data + quick-login buttons.
if "--demo" in sys.argv:
    os.environ["MAAK_DEMO"] = "1"

from app import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
