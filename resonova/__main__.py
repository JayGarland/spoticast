import threading
import time
import webbrowser

import uvicorn

from resonova.config import settings


def main():
    host = settings.host
    port = settings.port

    def open_browser():
        time.sleep(1.0)
        webbrowser.open(f"http://127.0.0.1:{port}")

    t = threading.Thread(target=open_browser, daemon=True)
    t.start()

    uvicorn.run(
        "resonova.server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
