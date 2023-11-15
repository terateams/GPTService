from dotenv import load_dotenv
import os
load_dotenv()

from apps.apps import app


DATA_DIR = os.environ.get("DATA_DIR", "/data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

webport = int(os.environ.get("WEB_PORT", 8700))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=webport)
