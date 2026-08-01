from dotenv import load_dotenv
import os

# Load variables from the .env file
load_dotenv()

GW2_API_KEY = os.getenv("GW2_API_KEY")