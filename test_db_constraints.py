import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import uuid
import pathlib

env_path = pathlib.Path("backend/.env").resolve()
print("Env path:", env_path)
load_dotenv(env_path)

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

if not supabase_url or not supabase_key:
    print("No supabase credentials found in .env")
else:
    supabase: Client = create_client(supabase_url, supabase_key)
    test_id = str(uuid.uuid4())
    test_email = "test.bugfix2@test.com"
    test_name = "Test Name2"
    
    try:
        print("Inserting into usuarios...")
        try:
            res = supabase.table('usuarios').insert({
                "id": test_id,
                "email": test_email,
                "nombre": test_name,
                "rol": "usuario"
            }).execute()
            print("OK usuarios")
        except Exception as e:
            print(f"ERROR usuarios: {e.__class__.__name__}: {str(e)}")
            
        print("Inserting into users...")
        try:
            res = supabase.table('users').insert({
                "auth_user_id": test_id,
                "email": test_email,
                "nombre": test_name,
                "presupuesto_mensual": 1000
            }).execute()
            print("OK users")
        except Exception as e:
            print(f"ERROR users: {e.__class__.__name__}: {str(e)}")

        # cleanup
        try:
            supabase.table('users').delete().eq('auth_user_id', test_id).execute()
            supabase.table('usuarios').delete().eq('id', test_id).execute()
        except:
            pass

    except Exception as e:
        print("Fatal error:", e)
