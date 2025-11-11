#!/bin/bash
# Load environment and run deployment

# Load .env file
set -a
source .env
set +a

# Run deployment
python3 deploy_agents_to_runpod.py