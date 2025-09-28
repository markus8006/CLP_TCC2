import threading


from src.views import create_app
from src.utils.network.discovery import discovery_background_once


from src.utils.log.log import setup_logger

logger = setup_logger()

app = create_app()


if __name__ == "__main__":

    
    t = threading.Thread(target=discovery_background_once, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
