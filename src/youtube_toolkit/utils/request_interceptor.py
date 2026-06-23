import functools
import threading
import time
from typing import Callable, Any

def anti_detection_interceptor(func: Callable) -> Callable:
    """
    Decorator that automatically applies anti-detection measures to any method.
    
    The decorated method must be part of a class that has an 'anti_detection'
    attribute (AntiDetectionManager instance).
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # Check if the handler has anti-detection
        if hasattr(self, 'anti_detection') and self.anti_detection:
            # Apply anti-detection measures
            self.anti_detection.apply_delay()
            self.anti_detection.randomize_request_behavior()
        
        # Call the original method
        return func(self, *args, **kwargs)
    
    return wrapper

def rate_limit(max_requests: int = 10, window_minutes: int = 1):
    """
    Decorator for rate limiting methods.
    
    Args:
        max_requests: Maximum requests allowed in the time window
        window_minutes: Time window in minutes
    """
    def decorator(func: Callable) -> Callable:
        # Store rate limit data on the function
        if not hasattr(func, '_rate_limit_data'):
            func._rate_limit_data = {
                'requests': [],
                'max_requests': max_requests,
                'window_minutes': window_minutes
            }
            # Guard the shared 'requests' list so concurrent callers (Phase 5
            # thread-pool fan-out) cannot race on clean/check/sleep/append.
            func._rate_limit_lock = threading.Lock()

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            rate_data = func._rate_limit_data
            # The whole accounting step (clean -> check -> sleep -> record) is a
            # single critical section; an uncontended lock leaves single-threaded
            # behaviour identical.
            with func._rate_limit_lock:
                current_time = time.time()
                window_seconds = rate_data['window_minutes'] * 60

                # Clean old requests
                rate_data['requests'] = [
                    req_time for req_time in rate_data['requests']
                    if current_time - req_time < window_seconds
                ]

                # Check if we can make a request
                if len(rate_data['requests']) >= rate_data['max_requests']:
                    oldest_request = min(rate_data['requests'])
                    wait_time = window_seconds - (current_time - oldest_request)
                    if wait_time > 0:
                        time.sleep(wait_time)

                # Record this request
                rate_data['requests'].append(current_time)

            # Call the original method
            return func(self, *args, **kwargs)
        
        return wrapper
    return decorator
