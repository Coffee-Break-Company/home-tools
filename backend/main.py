import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()

CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

app = FastAPI(title="Home Tools API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_drive_service():
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH, scopes=SCOPES
    )
    return build("drive", "v3", credentials=credentials)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/drive/check")
def check_file_in_folder(folder_id: str | None = None):
    """Returns true if any file exists in the folder."""
    target_folder = folder_id or DRIVE_FOLDER_ID
    if not target_folder:
        raise HTTPException(status_code=400, detail="folder_id is required")

    try:
        service = get_drive_service()
        result = service.files().list(
            q=f"'{target_folder}' in parents and trashed = false",
            fields="files(id, name)",
            pageSize=1,
        ).execute()

        files = result.get("files", [])
        return {"exists": len(files) > 0, "file_count": len(files)}

    except HttpError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
