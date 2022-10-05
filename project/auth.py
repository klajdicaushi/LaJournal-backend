from ninja.security import HttpBearer

from project.services import UserService


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        user = UserService.get_user_by_token(token)
        if not user:
            raise InvalidToken
        return user


class InvalidCredentials(Exception):
    pass


class InvalidToken(Exception):
    pass
