"""REST API client for HTTP requests."""

import logging
from typing import Any, Dict, Optional
import aiohttp

from ..exceptions import ConnectionError as ClientConnectionError

logger = logging.getLogger(__name__)


class RestClient:
    """Async REST API client."""

    def __init__(self, server_url: str) -> None:
        """
        Initialize REST client.

        Args:
            server_url: Base URL of the server (e.g., https://worker.workers.dev)
        """
        self.server_url = server_url.rstrip("/")
        self._session: Optional[aiohttp.ClientSession] = None
        self._token: Optional[str] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure aiohttp session is created."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def set_token(self, token: Optional[str]) -> None:
        """
        Set JWT token for authentication header.

        Args:
            token: JWT token from login/register response
        """
        self._token = token

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for requests."""
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def post(self, path: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send POST request.

        Args:
            path: API path (e.g., /api/auth/login)
            data: Request body data

        Returns:
            Response JSON data

        Raises:
            ConnectionError: If request fails
        """
        url = f"{self.server_url}{path}"
        logger.debug(f"POST {url}")

        try:
            session = await self._ensure_session()
            async with session.post(url, json=data, headers=self._get_headers()) as response:
                response_data = await response.json()
                logger.debug(f"Response status: {response.status}")
                return response_data

        except aiohttp.ClientError as e:
            logger.error(f"POST request failed: {e}")
            raise ClientConnectionError(f"Request failed: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error in POST request: {e}")
            raise ClientConnectionError(f"Unexpected error: {e}") from e

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send GET request.

        Args:
            path: API path
            params: Query parameters

        Returns:
            Response JSON data

        Raises:
            ConnectionError: If request fails
        """
        url = f"{self.server_url}{path}"
        logger.debug(f"GET {url}")

        try:
            session = await self._ensure_session()
            async with session.get(
                url, params=params, headers=self._get_headers()
            ) as response:
                response_data = await response.json()
                logger.debug(f"Response status: {response.status}")
                return response_data

        except aiohttp.ClientError as e:
            logger.error(f"GET request failed: {e}")
            raise ClientConnectionError(f"Request failed: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error in GET request: {e}")
            raise ClientConnectionError(f"Unexpected error: {e}") from e

    async def delete(self, path: str) -> Dict[str, Any]:
        """
        Send DELETE request.

        Args:
            path: API path

        Returns:
            Response JSON data

        Raises:
            ConnectionError: If request fails
        """
        url = f"{self.server_url}{path}"
        logger.debug(f"DELETE {url}")

        try:
            session = await self._ensure_session()
            async with session.delete(url, headers=self._get_headers()) as response:
                # Handle both JSON and empty responses
                if response.content_type == "application/json":
                    response_data = await response.json()
                else:
                    response_data = {"status": "ok"}
                logger.debug(f"Response status: {response.status}")
                return response_data

        except aiohttp.ClientError as e:
            logger.error(f"DELETE request failed: {e}")
            raise ClientConnectionError(f"Request failed: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error in DELETE request: {e}")
            raise ClientConnectionError(f"Unexpected error: {e}") from e

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("REST client session closed")
