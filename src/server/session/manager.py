"""
Session management for MCP server
Saves and loads authentication tokens locally
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages local session storage for authentication"""

    def __init__(self, session_dir: Optional[Path] = None):
        """
        Initialize session manager

        Args:
            session_dir: Directory to store session file (default: ~/.llmbattle)
        """
        self.session_dir = session_dir or (Path.home() / ".llmbattle")
        self.session_file = self.session_dir / "session.json"

        # Create directory if it doesn't exist
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def save_session(self, account_id: int, session_id: str, token: str, username: Optional[str] = None):
        """
        Save session data to local file

        Args:
            account_id: Account ID
            session_id: Session ID
            token: JWT token
            username: Optional username for reference
        """
        data = {
            'account_id': account_id,
            'session_id': session_id,
            'token': token
        }

        if username:
            data['username'] = username

        try:
            self.session_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
            logger.info(f"Session saved: account_id={account_id}")
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            raise

    def load_session(self) -> Optional[Dict[str, Any]]:
        """
        Load session data from local file

        Returns:
            Session data dict or None if no session exists
        """
        if not self.session_file.exists():
            logger.debug("No session file found")
            return None

        try:
            data = json.loads(self.session_file.read_text(encoding='utf-8'))
            logger.info(f"Session loaded: account_id={data.get('account_id')}")
            return data
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None

    def clear_session(self):
        """Clear session data by deleting the session file"""
        if self.session_file.exists():
            try:
                self.session_file.unlink()
                logger.info("Session cleared")
            except Exception as e:
                logger.error(f"Failed to clear session: {e}")
                raise

    def has_session(self) -> bool:
        """Check if a session exists"""
        return self.session_file.exists()
