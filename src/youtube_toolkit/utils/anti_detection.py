import time
import random
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

@dataclass
class RequestRecord:
    """Record of a request for analytics."""
    timestamp: datetime
    url: str
    method: str
    success: bool
    response_time: float
    user_agent: str

class RequestAnalytics:
    """Track request patterns to optimize anti-detection."""
    
    def __init__(self, window_minutes: int = 60):
        self.window_minutes = window_minutes
        self.requests: List[RequestRecord] = []
        self.lock = threading.Lock()
    
    def record_request(self, url: str, method: str, success: bool, 
                      response_time: float, user_agent: str):
        """Record a request for analysis."""
        with self.lock:
            record = RequestRecord(
                timestamp=datetime.now(),
                url=url, method=method, success=success,
                response_time=response_time, user_agent=user_agent
            )
            self.requests.append(record)
            
            # Clean old records
            cutoff = datetime.now() - timedelta(minutes=self.window_minutes)
            self.requests = [r for r in self.requests if r.timestamp > cutoff]
    
    def get_recent_requests(self, minutes: int = 5) -> List[RequestRecord]:
        """Get requests from the last N minutes."""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [r for r in self.requests if r.timestamp > cutoff]
    
    def get_request_frequency(self, minutes: int = 5) -> float:
        """Get requests per minute in the last N minutes."""
        recent = self.get_recent_requests(minutes)
        if not recent:
            return 0.0
        return len(recent) / minutes
    
    def get_success_rate(self, minutes: int = 10) -> float:
        """Get success rate in the last N minutes."""
        recent = self.get_recent_requests(minutes)
        if not recent:
            return 1.0
        successful = sum(1 for r in recent if r.success)
        return successful / len(recent)

class StealthSession:
    """Enhanced session with anti-detection capabilities."""
    
    def __init__(self):
        self.session = requests.Session()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0'
        ]
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set initial headers
        self._update_headers()
    
    def _update_headers(self):
        """Update session headers with stealth values."""
        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
    
    def rotate_user_agent(self):
        """Rotate to a different user agent."""
        self._update_headers()
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """Make a GET request with stealth measures."""
        return self.session.get(url, **kwargs)
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """Make a POST request with stealth measures."""
        return self.session.post(url, **kwargs)

class AntiDetectionManager:
    """Centralized anti-detection manager for all handlers."""
    
    def __init__(self):
        self.stealth_session = StealthSession()
        self.analytics = RequestAnalytics()
        self.last_request_time = 0
        self.min_delay = 1.0  # Minimum delay between requests
        self.max_delay = 5.0   # Maximum delay between requests
        self.lock = threading.Lock()
    
    def apply_delay(self):
        """Apply intelligent delay based on analytics."""
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            
            # Base delay
            base_delay = random.uniform(self.min_delay, self.max_delay)
            
            # Adjust based on recent activity
            recent_freq = self.analytics.get_request_frequency(5)
            if recent_freq > 2.0:  # More than 2 requests per minute
                base_delay *= 2
            elif recent_freq > 5.0:  # More than 5 requests per minute
                base_delay *= 3
            
            # Adjust based on success rate
            success_rate = self.analytics.get_success_rate(10)
            if success_rate < 0.8:  # Low success rate
                base_delay *= 1.5
            
            # Ensure minimum delay
            actual_delay = max(base_delay, self.min_delay)
            
            # Wait if needed
            if time_since_last < actual_delay:
                sleep_time = actual_delay - time_since_last
                time.sleep(sleep_time)
            
            self.last_request_time = time.time()
    
    def get_stealth_headers(self) -> Dict[str, str]:
        """Get stealth headers for requests."""
        return dict(self.stealth_session.session.headers)
    
    def randomize_request_behavior(self):
        """Randomize request behavior to appear more human."""
        # Randomly rotate user agent
        if random.random() < 0.3:  # 30% chance
            self.stealth_session.rotate_user_agent()
        
        # Random small delay
        if random.random() < 0.5:  # 50% chance
            time.sleep(random.uniform(0.1, 0.5))
    
    def safe_request(self, url: str, method: str = 'get', **kwargs) -> Optional[requests.Response]:
        """Make a safe request with all anti-detection measures."""
        try:
            # Apply anti-detection measures
            self.apply_delay()
            self.randomize_request_behavior()
            
            # Make the request
            start_time = time.time()
            if method.lower() == 'get':
                response = self.stealth_session.get(url, **kwargs)
            elif method.lower() == 'post':
                response = self.stealth_session.post(url, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response_time = time.time() - start_time
            
            # Record the request
            success = response.status_code < 400
            self.analytics.record_request(
                url=url, method=method, success=success,
                response_time=response_time,
                user_agent=self.stealth_session.session.headers.get('User-Agent', '')
            )
            
            return response
            
        except Exception as e:
            # Record failed request
            self.analytics.record_request(
                url=url, method=method, success=False,
                response_time=0.0,
                user_agent=self.stealth_session.session.headers.get('User-Agent', '')
            )
            raise e
    
    def get_status(self) -> Dict[str, Any]:
        """Get current anti-detection status."""
        return {
            'recent_requests': len(self.analytics.get_recent_requests(5)),
            'request_frequency': self.analytics.get_request_frequency(5),
            'success_rate': self.analytics.get_success_rate(10),
            'last_request': datetime.fromtimestamp(self.last_request_time).isoformat() if self.last_request_time > 0 else 'Never',
            'current_user_agent': self.stealth_session.session.headers.get('User-Agent', 'Unknown')
        }
