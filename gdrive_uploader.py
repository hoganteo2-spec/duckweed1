#!/usr/bin/env python3
"""
Google Drive Uploader Module
Handles authentication and uploading segmented images to Google Drive.
"""

import logging
import os
import pickle
from pathlib import Path
from typing import Optional, Dict, List

from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as UserCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive']

# Folder name in Google Drive where files will be uploaded
UPLOAD_FOLDER_NAME = 'duckweed_segmented_images'

class GoogleDriveUploader:
    """Handle Google Drive authentication and file uploads."""
    
    def __init__(self, credentials_file: Optional[str] = None, token_file: Optional[str] = None):
        """
        Initialize Google Drive uploader.
        
        Supports two authentication methods:
        1. Service Account (credentials_file pointing to JSON key file)
        2. OAuth 2.0 User Credentials (credentials_file pointing to OAuth credentials)
        
        Args:
            credentials_file: Path to Google credentials file (service account JSON or OAuth JSON)
            token_file: Path to token.pickle for OAuth user credentials caching
        """
        self.service = None
        self.upload_folder_id = None
        self.credentials_file = credentials_file
        self.token_file = token_file or "token.pickle"
        
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Drive API."""
        try:
            if self.credentials_file and Path(self.credentials_file).exists():
                logger.info(f"Attempting authentication with credentials file: {self.credentials_file}")
                
                # Try service account first
                try:
                    creds = Credentials.from_service_account_file(
                        self.credentials_file, scopes=SCOPES
                    )
                    logger.info("Authenticated using Service Account")
                except Exception:
                    # Fall back to OAuth flow
                    logger.info("Service account authentication failed, trying OAuth flow")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    
                    # Save credentials for next run
                    with open(self.token_file, 'wb') as token:
                        pickle.dump(creds, token)
                    logger.info(f"Credentials saved to {self.token_file}")
            else:
                # Try to load cached OAuth credentials
                if Path(self.token_file).exists():
                    logger.info(f"Loading cached credentials from {self.token_file}")
                    with open(self.token_file, 'rb') as token:
                        creds = pickle.load(token)
                    
                    # Refresh if necessary
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                else:
                    logger.error("No credentials file found and no cached credentials available")
                    logger.error("Please provide credentials_file or set up OAuth credentials")
                    raise FileNotFoundError(
                        "Credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS or provide credentials_file"
                    )
            
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Google Drive API service created successfully")
            
            # Verify authentication by getting user info
            about = self.service.about().get(fields='user').execute()
            user_email = about['user'].get('emailAddress', 'Unknown')
            logger.info(f"Authenticated as: {user_email}")
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise
    
    def _get_or_create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """
        Get or create a folder in Google Drive.
        
        Args:
            folder_name: Name of the folder
            parent_id: Parent folder ID (None for root)
            
        Returns:
            Folder ID
        """
        try:
            # Search for existing folder
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and parents='{parent_id}'"
            
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                pageSize=10
            ).execute()
            
            items = results.get('files', [])
            
            if items:
                folder_id = items[0]['id']
                logger.info(f"Found existing folder '{folder_name}' with ID: {folder_id}")
                return folder_id
            
            # Create new folder if not found
            logger.info(f"Creating new folder '{folder_name}'")
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"Created new folder with ID: {folder_id}")
            return folder_id
        
        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            raise
    
    def get_upload_folder_id(self) -> str:
        """Get or create the upload folder and cache its ID."""
        if self.upload_folder_id is None:
            self.upload_folder_id = self._get_or_create_folder(UPLOAD_FOLDER_NAME)
        return self.upload_folder_id
    
    def upload_file(self, file_path: Path, file_name: Optional[str] = None, 
                   subfolder: Optional[str] = None) -> Optional[Dict]:
        """
        Upload a file to Google Drive.
        
        Args:
            file_path: Local path to file
            file_name: Name for file in Google Drive (default: original name)
            subfolder: Subfolder within upload folder (created if not exists)
            
        Returns:
            File metadata dictionary if successful, None otherwise
        """
        try:
            if not Path(file_path).exists():
                logger.error(f"File not found: {file_path}")
                return None
            
            file_name = file_name or Path(file_path).name
            
            # Get parent folder ID
            parent_id = self.get_upload_folder_id()
            
            # Create subfolder if specified
            if subfolder:
                parent_id = self._get_or_create_folder(subfolder, parent_id)
            
            # Check if file already exists
            query = f"name='{file_name}' and '{parent_id}' in parents and trashed=false"
            existing = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id)',
                pageSize=1
            ).execute()
            
            # File metadata
            file_metadata = {'name': file_name, 'parents': [parent_id]}
            media = MediaFileUpload(str(file_path), resumable=True)
            
            # Update or create file
            existing_files = existing.get('files', [])
            if existing_files:
                file_id = existing_files[0]['id']
                logger.info(f"Updating existing file: {file_name}")
                file = self.service.files().update(
                    fileId=file_id,
                    body=file_metadata,
                    media_body=media,
                    fields='id, webViewLink'
                ).execute()
            else:
                logger.info(f"Creating new file: {file_name}")
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id, webViewLink'
                ).execute()
            
            file_id = file.get('id')
            web_link = file.get('webViewLink', 'N/A')
            
            logger.info(f"✓ File uploaded successfully: {file_name}")
            logger.info(f"  File ID: {file_id}")
            logger.info(f"  View link: {web_link}")
            
            print(f"✓ Uploaded to Google Drive: {file_name}")
            print(f"  Link: {web_link}")
            
            return file
        
        except HttpError as error:
            logger.error(f"Upload failed: {error}")
            print(f"✗ Upload failed: {file_name}")
            return None
    
    def upload_multiple(self, file_paths: List[Path], subfolder: Optional[str] = None) -> Dict[str, bool]:
        """
        Upload multiple files to Google Drive.
        
        Args:
            file_paths: List of file paths to upload
            subfolder: Subfolder for all uploads
            
        Returns:
            Dictionary mapping file names to upload success status
        """
        results = {}
        for file_path in file_paths:
            result = self.upload_file(file_path, subfolder=subfolder)
            results[file_path.name] = result is not None
        
        return results


def create_uploader(use_service_account: bool = False, 
                   credentials_file: Optional[str] = None) -> GoogleDriveUploader:
    """
    Factory function to create a Google Drive uploader.
    
    Args:
        use_service_account: If True, expects GOOGLE_APPLICATION_CREDENTIALS env var
        credentials_file: Path to credentials file (overrides env var)
        
    Returns:
        GoogleDriveUploader instance
    """
    creds_file = credentials_file
    
    if not creds_file and use_service_account:
        creds_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    
    if creds_file:
        logger.info(f"Using credentials file: {creds_file}")
    else:
        logger.info("No credentials file specified, using default OAuth flow")
    
    return GoogleDriveUploader(credentials_file=creds_file)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    try:
        # Initialize uploader
        uploader = create_uploader()
        
        # Test upload
        test_file = Path("segmented_images/annotated/test.png")
        if test_file.exists():
            result = uploader.upload_file(test_file)
            if result:
                print("✓ Test upload successful")
        else:
            print("No test file found")
    
    except Exception as e:
        print(f"✗ Error: {e}")

