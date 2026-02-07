from __future__ import annotations

import functools
import logging
from typing import Callable, Any
from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def cached_response(timeout: int = 300, key_func: Callable = None):
    """Decorator for caching view responses"""
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(self, request, *args, **kwargs)
            else:
                view_name = self.__class__.__name__
                user_id = getattr(request.user, 'id', 'anonymous')
                cache_key = f"{view_name}:{user_id}:{hash(str(args) + str(kwargs))}"
            
            try:
                # Try to get from cache
                cached_response = cache.get(cache_key)
                if cached_response is not None:
                    return Response(cached_response)
                
                # Cache miss - execute view
                response = view_func(self, request, *args, **kwargs)
                
                # Cache successful responses only
                if response.status_code == status.HTTP_200_OK:
                    cache.set(cache_key, response.data, timeout=timeout)
                
                return response
                
            except Exception as e:
                logger.error(f"Cache decorator error: {str(e)}")
                # Fallback to normal execution
                return view_func(self, request, *args, **kwargs)
        
        return wrapper
    return decorator


def rate_limit(max_requests: int = 5, window_seconds: int = 60):
    """Decorator for rate limiting endpoints"""
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            # Generate rate limit key
            user_id = getattr(request.user, 'id', None)
            ip_address = request.META.get('REMOTE_ADDR', 'unknown')
            identifier = str(user_id) if user_id else ip_address
            
            rate_key = f"rate_limit:{view_func.__name__}:{identifier}"
            
            try:
                # Get current request count
                current_requests = cache.get(rate_key, 0)
                
                if current_requests >= max_requests:
                    return Response({
                        'success': False,
                        'error': {
                            'code': 'rate_limit_exceeded',
                            'message': f'Rate limit exceeded. Max {max_requests} requests per {window_seconds} seconds.'
                        }
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)
                
                # Increment counter
                cache.set(rate_key, current_requests + 1, timeout=window_seconds)
                
                return view_func(self, request, *args, **kwargs)
                
            except Exception as e:
                logger.error(f"Rate limit decorator error: {str(e)}")
                # Fallback to normal execution
                return view_func(self, request, *args, **kwargs)
        
        return wrapper
    return decorator


def log_api_call(include_request_data: bool = False):
    """
    Decorator for logging API calls with accurate, useful output.
    
    Logs: METHOD /path View.method user=X status=200 42ms
    
    - Only logs warnings for 4xx, errors for 5xx/exceptions
    - Successful GET requests logged at DEBUG to reduce noise
    - Mutating requests (POST/PUT/PATCH/DELETE) always logged at INFO
    - Optionally includes request body (sensitive fields auto-redacted)
    """
    # Sensitive fields that should never appear in logs
    REDACTED_FIELDS = frozenset({
        'password', 'token', 'otp', 'pin', 'secret',
        'access_token', 'refresh_token', 'credit_card',
        'card_number', 'cvv', 'biometric_data',
    })

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            import time
            start = time.monotonic()

            view_name = self.__class__.__name__
            method = request.method
            path = request.path
            user = str(request.user) if request.user.is_authenticated else 'anon'

            try:
                response = view_func(self, request, *args, **kwargs)
                elapsed_ms = round((time.monotonic() - start) * 1000, 1)
                status_code = response.status_code

                # Build log line — everything a developer needs in one glance
                msg = f"{method} {path} {view_name}.{view_func.__name__} user={user} status={status_code} {elapsed_ms}ms"

                # Append request body for mutating endpoints if opted-in
                if include_request_data and method in ('POST', 'PUT', 'PATCH') and hasattr(request, 'data'):
                    safe = {k: '***' if k in REDACTED_FIELDS else v for k, v in request.data.items()}
                    msg += f" body={safe}"

                # Log level based on status code
                if status_code >= 500:
                    logger.error(msg)
                elif status_code >= 400:
                    logger.warning(msg)
                elif method in ('POST', 'PUT', 'PATCH', 'DELETE'):
                    # Mutating requests always at INFO
                    logger.info(msg)
                else:
                    # GET/HEAD/OPTIONS at DEBUG — keeps production logs clean
                    logger.debug(msg)

                return response

            except Exception as e:
                elapsed_ms = round((time.monotonic() - start) * 1000, 1)
                logger.error(
                    f"{method} {path} {view_name}.{view_func.__name__} user={user} "
                    f"EXCEPTION {e.__class__.__name__}: {e} {elapsed_ms}ms"
                )
                raise

        return wrapper
    return decorator

