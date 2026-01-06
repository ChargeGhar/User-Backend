from __future__ import annotations

import functools
import logging
from typing import Callable, Any
from django.core.cache import cache
from django.utils import timezone
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


def log_api_call(include_request_data: bool = False, include_response_data: bool = False):
    """Decorator for logging API calls"""
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            start_time = timezone.now()
            
            # Log request
            log_data = {
                'view': self.__class__.__name__,
                'method': request.method,
                'path': request.path,
                'user': str(request.user) if request.user.is_authenticated else 'anonymous',
                'ip': request.META.get('REMOTE_ADDR', 'unknown'),
                'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown')
            }
            
            if include_request_data and hasattr(request, 'data'):
                # Don't log sensitive data
                safe_data = {k: v for k, v in request.data.items() 
                           if k not in ['password', 'token', 'otp']}
                log_data['request_data'] = safe_data
            
            try:
                response = view_func(self, request, *args, **kwargs)
                
                # Calculate response time
                end_time = timezone.now()
                response_time = (end_time - start_time).total_seconds() * 1000
                
                log_data.update({
                    'status_code': response.status_code,
                    'response_time_ms': round(response_time, 2)
                })
                
                if include_response_data and hasattr(response, 'data'):
                    log_data['response_data'] = response.data
                
                # Log based on status code
                if response.status_code >= 500:
                    logger.error("API call failed", extra=log_data)
                elif response.status_code >= 400:
                    logger.warning("API call error", extra=log_data)
                else:
                    logger.info("API call success", extra=log_data)
                
                return response
                
            except Exception as e:
                end_time = timezone.now()
                response_time = (end_time - start_time).total_seconds() * 1000
                
                log_data.update({
                    'exception': str(e),
                    'response_time_ms': round(response_time, 2)
                })
                
                logger.error("API call exception", extra=log_data)
                raise
        
        return wrapper
    return decorator

