#!/bin/bash
# ChromaDB Management Script
# Usage: ./scripts/manage_chromadb.sh {status|clean|help}

# Configuration
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Find Python executable
find_python() {
  if [ -f "$WORKSPACE_DIR/venv/bin/python" ]; then
    echo "$WORKSPACE_DIR/venv/bin/python"
  elif [ -n "$VIRTUAL_ENV" ]; then
    echo "$VIRTUAL_ENV/bin/python"
  elif command -v python3 > /dev/null 2>&1; then
    echo "python3"
  elif command -v python > /dev/null 2>&1; then
    echo "python"
  else
    echo "Python not found. Please install Python or activate your virtual environment."
    exit 1
  fi
}

PYTHON_CMD=$(find_python)
echo "Using Python: $PYTHON_CMD"

# Print help
show_help() {
  echo "ChromaDB Management Script"
  echo ""
  echo "Usage: ./scripts/manage_chromadb.sh {command}"
  echo ""
  echo "Commands:"
  echo "  status         Get information about ChromaDB contents and statistics"
  echo "  clean          Reset and clean ChromaDB collections"
  echo "  help           Show this help message"
  echo ""
  echo "Examples:"
  echo "  ./scripts/manage_chromadb.sh status     # Show detailed ChromaDB statistics"
  echo "  ./scripts/manage_chromadb.sh clean      # Clean ChromaDB collections with confirmation"
}

# Get ChromaDB status
get_status() {
  echo "Checking ChromaDB status..."
  cd "$WORKSPACE_DIR"
  
  $PYTHON_CMD -c "
import os
from chromadb import PersistentClient
from config.feature_flags import CHROMADB_PERSIST_DIRECTORY, ENABLE_NEWS_EMBEDDINGS, USE_CHROMADB_CACHING
import logging

# Disable excessive logging
logging.getLogger('chromadb').setLevel(logging.ERROR)

print(f'\\nChromaDB configuration:')
print(f'  CHROMADB_PERSIST_DIRECTORY: {CHROMADB_PERSIST_DIRECTORY}')
print(f'  ENABLE_NEWS_EMBEDDINGS: {ENABLE_NEWS_EMBEDDINGS}')
print(f'  USE_CHROMADB_CACHING: {USE_CHROMADB_CACHING}')

if not ENABLE_NEWS_EMBEDDINGS or not USE_CHROMADB_CACHING:
    print('\\nWARNING: ChromaDB is currently disabled in feature flags!')

if not os.path.exists(CHROMADB_PERSIST_DIRECTORY):
    print(f'\\nChromaDB directory does not exist at: {CHROMADB_PERSIST_DIRECTORY}')
    exit(0)

print(f'\\nChromaDB directory exists at: {CHROMADB_PERSIST_DIRECTORY}')
print(f'Directory size: {sum(os.path.getsize(os.path.join(root, file)) for root, dirs, files in os.walk(CHROMADB_PERSIST_DIRECTORY) for file in files) / (1024*1024):.2f} MB')

try:
    client = PersistentClient(path=CHROMADB_PERSIST_DIRECTORY)
    
    # In v0.6.0, list_collections() returns only names
    collection_names = client.list_collections()
    print(f'\\nFound {len(collection_names)} collections:')
    
    total_embeddings = 0
    
    for name in collection_names:
        try:
            # Get the actual collection object
            collection = client.get_collection(name=name)
            count = collection.count()
            total_embeddings += count
            print(f'  - {name}: {count} embeddings')
            
            # Sample a few items to show their IDs (if available)
            if count > 0:
                sample = collection.get(limit=5, include=['documents'])
                print(f'    Sample IDs: {sample[\"ids\"][:3]}...')
                if 'documents' in sample and sample['documents']:
                    # Show first few characters of first document
                    first_doc = sample['documents'][0]
                    preview = first_doc[:100] + '...' if len(first_doc) > 100 else first_doc
                    print(f'    Document preview: {preview}')
        except Exception as e:
            print(f'  - {name}: Error getting collection details - {str(e)}')
    
    print(f'\\nTotal embeddings across all collections: {total_embeddings}')
    
except Exception as e:
    print(f'\\nError connecting to ChromaDB: {str(e)}')
"
}

# Clean and reset ChromaDB
clean_chromadb() {
  echo "This will COMPLETELY ERASE all ChromaDB collections and data."
  read -p "Are you sure you want to continue? (y/n): " confirm
  if [[ "$confirm" != [yY]* ]]; then
    echo "Operation cancelled"
    return
  fi
  
  cd "$WORKSPACE_DIR"
  
  $PYTHON_CMD -c "
import os
import shutil
from config.feature_flags import CHROMADB_PERSIST_DIRECTORY

print(f'\\nCleaning ChromaDB at: {CHROMADB_PERSIST_DIRECTORY}')

if not os.path.exists(CHROMADB_PERSIST_DIRECTORY):
    print(f'ChromaDB directory does not exist. Nothing to clean.')
    exit(0)

try:
    # Remove the entire directory
    shutil.rmtree(CHROMADB_PERSIST_DIRECTORY)
    print(f'Successfully removed ChromaDB directory')
    
    # Create an empty directory to ensure it exists for future use
    os.makedirs(CHROMADB_PERSIST_DIRECTORY, exist_ok=True)
    print(f'Created empty ChromaDB directory')
    
    print(f'\\nChromaDB has been reset successfully!')
except Exception as e:
    print(f'Error cleaning ChromaDB: {str(e)}')
"
}

# Main script logic
case "$1" in
  status)
    get_status
    ;;
  clean)
    clean_chromadb
    ;;
  help|--help|-h)
    show_help
    ;;
  *)
    echo "Unknown command: $1"
    echo ""
    show_help
    exit 1
    ;;
esac

exit 0 