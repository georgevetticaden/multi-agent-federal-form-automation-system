"""
OAuth 2.1 token validation for MDCalc MCP Server.

This module provides OAuth token validation for the MDCalc MCP server using
Auth0 as the identity provider. It supports both JWT and JWE token formats
and implements selective authentication per MCP protocol requirements.

TOKEN TYPES SUPPORTED:
    - JWT (JSON Web Tokens): Validated via JWKS (JSON Web Key Set)
    - JWE (JSON Web Encryption): Validated via Auth0 userinfo endpoint
    - Opaque tokens: Validated via Auth0 userinfo endpoint

VALIDATION STRATEGY:
    1. Extract token from Authorization: Bearer <token> header
    2. Check if token has 'kid' (key ID) in header:
       - If yes: JWT token → Validate signature with JWKS
       - If no: JWE/opaque → Validate via userinfo endpoint
    3. Verify issuer, audience, and expiration
    4. Extract and return scopes for authorization

SELECTIVE AUTHENTICATION:
    Per MCP specification, authentication is NOT required for all methods:

    - initialize: NO auth (client discovers capabilities)
    - notifications/initialized: NO auth (handshake confirmation)
    - tools/list: REQUIRES auth (resource access)
    - tools/call: REQUIRES auth (calculator execution)

    This is enforced in server.py by calling verify_token_manual() only
    for methods that require authentication.

SECURITY FEATURES:
    - JWKS caching to reduce Auth0 API calls
    - Token signature verification for JWT tokens
    - Audience and issuer validation
    - Scope-based authorization
    - Graceful handling of multiple token formats

For Auth0 configuration, see .env file and docs/DEPLOYMENT_GUIDE.md
"""

import httpx
from jose import jwt, JWTError
from typing import Dict
from fastapi import HTTPException
from functools import lru_cache

from .config import settings
from .logging_config import get_logger

# Setup logger for this module
logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_jwks() -> Dict:
    """
    Fetch JSON Web Key Set from Auth0.
    Cached to avoid repeated requests.
    """
    jwks_url = f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json"
    logger.info(f"Fetching JWKS from Auth0: {jwks_url}")

    try:
        response = httpx.get(jwks_url, timeout=10.0)
        response.raise_for_status()
        jwks = response.json()

        key_count = len(jwks.get("keys", []))
        logger.info(f"Successfully fetched JWKS with {key_count} keys")
        logger.debug(f"JWKS key IDs: {[k.get('kid') for k in jwks.get('keys', [])]}")

        return jwks
    except Exception as e:
        logger.error(f"Failed to fetch JWKS from {jwks_url}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch JWKS: {str(e)}"
        )


def validate_via_userinfo(token: str) -> Dict:
    """
    Validate opaque/JWE token using Auth0 userinfo endpoint.

    Used for tokens that don't have a kid (JWE encrypted tokens).
    Auth0's userinfo endpoint validates the token and returns user info.

    Args:
        token: Access token to validate

    Returns:
        Token payload with subject and scopes

    Raises:
        HTTPException: If token is invalid
    """
    userinfo_url = f"https://{settings.AUTH0_DOMAIN}/userinfo"
    logger.info(f"Validating token via userinfo: {userinfo_url}")

    try:
        response = httpx.get(
            userinfo_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0
        )

        if response.status_code == 401:
            logger.error("Token validation failed: 401 Unauthorized from userinfo endpoint")
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token"
            )

        response.raise_for_status()
        userinfo = response.json()

        logger.info(f"Token validated successfully via userinfo for subject: {userinfo.get('sub')}")

        # Return payload compatible with JWT validation
        # Auth0 userinfo doesn't return scopes, so we grant all configured scopes
        return {
            "sub": userinfo.get("sub"),
            "iss": settings.AUTH0_ISSUER.rstrip('/'),
            "aud": settings.AUTH0_API_AUDIENCE,
            "scope": "mdcalc:read mdcalc:calculate",  # Grant all scopes for validated tokens
            "permissions": ["mdcalc:read", "mdcalc:calculate"]
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"Token validation failed: HTTP {e.response.status_code}")
        raise HTTPException(
            status_code=401,
            detail=f"Token validation failed: {e.response.status_code}"
        )
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail=f"Token validation failed: {str(e)}"
        )


