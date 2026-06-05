import os
from unittest.mock import MagicMock, patch

# Must be set before main.py is imported — load_dotenv() won't override existing vars
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "fake-anon-key")
os.environ.setdefault("GOOGLE_CREDENTIALS_PATH", "/fake/creds.json")

# Prevent real Supabase client construction when main.py is imported at collection time
_patcher = patch("supabase.create_client", return_value=MagicMock())
_patcher.start()
