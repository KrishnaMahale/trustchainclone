"""
Firebase service for backend integration.
Handles communication with Firestore and Firebase Storage using firebase-admin SDK.
"""
import os
import json
from typing import Optional

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_ENABLED = True
except ImportError:
    FIREBASE_ENABLED = False
    print("[WARNING] firebase-admin not installed. Firebase features disabled.")


class FirebaseConfig:
    """Firebase configuration from environment variables."""

    def __init__(self):
        self.project_id = os.getenv("FIREBASE_PROJECT_ID", "")
        self.api_key = os.getenv("FIREBASE_API_KEY", "")
        self.auth_domain = os.getenv("FIREBASE_AUTH_DOMAIN", "")
        self.storage_bucket = os.getenv("FIREBASE_STORAGE_BUCKET", "")
        self.messaging_sender_id = os.getenv("FIREBASE_MESSAGING_SENDER_ID", "")
        self.app_id = os.getenv("FIREBASE_APP_ID", "")


def _get_firestore_client():
    """Get Firestore client instance."""
    if not FIREBASE_ENABLED:
        return None

    try:
        # Check if Firebase app is already initialized
        firebase_admin.get_app()
    except ValueError:
        # Not initialized, initialize now
        try:
            # Try to load service account key from file
            cred_path = os.getenv(
                "FIREBASE_SERVICE_ACCOUNT_PATH", "firebase-key.json"
            )
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            else:
                print(
                    f"[WARNING] Firebase service account key not found at {cred_path}. "
                    "Using default credentials (set GOOGLE_APPLICATION_CREDENTIALS env var)"
                )
                # Will use GOOGLE_APPLICATION_CREDENTIALS env var if set
                firebase_admin.initialize_app()
        except Exception as e:
            print(f"[ERROR] Failed to initialize Firebase: {e}")
            return None

    return firestore.client()


class FirebaseService:
    """Service for Firebase operations."""

    @staticmethod
    def get_config() -> FirebaseConfig:
        """Get Firebase configuration."""
        return FirebaseConfig()

    @staticmethod
    def create_user_in_firestore(user_id: int, user_data: dict) -> bool:
        """
        Create or update user document in Firestore.
        """
        if not FIREBASE_ENABLED:
            print("[INFO] Firebase disabled, skipping Firestore sync")
            return True

        try:
            db = _get_firestore_client()
            if not db:
                print("[WARNING] Firestore client not available")
                return False

            db.collection("users").document(str(user_id)).set(user_data, merge=True)
            print(f"[INFO] User {user_id} synced to Firestore")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to sync user {user_id} to Firestore: {e}")
            return False

    @staticmethod
    def save_project_to_firebase(project_id: int, project_data: dict) -> bool:
        """
        Save project data to Firestore.
        """
        if not FIREBASE_ENABLED:
            print("[INFO] Firebase disabled, skipping project sync")
            return True

        try:
            db = _get_firestore_client()
            if not db:
                print("[WARNING] Firestore client not available")
                return False

            db.collection("projects").document(str(project_id)).set(
                project_data, merge=True
            )
            print(f"[INFO] Project {project_id} synced to Firestore")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to sync project {project_id} to Firestore: {e}")
            return False

    @staticmethod
    def save_vote_to_firebase(vote_id: int, vote_data: dict) -> bool:
        """
        Save vote data to Firestore.
        """
        if not FIREBASE_ENABLED:
            return True

        try:
            db = _get_firestore_client()
            if not db:
                return False

            db.collection("votes").document(str(vote_id)).set(vote_data, merge=True)
            print(f"[INFO] Vote {vote_id} synced to Firestore")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to sync vote to Firestore: {e}")
            return False


firebase_service = FirebaseService()
