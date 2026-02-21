import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.config import paths
from src.rag.vectorstore import IPCBNSRelationalStore

def seed():
    print(f"[seed_db] Seeding database at {paths.SQLITE_DB}...")
    store = IPCBNSRelationalStore(paths.SQLITE_DB)
    
    mappings = [
        ("302", "101", "Murder"),
        ("307", "109", "Attempt to murder"),
        ("376", "64", "Rape"),
        ("379", "303", "Theft"),
        ("420", "318", "Cheating"),
        ("499", "356", "Defamation"),
        ("120B", "61", "Criminal conspiracy"),
        ("143", "189", "Unlawful assembly")
    ]
    
    for ipc, bns, notes in mappings:
        print(f"  Inserting: IPC {ipc} -> BNS {bns} ({notes})")
        store.upsert_mapping(ipc, bns, notes)
    
    print("[seed_db] Done.")

if __name__ == "__main__":
    seed()
