#!/usr/bin/env python3
"""
Set Admin Password for Hidden Admin Panel
Generates SHA-256 hash for secure password storage
"""

import hashlib
import getpass
import sys

def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def main():
    print("=" * 60)
    print("🔐 BullsBears Admin Password Setup")
    print("=" * 60)
    print()
    print("This will generate a secure password hash for the admin panel.")
    print("The hash will be stored in your .env file.")
    print()
    
    # Get admin email
    admin_email = input("Admin Email (default: admin@bullsbears.xyz): ").strip()
    if not admin_email:
        admin_email = "admin@bullsbears.xyz"
    
    # Get password
    while True:
        password = getpass.getpass("Admin Password (min 12 characters): ")
        if len(password) < 12:
            print("❌ Password must be at least 12 characters long")
            continue
        
        password_confirm = getpass.getpass("Confirm Password: ")
        if password != password_confirm:
            print("❌ Passwords do not match")
            continue
        
        break
    
    # Generate hash
    password_hash = hash_password(password)
    
    print()
    print("✅ Password hash generated successfully!")
    print()
    print("=" * 60)
    print("Add these lines to your backend/.env file:")
    print("=" * 60)
    print()
    print(f"ADMIN_EMAIL={admin_email}")
    print(f"ADMIN_PASSWORD_HASH={password_hash}")
    print()
    print("=" * 60)
    print()
    print("⚠️  IMPORTANT SECURITY NOTES:")
    print("1. Never commit the .env file to git")
    print("2. Keep this password secure - it grants full system access")
    print("3. The admin panel URL is: /admin-control-xyz")
    print("4. This URL is not linked anywhere - keep it secret")
    print()
    print("🚀 After updating .env, restart the backend:")
    print("   cd backend && uvicorn app.main:app --reload")
    print()

if __name__ == "__main__":
    main()

