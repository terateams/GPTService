import jwt
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os
import sys

load_dotenv()

if __name__ == "__main__":
    api_secret = os.environ.get("API_SECRET")
    s = jwt.encode(
        {
            "uid": "gptservice",
            "appid": "gptservice",
            "expire_time": (datetime.now() + timedelta(days=1000)).strftime("%Y-%m-%d %H:%M:%S"),
            "level": "gptservice",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        api_secret,
        algorithm="HS256",
    )
    print(s)

