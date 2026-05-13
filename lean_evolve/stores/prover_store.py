import json
import os


def init_db(db_path="proofs.json"):
    """
    Create the JSON file if missing, return its path.
    """
    if not os.path.exists(db_path):
        with open(db_path, "w") as f:
            json.dump({}, f)  # empty dict
    return db_path


def load_data(db_path):
    """Load the entire JSON dictionary."""
    with open(db_path, "r") as f:
        return json.load(f)


def save_data(db_path, data):
    """Write the entire JSON dictionary back to disk."""
    with open(db_path, "w") as f:
        json.dump(data, f, indent=2)


def store_proof(db_path, theorem: str, proof: str):
    """
    Insert a new theorem–proof pair.
    Will overwrite ONLY if theorem already exists.
    """
    data = load_data(db_path)
    data[theorem] = proof
    save_data(db_path, data)


def has_theorem(db_path, theorem: str):
    """
    Load JSON once, check if theorem exists,
    and return (exists, proof_or_none).
    """
    data = load_data(db_path)
    if theorem in data:
        return True, data[theorem]
    else:
        return False, None
