import chromadb.config
chromadb.config.Settings.anonymized_telemetry = False  # 🔕 disables telemetry

from chromadb import PersistentClient
client = PersistentClient(path="test")            # ✅ no telemetry errors now

print("Chroma fully ready")
