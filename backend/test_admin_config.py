#!/usr/bin/env python3
"""Test script to check admin configuration loading"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

print("=" * 60)
print("ADMIN CONFIGURATION TEST")
print("=" * 60)

print(f"\n📧 ADMIN_EMAIL environment variable: {os.getenv('ADMIN_EMAIL')}")
print(f"🔐 ADMIN_PASSWORD_HASH environment variable: {os.getenv('ADMIN_PASSWORD_HASH')}")

print(f"\n📧 settings.admin_email: {getattr(settings, 'admin_email', 'NOT FOUND')}")
print(f"🔐 settings.admin_password_hash: {getattr(settings, 'admin_password_hash', 'NOT FOUND')}")

print(f"\n✅ hasattr(settings, 'admin_email'): {hasattr(settings, 'admin_email')}")
print(f"✅ hasattr(settings, 'admin_password_hash'): {hasattr(settings, 'admin_password_hash')}")

print("\n" + "=" * 60)

