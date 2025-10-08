import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Disable any system proxies
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""

# Hugging Face API key
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
if not HUGGINGFACE_API_KEY:
    print("❌ HUGGINGFACE_API_KEY not set!")
    exit(1)
else:
    print("✅ HUGGINGFACE_API_KEY loaded successfully")

# Use a public smaller/faster model to test
API_URL = "https://api-inference.huggingface.co/models/sshleifer/distilbart-cnn-12-6"
# You can switch back to facebook/bart-large-cnn later if needed

headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}

# Sample text to summarize
payload = {"inputs": "who is pm of India?"}

try:
    response = requests.post(
        API_URL,
        headers=headers,
        json=payload,
        timeout=120,  # increased from 30s to 120s
        proxies={"http": None, "https": None}  # Disable proxies for this request
    )
    response.raise_for_status()
    data = response.json()
    print("✅ API call successful!")
    print("Response:", data)
except requests.exceptions.HTTPError as e:
    print(f"❌ API call failed: {e}")
except requests.exceptions.ReadTimeout as e:
    print(f"❌ API call timed out: {e}")
except Exception as e:
    print(f"❌ Other error: {e}")
