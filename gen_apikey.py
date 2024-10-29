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
            "uid": "teamstools",
            "appid": "teamstools",
            "expire_time": (datetime.now() + timedelta(days=10000)).strftime("%Y-%m-%d %H:%M:%S"),
            "level": "teamstools",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        api_secret,
        algorithm="HS256",
    )
    print(s)

