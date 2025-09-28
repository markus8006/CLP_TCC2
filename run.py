from src.views import create_app



from src.utils.log.log import setup_logger

logger = setup_logger()

app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