async def verify_token_manual(request) -> Dict:
    """
    Verify OAuth token from Authorization header.

    Used for selective authentication in MCP endpoint where we need to
    conditionally validate tokens based on MCP method type (from request body).
    Does not use FastAPI's dependency injection to allow conditional execution.

    Args:
        request: FastAPI Request object

    Returns:
        Decoded token payload with scopes

    Raises:
        HTTPException: If token is missing, invalid, or expired
    """
    from fastapi import Request

    # Extract Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        logger.error("Missing Authorization header")
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Validate Bearer scheme
    if not auth_header.startswith("Bearer "):
        logger.error(f"Invalid Authorization header format: {auth_header[:20]}...")
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Extract token
    token = auth_header[7:]  # Remove "Bearer " prefix
    token_preview = f"{token[:20]}...{token[-20:]}" if len(token) > 40 else token

    logger.info(f"Validating token: {token_preview}")

    try:
        # Try to decode token header
        try:
            unverified_header = jwt.get_unverified_header(token)
            token_kid = unverified_header.get("kid")
            logger.debug(f"Token key ID (kid): {token_kid}")

            # If no kid, this is likely a JWE or opaque token
            if token_kid is None:
                logger.info("Token has no kid - using Auth0 userinfo for validation")
                return validate_via_userinfo(token)

        except JWTError as e:
            # Not a JWT, try userinfo validation
            logger.info(f"Token is not a JWT: {e} - using Auth0 userinfo for validation")
            return validate_via_userinfo(token)

        # Get JWKS from Auth0
        jwks = get_jwks()

        # Find matching key in JWKS
        rsa_key = None
        for key in jwks.get("keys", []):
            if key["kid"] == token_kid:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                logger.debug(f"Found matching key in JWKS: {token_kid}")
                break

        if rsa_key is None:
            logger.error(f"Token key ID {token_kid} not found in JWKS")
            logger.debug(f"Available key IDs: {[k.get('kid') for k in jwks.get('keys', [])]}")
            raise HTTPException(
                status_code=401,
                detail="Unable to find appropriate key in JWKS"
            )

        # Verify and decode token
        logger.debug(f"Verifying token signature and claims")
        logger.debug(f"Expected audience: {settings.AUTH0_API_AUDIENCE}")
        logger.debug(f"Expected issuer: {settings.AUTH0_ISSUER}")

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.AUTH0_API_AUDIENCE,
            issuer=settings.AUTH0_ISSUER
        )

        # Log successful validation (don't log sensitive payload data)
        scopes = get_token_scopes(payload)
        subject = payload.get("sub", "unknown")
        logger.info(f"Token validated successfully for subject: {subject}")
        logger.info(f"Token scopes: {scopes}")

        return payload

    except JWTError as e:
        logger.error(f"JWT validation failed: {str(e)}")
        logger.debug(f"Token preview: {token_preview}")
        raise HTTPException(
            status_code=401,
            detail=f"Token validation failed: {str(e)}"
        )
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected authentication error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail=f"Authentication error: {str(e)}"
        )


def get_token_scopes(token_payload: Dict) -> list:
    """
    Extract scopes from decoded token payload.

    Args:
        token_payload: Decoded JWT token

    Returns:
        List of scope strings (e.g., ["mdcalc:read", "mdcalc:calculate"])
    """
    # Auth0 stores scopes as space-separated string
    scopes_string = token_payload.get("scope", "")
    return scopes_string.split() if scopes_string else []


def require_scope(required_scope: str, token_scopes: list) -> None:
    """
    Verify that token has required scope.

    Args:
        required_scope: Scope needed for the operation
        token_scopes: Scopes present in the token

    Raises:
        HTTPException: If required scope is missing
    """
    logger.debug(f"Checking for required scope: {required_scope}")
    logger.debug(f"Token has scopes: {token_scopes}")

    if required_scope not in token_scopes:
        logger.warning(f"Insufficient permissions: required '{required_scope}', have {token_scopes}")
        raise HTTPException(
            status_code=403,
            detail=f"Insufficient permissions. Required scope: {required_scope}"
        )

    logger.debug(f"Scope check passed: {required_scope}")
