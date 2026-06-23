"""
Core DownloadResult dataclass for standardized download results.
"""

from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from .dict_access import DictAccessMixin


@dataclass
class DownloadResult(DictAccessMixin):
    """Standardized download result structure."""
    
    file_path: str
    success: bool = True
    error_message: Optional[str] = None
    
    # Additional metadata for successful downloads
    file_size: Optional[int] = None
    download_time: Optional[float] = None
    format: Optional[str] = None
    quality: Optional[str] = None
    
    # Additional metadata for failed downloads
    retry_count: Optional[int] = None
    backend_used: Optional[str] = None
    
    def __post_init__(self):
        """Validate and clean data after initialization."""
        # Ensure file_path is a string
        if not isinstance(self.file_path, str):
            self.file_path = str(self.file_path)
        
        # Clean file_path (remove extra whitespace)
        self.file_path = self.file_path.strip()
        
        # If success is False, ensure we have an error message
        if not self.success and not self.error_message:
            self.error_message = "Unknown error occurred"
    
    @property
    def file_exists(self) -> bool:
        """Check if the downloaded file actually exists."""
        if not self.success:
            return False
        return Path(self.file_path).exists()
    
    @property
    def file_size_mb(self) -> Optional[float]:
        """Get file size in MB if available."""
        if self.file_size is not None:
            return round(self.file_size / (1024 * 1024), 2)
        return None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for easy serialization."""
        return {
            'file_path': self.file_path,
            'success': self.success,
            'error_message': self.error_message,
            'file_size': self.file_size,
            'download_time': self.download_time,
            'format': self.format,
            'quality': self.quality,
            'retry_count': self.retry_count,
            'backend_used': self.backend_used,
            'file_exists': self.file_exists,
            'file_size_mb': self.file_size_mb
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DownloadResult':
        """Create DownloadResult from dictionary."""
        return cls(**data)
    
    @classmethod
    def success_result(cls, file_path: str, **kwargs) -> 'DownloadResult':
        """Create a successful download result."""
        return cls(file_path=file_path, success=True, **kwargs)
    
    @classmethod
    def failure_result(cls, file_path: str, error_message: str, **kwargs) -> 'DownloadResult':
        """Create a failed download result."""
        return cls(file_path=file_path, success=False, error_message=error_message, **kwargs)
    
    def __str__(self) -> str:
        """String representation for easy debugging."""
        if self.success:
            return f"DownloadResult(success=True, file='{self.file_path}')"
        else:
            return f"DownloadResult(success=False, error='{self.error_message}')"
    
    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return f"DownloadResult(file_path='{self.file_path}', success={self.success}, error_message='{self.error_message}', file_size={self.file_size}, download_time={self.download_time}, format='{self.format}', quality='{self.quality}')"
