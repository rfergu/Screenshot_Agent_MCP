"""Session management for conversation persistence and context windowing."""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from utils.logger import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Manages conversation sessions with persistence and cleanup."""

    def __init__(self, session_dir: Optional[Path] = None):
        """Initialize session manager.

        Args:
            session_dir: Directory to store session files. 
                        Defaults to ~/.screenshot_organizer/sessions
        """
        if session_dir:
            self.session_dir = Path(session_dir)
        else:
            self.session_dir = Path.home() / ".screenshot_organizer" / "sessions"
        
        # Create session directory if it doesn't exist
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"SessionManager initialized with directory: {self.session_dir}")

    def create_session(self) -> str:
        """Create a new session with unique ID.

        Returns:
            Session ID (UUID).
        """
        session_id = str(uuid4())
        session_file = self._get_session_file(session_id)
        
        # Create empty session file with metadata
        session_data = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "conversation_history": []
        }
        
        self._write_session_file(session_file, session_data)
        logger.info(f"Created new session: {session_id}")
        
        return session_id

    def save_session(self, session_id: str, conversation_history: List[Dict[str, Any]]):
        """Save conversation history to session file.

        Args:
            session_id: Session ID.
            conversation_history: List of conversation messages.
        """
        session_file = self._get_session_file(session_id)
        
        # Load existing session data to preserve metadata
        if session_file.exists():
            session_data = self._read_session_file(session_file)
        else:
            session_data = {
                "session_id": session_id,
                "created_at": datetime.now().isoformat()
            }
        
        # Update session data
        session_data["last_accessed"] = datetime.now().isoformat()
        session_data["conversation_history"] = conversation_history
        session_data["message_count"] = len(conversation_history)
        
        self._write_session_file(session_file, session_data)
        logger.debug(f"Saved session {session_id} with {len(conversation_history)} messages")

    def load_session(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """Load conversation history from session file.

        Args:
            session_id: Session ID.

        Returns:
            Conversation history if session exists, None otherwise.
        """
        session_file = self._get_session_file(session_id)
        
        if not session_file.exists():
            logger.warning(f"Session file not found: {session_id}")
            return None
        
        try:
            session_data = self._read_session_file(session_file)
            
            # Update last accessed time
            session_data["last_accessed"] = datetime.now().isoformat()
            self._write_session_file(session_file, session_data)
            
            conversation_history = session_data.get("conversation_history", [])
            logger.info(f"Loaded session {session_id} with {len(conversation_history)} messages")
            
            return conversation_history
            
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    def clear_session(self, session_id: str):
        """Clear conversation history for a session but keep the session file.

        Args:
            session_id: Session ID.
        """
        session_file = self._get_session_file(session_id)
        
        if session_file.exists():
            session_data = self._read_session_file(session_file)
            session_data["conversation_history"] = []
            session_data["message_count"] = 0
            session_data["last_accessed"] = datetime.now().isoformat()
            self._write_session_file(session_file, session_data)
            logger.info(f"Cleared conversation history for session {session_id}")

    def delete_session(self, session_id: str):
        """Delete a session file completely.

        Args:
            session_id: Session ID.
        """
        session_file = self._get_session_file(session_id)
        
        if session_file.exists():
            session_file.unlink()
            logger.info(f"Deleted session: {session_id}")
        else:
            logger.warning(f"Session file not found for deletion: {session_id}")

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all available sessions with metadata.

        Returns:
            List of session metadata dictionaries.
        """
        sessions = []
        
        for session_file in self.session_dir.glob("session_*.json"):
            try:
                session_data = self._read_session_file(session_file)
                sessions.append({
                    "session_id": session_data["session_id"],
                    "created_at": session_data.get("created_at"),
                    "last_accessed": session_data.get("last_accessed"),
                    "message_count": session_data.get("message_count", 0)
                })
            except Exception as e:
                logger.warning(f"Failed to read session file {session_file}: {e}")
        
        # Sort by last accessed (most recent first)
        sessions.sort(key=lambda x: x.get("last_accessed", ""), reverse=True)
        
        logger.debug(f"Found {len(sessions)} sessions")
        return sessions

    def cleanup_old_sessions(self, max_age_days: int = 30):
        """Delete sessions older than specified age.

        Args:
            max_age_days: Maximum age in days. Sessions older than this are deleted.

        Returns:
            Number of sessions deleted.
        """
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        deleted_count = 0
        
        for session_file in self.session_dir.glob("session_*.json"):
            try:
                session_data = self._read_session_file(session_file)
                last_accessed = session_data.get("last_accessed")
                
                if last_accessed:
                    last_accessed_dt = datetime.fromisoformat(last_accessed)
                    if last_accessed_dt < cutoff_date:
                        session_file.unlink()
                        deleted_count += 1
                        logger.info(f"Deleted old session: {session_data['session_id']}")
                        
            except Exception as e:
                logger.warning(f"Failed to process session file {session_file}: {e}")
        
        logger.info(f"Cleaned up {deleted_count} old sessions (>{max_age_days} days)")
        return deleted_count

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata about a specific session.

        Args:
            session_id: Session ID.

        Returns:
            Session metadata if session exists, None otherwise.
        """
        session_file = self._get_session_file(session_id)
        
        if not session_file.exists():
            return None
        
        try:
            session_data = self._read_session_file(session_file)
            return {
                "session_id": session_data["session_id"],
                "created_at": session_data.get("created_at"),
                "last_accessed": session_data.get("last_accessed"),
                "message_count": session_data.get("message_count", 0),
                "file_size_bytes": session_file.stat().st_size
            }
        except Exception as e:
            logger.error(f"Failed to get session info for {session_id}: {e}")
            return None

    def _get_session_file(self, session_id: str) -> Path:
        """Get path to session file.

        Args:
            session_id: Session ID.

        Returns:
            Path to session file.
        """
        return self.session_dir / f"session_{session_id}.json"

    def _read_session_file(self, session_file: Path) -> Dict[str, Any]:
        """Read session data from file.

        Args:
            session_file: Path to session file.

        Returns:
            Session data dictionary.
        """
        with open(session_file, "r") as f:
            return json.load(f)

    def _write_session_file(self, session_file: Path, session_data: Dict[str, Any]):
        """Write session data to file.

        Args:
            session_file: Path to session file.
            session_data: Session data dictionary.
        """
        with open(session_file, "w") as f:
            json.dump(session_data, f, indent=2)

    def export_session(self, session_id: str, export_path: Path) -> bool:
        """Export a session to a custom location.

        Args:
            session_id: Session ID to export.
            export_path: Destination path for export.

        Returns:
            True if export successful, False otherwise.
        """
        session_file = self._get_session_file(session_id)
        
        if not session_file.exists():
            logger.error(f"Cannot export non-existent session: {session_id}")
            return False
        
        try:
            session_data = self._read_session_file(session_file)
            
            with open(export_path, "w") as f:
                json.dump(session_data, f, indent=2)
            
            logger.info(f"Exported session {session_id} to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export session {session_id}: {e}")
            return False

    def import_session(self, import_path: Path) -> Optional[str]:
        """Import a session from a file.

        Args:
            import_path: Path to session file to import.

        Returns:
            Session ID if import successful, None otherwise.
        """
        try:
            with open(import_path, "r") as f:
                session_data = json.load(f)
            
            # Generate new session ID to avoid conflicts
            session_id = str(uuid4())
            session_data["session_id"] = session_id
            session_data["imported_at"] = datetime.now().isoformat()
            
            session_file = self._get_session_file(session_id)
            self._write_session_file(session_file, session_data)
            
            logger.info(f"Imported session from {import_path} as {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to import session from {import_path}: {e}")
            return None
