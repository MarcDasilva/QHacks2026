import psycopg2
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

def validate_connection_string_format(db_url):
    if not db_url:
        return False, None, "DATABASE_URL is empty"
    
    parsed = urlparse(db_url)
    hostname = parsed.hostname
    
    if not hostname:
        return False, None, "Could not extract hostname from DATABASE_URL"
    
    # Accept both direct database URLs (.supabase.co) and connection pooling URLs (pooler.supabase.com)
    is_supabase_url = (
        hostname.endswith('.supabase.co') or 
        hostname.endswith('.pooler.supabase.com') or
        'pooler.supabase.com' in hostname
    )
    if not is_supabase_url:
        return False, hostname, f"Hostname '{hostname}' doesn't appear to be a Supabase URL"
    
    if not parsed.username:
        return False, hostname, "Username is missing from connection string"
    
    if not parsed.password:
        return False, hostname, "Password is missing from connection string"
    
    return True, hostname, None

def get_conn():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    # Validate connection string format (but don't check DNS - let psycopg2 handle it)
    is_valid, hostname, error_msg = validate_connection_string_format(db_url)
    
    if not is_valid:
        print(f"\n[ERROR] Connection String Format Invalid:")
        print(f"   {error_msg}")
        print(f"\n[INFO] Expected formats:")
        print(f"   Direct: postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres")
        print(f"   Pooling: postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres")
        print(f"\n[INFO] Note: If your password contains special characters, you may need to URL-encode them")
        raise ValueError(f"Invalid connection string format: {error_msg}")
    
    try:
        return psycopg2.connect(db_url)
    except psycopg2.OperationalError as e:
        error_str = str(e)
        print(f"\n[ERROR] Connection Error: {e}")
        print(f"\n[TROUBLESHOOTING]")
        
        if "could not translate host name" in error_str.lower() or "name or service not known" in error_str.lower():
            print("DNS Resolution Failed")
            if hostname:
                print(f"Current hostname: {hostname}")
        elif "password authentication failed" in error_str.lower():
            print("Authentication Failed - Password is incorrect")
        elif "timeout" in error_str.lower():
            print("Connection Timeout - Network or firewall issue")
        else:
            print("Verify the DATABASE_URL in your .env file is correct")
            if hostname:
                print("Check if the Supabase project '{hostname}' exists and is active")
        raise

if __name__ == "__main__":
    try:
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            parsed = urlparse(db_url)
            print("[INFO] Connection string details:")
            print(f"   Hostname: {parsed.hostname}")
            print(f"   Port: {parsed.port or '5432 (default)'}")
            print(f"   Database: {parsed.path.lstrip('/') if parsed.path else 'N/A'}")
            print(f"   Username: {parsed.username or 'N/A'}")
            print(f"   Password: {'***' if parsed.password else 'Not set'}")
            print()
        
        print("[INFO] Attempting to connect to database...")
        conn = get_conn()
        print("[SUCCESS] Successfully connected to database!")
        
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        result = cursor.fetchone()
        print(f"[SUCCESS] Test query result: {result}")
        
        conn.close()
        print("[SUCCESS] Connection closed.")
    except ValueError as e:
        print(f"\n[ERROR] Configuration Error: {e}")
        exit(1)
    except Exception as e:
        print(f"\n[ERROR] Failed to connect: {e}")