"""
API client error classes
"""

class ApiError(Exception):
    """Base API error"""
    pass

class AuthenticationError(ApiError):
    """Authentication failed"""
    pass

class ValidationError(ApiError):
    """Validation error"""
    pass

class NetworkError(ApiError):
    """Network error"""
    pass

class NotFoundError(ApiError):
    """Resource not found"""
    pass
