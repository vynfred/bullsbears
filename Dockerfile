FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl wget git postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.ai/install.sh | sh

# Set working directory
WORKDIR /workspace

# Copy deployment package
COPY bullsbears_runpod_deployment.zip /workspace/
RUN unzip bullsbears_runpod_deployment.zip && rm bullsbears_runpod_deployment.zip

# Install Python dependencies
COPY requirements.txt /workspace/
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install runpod

# Copy handler
COPY runpod_handler.py /workspace/

# Set environment variables
ENV OLLAMA_HOST=0.0.0.0:11434
ENV PYTHONPATH=/workspace

# Expose ports
EXPOSE 11434 8000

# Start script
COPY start.sh /workspace/
RUN chmod +x /workspace/start.sh

CMD ["/workspace/start.sh"]
