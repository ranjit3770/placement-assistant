import hashlib
import json
import os
from pathlib import Path

def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

def main():
    base_dir = Path(__file__).parent
    
    docs = []
    
    # tenant-a 2025
    p1 = base_dir / "tenant-a" / "policy_2025.md"
    docs.append({
        "id": "doc_tenant_a_2025",
        "tenant": "tenant-a",
        "policy_version": "v2025",
        "academic_year": "2025-2026",
        "scope": "placement",
        "path": "tenant-a/policy_2025.md",
        "sha256": hash_file(p1)
    })
    
    # tenant-a 2026
    p2 = base_dir / "tenant-a" / "policy_2026.md"
    docs.append({
        "id": "doc_tenant_a_2026",
        "tenant": "tenant-a",
        "policy_version": "v2026",
        "academic_year": "2026-2027",
        "scope": "placement",
        "path": "tenant-a/policy_2026.md",
        "sha256": hash_file(p2)
    })
    
    # tenant-b 2025
    p3 = base_dir / "tenant-b" / "policy_2025.md"
    docs.append({
        "id": "doc_tenant_b_2025",
        "tenant": "tenant-b",
        "policy_version": "v2025",
        "academic_year": "2025-2026",
        "scope": "placement",
        "path": "tenant-b/policy_2025.md",
        "sha256": hash_file(p3)
    })

    manifest = {
        "corpus_version": "1.0.0",
        "documents": docs
    }
    
    with open(base_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
        
    print("Generated manifest.json")

if __name__ == "__main__":
    main()
