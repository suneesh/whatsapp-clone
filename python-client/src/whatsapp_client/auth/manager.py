"""Authentication manager for user login and registration."""

import logging
from typing import Optional, TYPE_CHECKING

from ..models import User, RegisterRequest, LoginRequest, AuthResponse, ErrorResponse
from ..exceptions import AuthenticationError, ValidationError, UsernameExistsError

if TYPE_CHECKING:
    from ..client import WhatsAppClient

logger = logging.getLogger(__name__)


class AuthManager:
    """Manages user authentication and registration."""

    def __init__(self, client: "WhatsAppClient") -> None:
        """
        Initialize AuthManager.

        Args:
            client: Parent WhatsAppClient instance
        """
        self.client = client
        self._user: Optional[User] = None
        self._user_id: Optional[str] = None
        self._token: Optional[str] = None

    @property
    def user(self) -> Optional[User]:
        """Get current authenticated user."""
        return self._user

    @property
    def user_id(self) -> Optional[str]:
        """Get current user ID."""
        return self._user_id

    @property
    def token(self) -> Optional[str]:
        """Get current JWT token."""
        return self._token

    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self._user is not None and self._user_id is not None and self._token is not None

    async def register(
        self, username: str, password: str, avatar: Optional[str] = None
    ) -> User:
        """
        Register a new user account.

        Args:
            username: Username (3-100 characters)
            password: Password (6+ characters)
            avatar: Optional avatar URL

        Returns:
            User object with account details

        Raises:
            ValidationError: If username or password invalid
            UsernameExistsError: If username already taken
            ConnectionError: If network request fails
        """
        logger.info(f"Registering new user: {username}")

        # Validate input
        try:
            request = RegisterRequest(username=username, password=password, avatar=avatar)
        except ValueError as e:
            raise ValidationError(str(e)) from e

        # Send registration request
        try:
            response = await self.client._rest.post(
                "/api/auth/register", data=request.model_dump(exclude_none=True)
            )

            # Check for errors
            if "error" in response:
                error_msg = response["error"]
                if "already taken" in error_msg.lower():
                    raise UsernameExistsError(error_msg)
                raise AuthenticationError(error_msg)

            # Parse response
            auth_response = AuthResponse(**response)
            self._user = User(**response)
            self._user_id = auth_response.id
            self._token = auth_response.token
            
            # Update REST client with token
            self.client._rest.set_token(self._token)

            logger.info(f"Successfully registered user: {username} (ID: {self._user_id})")
            return self._user

        except (UsernameExistsError, AuthenticationError):
            raise
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            raise AuthenticationError(f"Registration failed: {e}") from e

    async def login(self, username: str, password: str) -> User:
        """
        Login with existing credentials.

        Args:
            username: Username
            password: Password

        Returns:
            User object with account details

        Raises:
            ValidationError: If credentials are empty
            AuthenticationError: If login fails
            ConnectionError: If network request fails
        """
        logger.info(f"Logging in user: {username}")

        # Validate input
        try:
            request = LoginRequest(username=username, password=password)
        except ValueError as e:
            raise ValidationError(str(e)) from e

        # Send login request
        try:
            response = await self.client._rest.post(
                "/api/auth/login", data=request.model_dump()
            )

            # Check for errors
            if "error" in response:
                error_msg = response["error"]
                raise AuthenticationError(error_msg)

            # Parse response
            auth_response = AuthResponse(**response)
            self._user = User(**response)
            self._user_id = auth_response.id
            self._token = auth_response.token
            
            # Update REST client with token
            self.client._rest.set_token(self._token)

            logger.info(f"Successfully logged in: {username} (ID: {self._user_id})")
            return self._user

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise AuthenticationError(f"Login failed: {e}") from e

    async def logout(self) -> None:
        """
        Logout current user and clear session data.
        """
        if self._user:
            logger.info(f"Logging out user: {self._user.username}")
        else:
            logger.info("Logging out (no user was logged in)")

        self._user = None
        self._user_id = None
