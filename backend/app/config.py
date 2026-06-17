"""Application configuration: env-derived constants and shared clients.

Everything the app reads from the environment lives here, so the rest of the
code imports settled values instead of calling os.getenv() in scattered places.
Modules that need the Supabase client reference it as `config.supabase` (not a
direct name import) so tests can swap it for a mock at runtime.
"""

import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

TIMEZONE = ZoneInfo("America/Sao_Paulo")
SCOPES = ["https://www.googleapis.com/auth/drive"]

MONTHS_PT = [
    "janeiro", "fevereiro", "marco", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
