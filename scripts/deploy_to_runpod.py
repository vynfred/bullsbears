#!/usr/bin/env python3

"""
BullsBears AI - RunPod Deployment Script
Deploys the complete multi-agent system to RunPod
"""

import os
import sys
import json
import time
import requests
from pathlib import Path

# RunPod API configuration
RUNPOD_API_KEY = os.getenv('RUNPOD_API')
RUNPOD_API_BASE = "https://api.runpod.ai/graphql"

def create_runpod_instance():
    """Create a new RunPod instance with our configuration"""
    
    if not RUNPOD_API_KEY:
        print("❌ RUNPOD_API key not found in environment")
        return None
    
    # GraphQL mutation to create pod
    mutation = """
    mutation {
        podFindAndDeployOnDemand(
            input: {
                cloudType: SECURE
                gpuCount: 1
                volumeInGb: 50
                containerDiskInGb: 100
                minVcpuCount: 16
                minMemoryInGb: 96
                gpuTypeId: "NVIDIA RTX 6000 Ada Generation"
                name: "bullsbears-ai-agents"
                imageName: "runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04"
                dockerArgs: ""
                ports: "11434/http,8000/http"
                volumeMountPath: "/workspace"
                env: [
                    {key: "OLLAMA_HOST", value: "0.0.0.0:11434"},
                    {key: "OLLAMA_MODELS", value: "/workspace/models"},
                    {key: "PYTHONPATH", value: "/workspace/bullsbears"}
                ]
            }
        ) {
            id
            imageName
            env
            machineId
            machine {
                podHostId
            }
        }
    }
    """
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {RUNPOD_API_KEY}"
    }
    
    response = requests.post(
        RUNPOD_API_BASE,
        json={"query": mutation},
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        if 'errors' in data:
            print(f"❌ RunPod API Error: {data['errors']}")
            return None
        
        pod_data = data['data']['podFindAndDeployOnDemand']
        print(f"✅ RunPod instance created: {pod_data['id']}")
        return pod_data
    else:
        print(f"❌ Failed to create RunPod instance: {response.status_code}")
        return None

def wait_for_pod_ready(pod_id):
    """Wait for pod to be ready"""
    print(f"⏳ Waiting for pod {pod_id} to be ready...")
    
    query = f"""
    query {{
        pod(input: {{podId: "{pod_id}"}}) {{
            id
            name
            runtime {{
                uptimeInSeconds
                ports {{
                    ip
                    isIpPublic
                    privatePort
                    publicPort
                    type
                }}
            }}
        }}
    }}
    """
    
    headers = {
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {RUNPOD_API_KEY}"
    }
    
    for i in range(60):  # Wait up to 10 minutes
        response = requests.post(
            RUNPOD_API_BASE,
            json={"query": query},
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            pod = data['data']['pod']
            
            if pod and pod['runtime'] and pod['runtime']['uptimeInSeconds'] > 0:
                print(f"✅ Pod is ready! Uptime: {pod['runtime']['uptimeInSeconds']}s")
                return pod
        
        print(f"⏳ Still waiting... ({i+1}/60)")
        time.sleep(10)
    
    print("❌ Pod failed to become ready within 10 minutes")
    return None

def upload_agent_system(pod_info):
    """Upload our agent system to the pod"""
    print("📤 Uploading BullsBears agent system...")
    
    # Get pod connection info
    ports = pod_info['runtime']['ports']
    ssh_port = None
    
    for port in ports:
        if port['privatePort'] == 22:
            ssh_port = port['publicPort']
            break
    
    if not ssh_port:
        print("❌ SSH port not found")
        return False
    
    # For now, we'll provide instructions for manual upload
    print("📋 Manual upload instructions:")
    print(f"   1. Connect to pod via Jupyter/Terminal")
    print(f"   2. Run the setup script")
    print(f"   3. Upload agent files")
    
    return True

def main():
    """Main deployment function"""
    print("🚀 BullsBears AI - RunPod Deployment")
    print("====================================")
    
    # Create RunPod instance
    pod_data = create_runpod_instance()
    if not pod_data:
        sys.exit(1)
    
    pod_id = pod_data['id']
    
    # Wait for pod to be ready
    pod_info = wait_for_pod_ready(pod_id)
    if not pod_info:
        sys.exit(1)
    
    # Upload agent system
    if upload_agent_system(pod_info):
        print("✅ Deployment complete!")
        print(f"🌐 Pod ID: {pod_id}")
        print("📋 Next steps:")
        print("   1. Access pod via RunPod dashboard")
        print("   2. Run setup script")
        print("   3. Test agent system")
    else:
        print("❌ Deployment failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
