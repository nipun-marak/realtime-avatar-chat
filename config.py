import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyDIy96R6wUVCi9YmXKCWUaH8TxavT3MUn4')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY', 'sk_95f0a6a774bf4447e24f78818c726f3ebab303a7fef5b3c3')

# Database Configuration
DB_NAME = os.getenv('DB_NAME', 'companion.db')

# Application Configuration
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5001))

# Validate required API keys
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is required. Please set it in your .env file.")
if not ELEVENLABS_API_KEY:
    print("Warning: ELEVENLABS_API_KEY not set. Voice features will be disabled.")
