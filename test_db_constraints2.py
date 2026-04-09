import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import uuid
import pathlib

env_path = pathlib.Path("backend/.env").resolve()
load_dotenv(env_path)

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_ANON_KEY")

if supabase_url and supabase_key:
    supabase: Client = create_client(supabase_url, supabase_key)
    test_id = str(uuid.uuid4())
    test_name = "Test Name2"
    
    try:
        res = supabase.table('users').insert({
            "auth_user_id": test_id,
            "nombre": test_name,
            "presupuesto_mensual": 1000
        }).execute()
        print("OK users:", res.data)
        supabase.table('users').delete().eq('auth_user_id', test_id).execute()
    except Exception as e:
        print(f"ERROR users: {e.__class__.__name__}: {str(e)}")
