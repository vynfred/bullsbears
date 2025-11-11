#!/usr/bin/env python3
"""
Comprehensive Google Cloud SQL Connection Diagnostics
"""

import os
import asyncio
import asyncpg
import socket
import subprocess
from dotenv import load_dotenv

load_dotenv()

async def test_network_connectivity():
    """Test basic network connectivity to the database host"""
    host = "104.198.40.56"
    port = 5432
    
    print(f"🌐 Testing network connectivity to {host}:{port}")
    
    try:
        # Test if we can reach the host/port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print("✅ Network connectivity: Port is reachable")
            return True
        else:
            print("❌ Network connectivity: Port is not reachable")
            print("   This suggests firewall/network issues")
            return False
            
    except Exception as e:
        print(f"❌ Network test failed: {e}")
        return False

def test_dns_resolution():
    """Test DNS resolution"""
    host = "104.198.40.56"
    print(f"🔍 Testing DNS resolution for {host}")
    
    try:
        import socket
        result = socket.gethostbyaddr(host)
        print(f"✅ DNS resolution: {result}")
        return True
    except Exception as e:
        print(f"⚠️ DNS resolution: {e} (this is often normal for IP addresses)")
        return True  # Not critical for IP addresses

async def test_database_connection_variants():
    """Test different connection string formats"""
    
    variants = [
        {
            "name": "URL-encoded password",
            "url": "postgresql://postgres:%3C%24%3FFh%2AQNNmfJ0vTD@104.198.40.56:5432/postgres"
        },
        {
            "name": "Raw password with escaping",
            "url": "postgresql://postgres:<$?Fh*QNNmfJ0vTD@104.198.40.56:5432/postgres"
        },
        {
            "name": "SSL disabled",
            "url": "postgresql://postgres:%3C%24%3FFh%2AQNNmfJ0vTD@104.198.40.56:5432/postgres?sslmode=disable"
        },
        {
            "name": "SSL required",
            "url": "postgresql://postgres:%3C%24%3FFh%2AQNNmfJ0vTD@104.198.40.56:5432/postgres?sslmode=require"
        }
    ]
    
    for variant in variants:
        print(f"\n🔌 Testing: {variant['name']}")
        try:
            conn = await asyncio.wait_for(
                asyncpg.connect(variant['url']),
                timeout=8.0
            )
            
            print("✅ Connection successful!")
            version = await conn.fetchval("SELECT version()")
            print(f"   PostgreSQL: {version.split(',')[0]}")
            await conn.close()
            return True
            
        except asyncio.TimeoutError:
            print("❌ Connection timeout")
        except Exception as e:
            print(f"❌ Connection failed: {e}")
    
    return False

def check_cloud_sql_proxy():
    """Check if Cloud SQL Proxy is available"""
    print("\n🔧 Checking for Google Cloud SQL Proxy...")
    
    try:
        result = subprocess.run(['cloud_sql_proxy', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ Cloud SQL Proxy found: {result.stdout.strip()}")
            return True
        else:
            print("❌ Cloud SQL Proxy not found")
            return False
    except FileNotFoundError:
        print("❌ Cloud SQL Proxy not installed")
        return False
    except Exception as e:
        print(f"❌ Cloud SQL Proxy check failed: {e}")
        return False

def suggest_solutions():
    """Suggest potential solutions"""
    print("\n" + "="*60)
    print("🔧 POTENTIAL SOLUTIONS:")
    print("="*60)
    
    print("\n1. 🔐 AUTHORIZED NETWORKS:")
    print("   - Go to Google Cloud Console → SQL → bullsbears-prod-db")
    print("   - Click 'Connections' → 'Networking'")
    print("   - Add your IP to 'Authorized networks'")
    print("   - Current IP check: curl ifconfig.me")
    
    print("\n2. 🚀 INSTANCE STATUS:")
    print("   - Verify the instance is RUNNING (not stopped/paused)")
    print("   - Check if it's in 'us-central1' region")
    
    print("\n3. 🔒 SSL REQUIREMENTS:")
    print("   - Try connecting with SSL disabled/required")
    print("   - Check if SSL certificates are needed")
    
    print("\n4. 🌐 CLOUD SQL PROXY (Recommended):")
    print("   - Install: gcloud components install cloud_sql_proxy")
    print("   - Run: cloud_sql_proxy -instances=bullsbears:us-central1:bullsbears-prod-db=tcp:5432")
    print("   - Connect to: localhost:5432")
    
    print("\n5. 🏃‍♂️ RUNPOD DEPLOYMENT (Production Path):")
    print("   - Deploy bootstrap to RunPod infrastructure")
    print("   - Run database operations from cloud environment")

async def main():
    """Run comprehensive diagnostics"""
    print("🔍 GOOGLE CLOUD SQL CONNECTION DIAGNOSTICS")
    print("="*60)
    
    # Test 1: Network connectivity
    network_ok = await test_network_connectivity()
    
    # Test 2: DNS resolution
    dns_ok = test_dns_resolution()
    
    # Test 3: Database connection variants
    if network_ok:
        db_ok = await test_database_connection_variants()
    else:
        print("\n⏭️ Skipping database tests due to network issues")
        db_ok = False
    
    # Test 4: Cloud SQL Proxy availability
    proxy_available = check_cloud_sql_proxy()
    
    # Summary
    print("\n" + "="*60)
    print("📊 DIAGNOSTIC SUMMARY:")
    print("="*60)
    print(f"Network Connectivity: {'✅' if network_ok else '❌'}")
    print(f"DNS Resolution: {'✅' if dns_ok else '❌'}")
    print(f"Database Connection: {'✅' if db_ok else '❌'}")
    print(f"Cloud SQL Proxy: {'✅' if proxy_available else '❌'}")
    
    if db_ok:
        print("\n🎉 DATABASE CONNECTION WORKING!")
        print("✅ Ready to proceed with migrations and bootstrap")
    else:
        suggest_solutions()

if __name__ == "__main__":
    asyncio.run(main())
