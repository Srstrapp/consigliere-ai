import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import pathlib

env_path = pathlib.Path("backend/.env").resolve()
load_dotenv(env_path)

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_ANON_KEY")

if supabase_url and supabase_key:
    supabase: Client = create_client(supabase_url, supabase_key)
    try:
        res = supabase.auth.sign_up({
            "email": "test.bugfix234@test.com",
            "password": "Password123!",
            "options": {
                "data": {
                    "full_name": "Test Bugfix"
                }
            }
        })
        print("SIGNUP OK:", res)
    except Exception as e:
        print(f"SIGNUP ERROR: {e.__class__.__name__}: {str(e)}")
