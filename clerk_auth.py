import os
import httpx
from functools import wraps
from flask import request, jsonify, redirect, url_for, session, g
from clerk_backend_api import Clerk
from clerk_backend_api.security import authenticate_request
from clerk_backend_api.security.types import AuthenticateRequestOptions

# Initialize Clerk SDK
clerk_secret_key = os.environ.get('CLERK_SECRET_KEY')
clerk_sdk = Clerk(bearer_auth=clerk_secret_key) if clerk_secret_key else None


def _try_resolve_clerk_user():
    """
    Attempt to verify the Clerk session from the current request
    and populate g.clerk_user_id.  Does nothing if already set or
    if Clerk is not configured.  Never raises — failures are silent.
    """
    if hasattr(g, 'clerk_user_id'):
        return  # already resolved this request
    if not clerk_sdk:
        return

    try:
        httpx_request = httpx.Request(
            method=request.method,
            url=request.url,
            headers=dict(request.headers)
        )
        request_state = clerk_sdk.authenticate_request(
            httpx_request,
            AuthenticateRequestOptions(
                authorized_parties=[request.host_url.rstrip('/')]
            )
        )
        if request_state.is_signed_in and hasattr(request_state, 'payload') and request_state.payload:
            g.clerk_user_id = request_state.payload.get('sub')
    except Exception as e:
        pass  # unauthenticated or network error — leave g.clerk_user_id unset


def clerk_auth_required(f):
    """Decorator to protect routes with Clerk authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If Clerk is not configured, redirect to login
        if not clerk_sdk:
            session['next_url'] = request.url
            return redirect(url_for('clerk_login'))

        _try_resolve_clerk_user()

        if not getattr(g, 'clerk_user_id', None):
            session['next_url'] = request.url
            return redirect(url_for('clerk_login'))

        return f(*args, **kwargs)

    return decorated_function


def get_clerk_user():
    """Get the current authenticated Clerk user"""
    _try_resolve_clerk_user()
    if not clerk_sdk or not hasattr(g, 'clerk_user_id'):
        return None

    try:
        user = clerk_sdk.users.get(user_id=g.clerk_user_id)
        return user
    except Exception as e:
        print(f"Error fetching Clerk user: {e}")
        return None


def get_clerk_user_id():
    """Get the current authenticated user's ID (works on any route, with or without decorator)."""
    _try_resolve_clerk_user()
    return getattr(g, 'clerk_user_id', None)
