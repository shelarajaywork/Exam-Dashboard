"""
Google Drive Service module.
Handles secure authentication with Google Drive API via Service Account or OAuth 2.0,
retrieving subfolders, and downloading/parsing data files (CSV, Excel, Google Sheets).
"""
import os
import io
import json
import logging
from typing import List, Dict, Optional, Tuple, Any
import pandas as pd
from dotenv import load_dotenv

# Load local environment if present
load_dotenv()

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]

def get_drive_credentials():
    """
    Attempts to locate and build Google credentials from:
    1. Streamlit secrets (for cloud deployment)
    2. Local service_account.json file
    3. GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_SERVICE_ACCOUNT_JSON environment variables
    4. OAuth2 token.json/credentials.json
    """
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    # Check Streamlit secrets if available
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if "gdrive_service_account" in st.secrets:
                sa_info = dict(st.secrets["gdrive_service_account"])
                return service_account.Credentials.from_service_account_info(sa_info, scopes=SCOPES)
            if "GOOGLE_SERVICE_ACCOUNT_JSON" in st.secrets:
                sa_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
                return service_account.Credentials.from_service_account_info(sa_info, scopes=SCOPES)
    except Exception as e:
        logger.debug(f"Streamlit secrets check note: {e}")

    # Check environment variable with raw JSON
    env_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if env_json:
        try:
            sa_info = json.loads(env_json)
            return service_account.Credentials.from_service_account_info(sa_info, scopes=SCOPES)
        except Exception as e:
            logger.error(f"Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON: {e}")

    # Check environment variable with file path
    env_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
    if os.path.exists(env_file):
        try:
            return service_account.Credentials.from_service_account_file(env_file, scopes=SCOPES)
        except Exception as e:
            logger.error(f"Failed to load service account from {env_file}: {e}")

    # Check OAuth2 token.json
    token_path = "token.json"
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            if creds and creds.valid:
                return creds
        except Exception as e:
            logger.error(f"Failed to load OAuth token from {token_path}: {e}")

    return None

def build_drive_service():
    """Builds and returns Google Drive v3 resource, or None if credentials are not configured."""
    creds = get_drive_credentials()
    if not creds:
        return None
    from googleapiclient.discovery import build
    return build('drive', 'v3', credentials=creds)

def list_drive_subfolders(service, parent_folder_id: str) -> List[Dict[str, str]]:
    """
    Fetches all subfolders residing inside the specified parent folder in Google Drive.
    """
    if not service or not parent_folder_id:
        return []

    try:
        query = (
            f"'{parent_folder_id}' in parents and "
            "mimeType = 'application/vnd.google-apps.folder' and "
            "trashed = false"
        )
        results = service.files().list(
            q=query,
            fields="files(id, name, modifiedTime)",
            orderBy="name",
            pageSize=100
        ).execute()

        folders = results.get('files', [])
        return [{"id": f["id"], "name": f["name"], "modifiedTime": f.get("modifiedTime", "")} for f in folders]
    except Exception as e:
        logger.error(f"Error querying Google Drive subfolders: {e}")
        raise e

def list_files_in_folder(service, folder_id: str) -> List[Dict[str, str]]:
    """
    Lists all supported data files (Excel, CSV, Google Sheets) inside a given folder.
    """
    if not service or not folder_id:
        return []

    try:
        query = (
            f"'{folder_id}' in parents and "
            "("
            "mimeType = 'text/csv' or "
            "mimeType = 'text/comma-separated-values' or "
            "mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or "
            "mimeType = 'application/vnd.ms-excel' or "
            "mimeType = 'application/vnd.google-apps.spreadsheet'"
            ") and trashed = false"
        )
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType, size, modifiedTime)",
            orderBy="name",
            pageSize=100
        ).execute()

        return results.get('files', [])
    except Exception as e:
        logger.error(f"Error querying files in folder {folder_id}: {e}")
        raise e

def download_file_as_dataframe(service, file_id: str, mime_type: str, file_name: str) -> Optional[pd.DataFrame]:
    """
    Downloads file content from Google Drive and converts it into a pandas DataFrame.
    Supports CSV, Excel (.xlsx, .xls), and Google Sheets (auto-exported to CSV/Excel).
    """
    from googleapiclient.http import MediaIoBaseDownload

    buffer = io.BytesIO()

    try:
        if mime_type == 'application/vnd.google-apps.spreadsheet':
            # Export Google Sheet to CSV
            request = service.files().export_media(fileId=file_id, mimeType='text/csv')
        else:
            # Direct binary download
            request = service.files().get_media(fileId=file_id)

        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        buffer.seek(0)

        # Parse into DataFrame based on file extension or mime type
        lower_name = file_name.lower()
        if mime_type == 'application/vnd.google-apps.spreadsheet' or lower_name.endswith('.csv') or 'csv' in mime_type:
            try:
                df = pd.read_csv(buffer, encoding='utf-8')
            except UnicodeDecodeError:
                buffer.seek(0)
                df = pd.read_csv(buffer, encoding='latin1')
        elif lower_name.endswith('.xlsx') or lower_name.endswith('.xls') or 'excel' in mime_type or 'spreadsheetml' in mime_type:
            df = pd.read_excel(buffer)
        else:
            # Attempt CSV as fallback
            df = pd.read_csv(buffer)

        return df

    except Exception as e:
        logger.error(f"Failed to read file {file_name} ({file_id}): {e}")
        raise e

def load_all_folder_data(service, folder_id: str) -> Tuple[Optional[pd.DataFrame], List[Dict[str, str]]]:
    """
    Fetches and combines all spreadsheet/CSV datasets found inside a Google Drive folder.
    Returns (combined_dataframe, list_of_file_metadatas).
    """
    files = list_files_in_folder(service, folder_id)
    if not files:
        return None, []

    dfs = []
    for f in files:
        try:
            df = download_file_as_dataframe(service, f['id'], f['mimeType'], f['name'])
            if df is not None and not df.empty:
                df['_source_file'] = f['name']
                dfs.append(df)
        except Exception as e:
            logger.warning(f"Skipping unreadable file {f['name']}: {e}")

    if not dfs:
        return None, files

    combined = pd.concat(dfs, ignore_index=True)
    return combined, files
