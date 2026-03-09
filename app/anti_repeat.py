import hashlib
import os

DB_FILE = "kb/generated_history.txt"

def is_duplicate(text):
    h = hashlib.md5(text.encode()).hexdigest()

    if not os.path.exists(DB_FILE):
        return False

    with open(DB_FILE) as f:
        hashes = f.read().splitlines()

    return h in hashes


def save_hash(text):
    h = hashlib.md5(text.encode()).hexdigest()

    with open(DB_FILE, "a") as f:
        f.write(h + "\n")