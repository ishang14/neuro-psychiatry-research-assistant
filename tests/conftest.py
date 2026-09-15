import os

# Provide dummy required settings so app.config.Settings() can be constructed during test
# collection without a real MongoDB Atlas cluster or Groq credentials configured.
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("GROQ_API_KEY", "gsk_test_dummy")
