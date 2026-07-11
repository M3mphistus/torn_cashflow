import os

from cryptography.fernet import Fernet

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("DEV_TORN_PLAYER_ID", "1")
os.environ.setdefault("XANAX_ITEM_ID", "206")
os.environ.setdefault("DEV_TORN_PLAYER_NAME", "test-dev")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("API_KEY_ENCRYPTION_SECRET", Fernet.generate_key().decode())
os.environ.setdefault("FRONTEND_ORIGIN", "http://localhost:5173")
