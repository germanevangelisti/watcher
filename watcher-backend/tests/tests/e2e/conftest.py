"""E2E conftest: restrict anyio to asyncio backend (trio not installed)."""
import pytest


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param
