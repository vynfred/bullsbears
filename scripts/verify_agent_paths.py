#!/usr/bin/env python3
"""
Verify all agent prompt paths are correct
"""
import os
from pathlib import Path

# Define expected structure (NEW: separated by infrastructure)
AGENTS = {
    "screen_agent.py": {
        "location": "backend/app/services/runpod_agents/screen_agent.py",
        "prompts": ["screen_prompt.txt", "weights.json"],
        "path_pattern": "Path(__file__).parent.parent / 'prompts'"
    },
    "learner_agent.py": {
        "location": "backend/app/services/runpod_agents/learner_agent.py",
        "prompts": ["learner_prompt.txt", "weights.json", "arbitrator_bias.json"],
        "path_pattern": "Path(__file__).parent.parent / 'prompts'"
    },
    "vision_agent.py": {
        "location": "backend/app/services/cloud_agents/vision_agent.py",
        "prompts": ["vision_prompt.txt"],
        "path_pattern": "Path(__file__).parent.parent / 'prompts'"
    },
    "social_agent.py": {
        "location": "backend/app/services/cloud_agents/social_agent.py",
        "prompts": ["social_prompt.txt"],
        "path_pattern": "Path(__file__).parent.parent / 'prompts'"
    },
    "arbitrator_agent.py": {
        "location": "backend/app/services/cloud_agents/arbitrator_agent.py",
        "prompts": ["arbitrator_prompt.txt", "arbitrator_bias.json"],
        "path_pattern": "Path(__file__).parent.parent / 'prompts'"
    }
}

PROMPT_DIR = "backend/app/services/prompts"

def verify_paths():
    print("🔍 AGENT PATH VERIFICATION\n")
    print("=" * 60)
    
    all_good = True
    
    # Check all agents exist
    for agent_name, config in AGENTS.items():
        agent_path = config["location"]
        print(f"\n📄 {agent_name}")
        print(f"   Location: {agent_path}")
        
        if not os.path.exists(agent_path):
            print(f"   ❌ Agent file not found!")
            all_good = False
            continue
        else:
            print(f"   ✅ Agent file exists")
        
        # Simulate path resolution
        agent_dir = os.path.dirname(agent_path)
        print(f"   Path pattern: {config['path_pattern']}")
        
        # Check each prompt file
        for prompt_file in config["prompts"]:
            # All agents now use parent.parent / 'prompts'
            # So from runpod_agents/ or cloud_agents/, go up to services/, then into prompts/
            services_dir = os.path.dirname(agent_dir)
            resolved_path = os.path.join(services_dir, "prompts", prompt_file)
            
            if os.path.exists(resolved_path):
                print(f"   ✅ {prompt_file} → {resolved_path}")
            else:
                print(f"   ❌ {prompt_file} NOT FOUND at {resolved_path}")
                all_good = False
    
    # Check all prompt files exist
    print(f"\n\n📁 PROMPT DIRECTORY: {PROMPT_DIR}")
    print("=" * 60)
    
    if not os.path.exists(PROMPT_DIR):
        print(f"❌ Prompt directory not found!")
        return False
    
    prompt_files = os.listdir(PROMPT_DIR)
    print(f"Found {len(prompt_files)} files:")
    for f in sorted(prompt_files):
        print(f"   ✅ {f}")
    
    print("\n" + "=" * 60)
    if all_good:
        print("✅ ALL PATHS VERIFIED SUCCESSFULLY!")
    else:
        print("❌ SOME PATHS ARE BROKEN - SEE ABOVE")
    
    return all_good

if __name__ == "__main__":
    success = verify_paths()
    exit(0 if success else 1)

