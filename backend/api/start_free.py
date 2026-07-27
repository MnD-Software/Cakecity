"""Start the API and worker together on a single free Render web instance.

This is intentionally a small-instance deployment mode. Paid environments should
run ``app.worker`` as the separate worker declared in ``render.yaml``.
"""

import os
import subprocess
import sys


def main() -> None:
    subprocess.run([sys.executable, "migrate.py"], check=True)
    subprocess.Popen([sys.executable, "-m", "app.worker"])
    port = os.environ.get("PORT", "10000")
    os.execvp(
        "uvicorn",
        [
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            port,
            "--proxy-headers",
        ],
    )


if __name__ == "__main__":
    main()
