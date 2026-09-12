"""Create development configuration once, without overwriting local secrets."""

import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[2]
target = root / ".env"
template = (root / ".env.example").read_text()
template = template.replace(
    "POSTGRES_PASSWORD=\n", f"POSTGRES_PASSWORD={secrets.token_hex(24)}\n"
)
template = template.replace("JWT_SECRET=\n", f"JWT_SECRET={secrets.token_hex(32)}\n")
try:
    descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
except FileExistsError:
    print(".env already exists; preserved without changes.")
else:
    with os.fdopen(descriptor, "w") as file:
        file.write(template)
    print("Created development .env with random secrets (mode 0600).")
