"""
modules/drive_utils.py
Shared Google Drive connection, folder scanning, and file download utilities.
"""
import io
import time
import socket
import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

# Prevent WinError 10054 on institutional proxy networks
socket.setdefaulttimeout(90)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
ROOT_FOLDER_ID = "1I4EeWDnCt3Bv0jbJyYh_r7Yr6YbNGY_F"  # Exam Dashboard root

# Fixed top-level section folder IDs
SECTION_FOLDER_IDS = {
    "Evaluation Dashboard Details": "1jYZSdfEq7lQ8SWfJKiI83dBBq4o24JJG",
    "Result Analysis":              "1YSjF3EoEyPT-ecaQIaUXl1fHY5Q67qwM",
}

DATA_MIMETYPES = {
    "text/csv",
    "text/comma-separated-values",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/vnd.google-apps.spreadsheet",
}


def get_drive_service():
    """Builds a fresh Google Drive API service client from Streamlit secrets."""
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def execute_with_retry(fn, max_retries: int = 3, delay: float = 1.5):
    """Retries a callable on transient network errors (e.g. WinError 10054)."""
    for attempt in range(max_retries):
        try:
            return fn()
        except (ConnectionResetError, socket.error, OSError) as exc:
            if attempt == max_retries - 1:
                raise exc
            time.sleep(delay * (attempt + 1))
        except HttpError:
            raise


@st.cache_data(ttl=300, show_spinner=False)
def list_subfolders(parent_id: str) -> list[dict]:
    """Returns immediate child folders of *parent_id*, sorted by name."""
    service = get_drive_service()

    def _call():
        res = service.files().list(
            q=f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id,name)",
            orderBy="name",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        return res.get("files", [])

    return execute_with_retry(_call)


@st.cache_data(ttl=300, show_spinner=False)
def find_files_recursive(folder_id: str) -> list[dict]:
    """Recursively collects all data files under *folder_id*."""
    service = get_drive_service()

    def _collect(fid):
        mime_filter = " or ".join(f"mimeType='{m}'" for m in DATA_MIMETYPES)
        files = service.files().list(
            q=f"'{fid}' in parents and trashed=false and ({mime_filter})",
            fields="files(id,name,mimeType,modifiedTime)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute().get("files", [])

        subfolders = service.files().list(
            q=f"'{fid}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id,name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute().get("files", [])

        result = list(files)
        for sub in subfolders:
            result.extend(_collect(sub["id"]))
        return result

    return execute_with_retry(lambda: _collect(folder_id))


@st.cache_data(ttl=600, show_spinner=False)
def download_file(file_id: str, file_name: str, mime_type: str) -> pd.DataFrame:
    """Downloads a Drive file and returns a cleaned DataFrame."""
    def _download():
        service = get_drive_service()
        buf = io.BytesIO()
        if mime_type == "application/vnd.google-apps.spreadsheet":
            req = service.files().export_media(fileId=file_id, mimeType="text/csv")
        else:
            req = service.files().get_media(fileId=file_id, supportsAllDrives=True)
        dl = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
        buf.seek(0)
        if mime_type == "application/vnd.google-apps.spreadsheet" or file_name.lower().endswith(".csv"):
            try:
                return pd.read_csv(buf, encoding="utf-8")
            except UnicodeDecodeError:
                buf.seek(0)
                return pd.read_csv(buf, encoding="latin1")
        return pd.read_excel(buf)

    return execute_with_retry(_download)
