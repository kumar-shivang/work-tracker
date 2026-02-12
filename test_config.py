import sys
sys.path.insert(0, '/home/shivang/n8n')

from app.config import Config
from dotenv import load_dotenv
import os

print("=== Checking Config.GITHUB_TOKEN ===")
print(f"Config.GITHUB_TOKEN present: {bool(Config.GITHUB_TOKEN)}")
if Config.GITHUB_TOKEN:
    print(f"Length: {len(Config.GITHUB_TOKEN)}")
    print(f"Prefix: {Config.GITHUB_TOKEN[:4]}...")

print("\n=== Checking .env directly ===")
load_dotenv(override=True)
direct_token = os.getenv("GITHUB_TOKEN")
print(f"Direct token present: {bool(direct_token)}")
if direct_token:
    print(f"Length: {len(direct_token)}")
    print(f"Prefix: {direct_token[:4]}...")

print("\n=== Are they the same? ===")
print(f"Match: {Config.GITHUB_TOKEN == direct_token}")
