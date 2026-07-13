"""
自定義應用異常定義
"""
from fastapi import HTTPException, status


class AppException(Exception):
    """應用基礎異常"""
    pass


class ValidationException(AppException):
    """驗證異常"""
    pass


class AuthenticationException(AppException):
    """認證異常"""
    pass


class AuthorizationException(AppException):
    """授權異常"""
    pass


class ResourceNotFoundException(AppException):
    """資源未找到異常"""
    pass


class ConflictException(AppException):
    """衝突異常 (如重複的資源)"""
    pass


class InvalidOperationException(AppException):
    """無效操作異常"""
    pass
