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

def clerk_auth_required(f):
    """Decorator to protect routes with Clerk authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If Clerk is not configured, redirect to login
        if not clerk_sdk:
            session['next_url'] = request.url
            return redirect(url_for('clerk_login'))
        
        # Get session token from cookie or Authorization header
        auth_token = None
        
        # Check Authorization header first
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            auth_token = auth_header.replace('Bearer ', '')
        
        # Check for __session cookie (Clerk's default cookie name)
        if not auth_token:
            auth_token = request.cookies.get('__session')
        
        if not auth_token:
            # Not authenticated - redirect to login
            session['next_url'] = request.url
            return redirect(url_for('clerk_login'))
        
        try:
            # Verify the token using Clerk's authenticate_request
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
            
            if not request_state.is_signed_in:
                session['next_url'] = request.url
                return redirect(url_for('clerk_login'))
            
            # Store user info in Flask's g object for use in the route
            if hasattr(request_state, 'payload') and request_state.payload:
                g.clerk_user_id = request_state.payload.get('sub')
            
        except Exception as e:
            print(f"Clerk auth error: {e}")
            session['next_url'] = request.url
            return redirect(url_for('clerk_login'))
        
        return f(*args, **kwargs)
    
    return decorated_function

def get_clerk_user():
    """Get the current authenticated Clerk user"""
    if not clerk_sdk or not hasattr(g, 'clerk_user_id'):
        return None
    
    try:
        user = clerk_sdk.users.get(user_id=g.clerk_user_id)
        return user
    except Exception as e:
        print(f"Error fetching Clerk user: {e}")
        return None

def get_clerk_user_id():
    """Get the current authenticated user's ID"""
    return getattr(g, 'clerk_user_id', None)
