from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyCookie
from fastapi.security.api_key import APIKeyHeader
from fastapi.security.oauth2 import OAuth2PasswordBearer

from gas import constants

header_schema = APIKeyHeader(name=constants.HEADER_MCP_SESSION_ID_KEY, auto_error=False)
cookie_scheme = APIKeyCookie(name=constants.COOKIE_SESSION_ID_KEY, auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/oauth2/token", auto_error=False)


def get_session_id(
    header_session_id: Annotated[str, Depends(header_schema)],
    cookie_session_id: Annotated[str, Depends(cookie_scheme)],
):
    session_id = cookie_session_id or header_session_id
    if not session_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return session_id
