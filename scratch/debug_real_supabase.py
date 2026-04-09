import os
from supabase import create_client
from dotenv import load_dotenv

# Cargar variables del backend
load_dotenv('backend/.env')

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Necesitamos service role para ver triggers/auth

if not key:
    print("❌ Falta SUPABASE_SERVICE_ROLE_KEY en el .env. Usando anon key para lectura básica...")
    key = os.environ.get("SUPABASE_ANON_KEY")

supabase = create_client(url, key)

def debug_database():
    print(f"--- 🔍 Debugging Supabase: {url} ---")
    
    # 1. Ver tablas y registros recientes
    try:
        users = supabase.table("users").select("id, auth_user_id, email, telegram_id, nombre").order("created_at", desc=True).limit(5).execute()
        print(f"\n✅ Ultimos 5 usuarios en public.users:")
        for u in users.data:
            print(f"  - ID: {u['id']}, Auth: {u['auth_user_id']}, Email: {u['email']}, Telegram: {u['telegram_id']}, Nombre: {u['nombre']}")
    except Exception as e:
        print(f"❌ Error leyendo public.users: {e}")

    # 2. Ver si existen duplicados por email
    try:
        query = """
        SELECT email, count(*) 
        FROM public.users 
        WHERE email IS NOT NULL 
        GROUP BY email 
        HAVING count(*) > 1;
        """
        # Como no puedo ejecutar SQL crudo fácil desde acá sin un rpc, solo informamos
        print("\n⚠️ Sugerencia: Revisa en tu SQL Editor si hay duplicados por email.")
    except:
        pass

if __name__ == "__main__":
    debug_database()
