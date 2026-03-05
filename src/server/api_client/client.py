"""
HTTP API client for central API server
"""

import os
import requests
from typing import Dict, Any, Optional, List

from .errors import (
    ApiError,
    AuthenticationError,
    ValidationError,
    NetworkError,
    NotFoundError
)


class ApiClient:
    """HTTP API client"""

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize API client

        Args:
            base_url: API base URL (defaults to API_BASE_URL env var or http://localhost:3000)
        """
        self.base_url = base_url or os.getenv('API_BASE_URL', 'http://localhost:3000')
        self.token = None
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    def set_token(self, token: str):
        """Set JWT token for authentication"""
        self.token = token
        self.session.headers.update({'Authorization': f'Bearer {token}'})

    def clear_token(self):
        """Clear JWT token"""
        self.token = None
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']

    def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint (e.g., '/api/accounts')
            json_data: JSON request body
            params: URL query parameters

        Returns:
            Response JSON data

        Raises:
            ApiError: API error
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=json_data,
                params=params,
                timeout=30
            )

            # Handle HTTP errors
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    error_message = error_data.get('error', {}).get('message', 'Unknown error')
                    error_code = error_data.get('error', {}).get('code', 'UNKNOWN_ERROR')
                except:
                    error_message = response.text or f'HTTP {response.status_code}'
                    error_code = f'HTTP_{response.status_code}'

                if response.status_code == 401:
                    raise AuthenticationError(error_message)
                elif response.status_code == 400:
                    raise ValidationError(error_message)
                elif response.status_code == 404:
                    raise NotFoundError(error_message)
                else:
                    raise ApiError(f'{error_code}: {error_message}')

            # Return JSON response
            return response.json()

        except requests.exceptions.RequestException as e:
            raise NetworkError(f'Network error: {e}')

    # Account API
    def create_account(self, username: str) -> Dict[str, Any]:
        """
        Create new account

        Returns:
            {
                'account_id': int,
                'session_id': str,
                'token': str,
                'message': str
            }
        """
        return self._request('POST', '/api/accounts', json_data={'username': username})

    def login(self, username: str) -> Dict[str, Any]:
        """
        Login to existing account

        Returns:
            {
                'account_id': int,
                'session_id': str,
                'token': str,
                'characters': List[Dict],
                'message': str
            }
        """
        return self._request('POST', '/api/accounts/login', json_data={'username': username})

    # Character API
    def create_character(
        self,
        account_id: int,
        name: str,
        prompt: str,
        base_hp: int,
        base_attack: int,
        base_defense: int,
        base_speed: int,
        ability_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Create new character (with computed stats from local LLM)

        Returns:
            {
                'character_id': int,
                'name': str,
                'level': int,
                'computed_stats': Dict,
                'abilities': List[Dict],
                'message': str
            }
        """
        data = {
            'account_id': account_id,
            'name': name,
            'prompt': prompt,
            'base_hp': base_hp,
            'base_attack': base_attack,
            'base_defense': base_defense,
            'base_speed': base_speed,
            'ability_ids': ability_ids or []
        }
        return self._request('POST', '/api/characters', json_data=data)

    def get_character(self, character_id: int) -> Dict[str, Any]:
        """Get character info"""
        return self._request('GET', f'/api/characters/{character_id}')

    def list_characters(self, account_id: int) -> Dict[str, Any]:
        """List characters by account"""
        return self._request('GET', '/api/characters', params={'account_id': account_id})

    def list_abilities(self) -> Dict[str, Any]:
        """List all available abilities"""
        return self._request('GET', '/api/abilities')

    # Matchmaking API
    def join_queue(self, character_id: int) -> Dict[str, Any]:
        """
        Join matchmaking queue

        Returns:
            {
                'queue_id': int,
                'character_id': int,
                'rating': int,
                'status': str,
                'message': str
            }
        """
        return self._request('POST', '/api/queue', json_data={'character_id': character_id})

    def leave_queue(self, character_id: int) -> Dict[str, Any]:
        """Leave matchmaking queue"""
        return self._request('DELETE', f'/api/queue/{character_id}')

    def get_queue(self) -> Dict[str, Any]:
        """Get current queue status"""
        return self._request('GET', '/api/queue')

    # Battle API
    def create_battle(self, player1_id: int, player2_id: int) -> Dict[str, Any]:
        """
        Create new battle

        Returns:
            {
                'battle_id': int,
                'message': str
            }
        """
        data = {
            'player1_id': player1_id,
            'player2_id': player2_id
        }
        return self._request('POST', '/api/battles', json_data=data)

    def record_turn(
        self,
        battle_id: int,
        turn_number: int,
        player1_action: str,
        player2_action: str,
        player1_damage: int,
        player2_damage: int,
        player1_hp_after: int,
        player2_hp_after: int,
        turn_log: str,
        winner_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Record battle turn result (computed locally by MCP server)

        Returns:
            {
                'battle_id': int,
                'turn_number': int,
                'status': str,
                'winner_id': Optional[int],
                'message': str
            }
        """
        data = {
            'turn_number': turn_number,
            'player1_action': player1_action,
            'player2_action': player2_action,
            'player1_damage': player1_damage,
            'player2_damage': player2_damage,
            'player1_hp_after': player1_hp_after,
            'player2_hp_after': player2_hp_after,
            'turn_log': turn_log
        }
        if winner_id:
            data['winner_id'] = winner_id

        return self._request('POST', f'/api/battles/{battle_id}/turns', json_data=data)

    def get_battle(self, battle_id: int) -> Dict[str, Any]:
        """Get battle status"""
        return self._request('GET', f'/api/battles/{battle_id}')

    def get_battle_turns(self, battle_id: int) -> Dict[str, Any]:
        """Get battle turns"""
        return self._request('GET', f'/api/battles/{battle_id}/turns')

    # Stats API
    def get_leaderboard(self, limit: int = 50) -> Dict[str, Any]:
        """Get leaderboard"""
        return self._request('GET', '/api/leaderboard', params={'limit': limit})

    def get_character_stats(self, character_id: int) -> Dict[str, Any]:
        """Get character stats"""
        return self._request('GET', f'/api/characters/{character_id}/stats')
