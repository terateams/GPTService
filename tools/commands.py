from common import generate_api_key
from dotenv import load_dotenv
import os

load_dotenv()

if __name__ == "__main__":
    api_secret = os.environ.get("API_SECRET")
    print(generate_api_key(api_secret))
    print(generate_api_key("myapikey"))



