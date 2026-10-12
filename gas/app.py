import logging

# import sentry_sdk
from fastapi import FastAPI
from fastapi_mcp import FastApiMCP

# from sentry_sdk.integrations.fastapi import FastApiIntegration
# from sentry_sdk.integrations.starlette import StarletteIntegration
from gas import constants
from gas.constants import SwaggerTags
from gas.core.settings import get_settings
from gas.routes import delivery, menu, order

settings = get_settings()

# sentry_sdk.init(
#     dsn=settings.SENTRY_DSN,
#     send_default_pii=True,
#     environment=settings.ENVIRONMENT,
#     integrations=[
#         StarletteIntegration(
#             transaction_style="endpoint",
#             failed_request_status_codes={403, *range(500, 599)},
#         ),
#         FastApiIntegration(
#             transaction_style="endpoint",
#             failed_request_status_codes={403, *range(500, 599)},
#         ),
#     ],
# )


logging.basicConfig(level=settings.LOG_LEVEL.upper())

app = FastAPI(debug=settings.ENVIRONMENT != "prod", root_path=settings.PROXY_PATH_PREFIX)

app.include_router(delivery.router)
app.include_router(menu.router)
app.include_router(order.router)


mcp = FastApiMCP(
    app,
    include_tags=[SwaggerTags.MCP],
    describe_all_responses=True,
    describe_full_response_schema=True,
    headers=[
        "authorization",
        constants.HEADER_MCP_SESSION_ID_KEY,
        "x-call-id",
        "x-chat-id",
        "x-client-id",
    ],
)
mcp.mount_http()
