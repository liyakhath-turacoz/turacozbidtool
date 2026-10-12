import uvicorn

from backend.main import app, logger


if __name__ == "__main__":
    logger.info("Starting backend API at http://127.0.0.1:8000")
    logger.info("Start the React web app separately from the web/ directory.")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
