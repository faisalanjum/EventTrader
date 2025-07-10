FROM python:3.11-slim

# Set working directory
WORKDIR /source

# NOTE: Build this from the mcp-neo4j-cypher directory:
# cd /home/faisal/neo4j-mcp-server/servers/mcp-neo4j-cypher
# docker build -f /home/faisal/EventMarketDB/k8s/mcp-services/Dockerfile.cypher -t faisalanjum/mcp-neo4j-cypher:latest .

# Copy all source files
COPY . /source/

# Install dependencies
RUN pip install --no-cache-dir 'neo4j>=5.26.0' 'mcp[cli]>=1.6.0' && \
    cd /source && \
    pip install -e .

# Keep container running for kubectl exec
CMD ["sleep", "infinity"]