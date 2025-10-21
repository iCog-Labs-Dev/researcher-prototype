from fastapi import status


class CommonError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    headers: dict[str, str] = {}


class AlreadyExist(CommonError):
    status_code = status.HTTP_409_CONFLICT


class AuthError(CommonError):
    status_code = status.HTTP_401_UNAUTHORIZED
    headers = {"WWW-Authenticate": "Bearer"}


class PasswordError(CommonError):
    pass
