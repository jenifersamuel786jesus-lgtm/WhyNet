import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "whynet-demo-change-in-production")
    DATABASE = os.getenv("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "whynet.db"))
    CHECK_TIMEOUT = float(os.getenv("CHECK_TIMEOUT", "2.5"))
    LATENCY_ATTEMPTS = int(os.getenv("LATENCY_ATTEMPTS", "4"))
    HIGH_LATENCY_MS = float(os.getenv("HIGH_LATENCY_MS", "250"))
    MAX_CONCURRENT_DIAGNOSTICS = 4
