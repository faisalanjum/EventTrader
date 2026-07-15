#!/usr/bin/env python3
"""Simple template update workflow."""

import subprocess
import sys

def update_templates():
    """Update templates from CSV and regenerate router prompt."""
    
    print("🔄 Updating templates from CSV...")
    
    # Step 1: Regenerate template library from CSV
    result = subprocess.run([sys.executable, "load_skeletons.py"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Error loading templates: {result.stderr}")
        return False
    print(result.stdout)
    
    # Step 2: Regenerate router prompt
    print("\n🔄 Regenerating router prompt...")
    result = subprocess.run([sys.executable, "generate_router_prompt.py"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Error generating prompt: {result.stderr}")
        return False
    print(result.stdout)
    
    print("\n✅ Templates and router prompt updated successfully!")
    print("   - templates/template_library.json")
    print("   - router_prompt.txt") 
    print("   - router_prompt.py")
    
    return True

if __name__ == "__main__":
    update_templates()