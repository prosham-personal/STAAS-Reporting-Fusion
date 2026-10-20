"""Read-only smoke tests against a real Fusion fleet member.

Skipped unless PURE_FUSION_SERVER, PURE_USER_NAME and PURE_API_TOKEN are set (use a
read-only lab array and an account with read access, never production). Run with:

    uv run pytest -m live tests/test_live_array.py

These tests never tag, create or delete anything.
"""
import os

import pytest

from staas_common import check_api_version, initialise_client, list_fleets, list_members

pytestmark = pytest.mark.live

REQUIRED = ("PURE_FUSION_SERVER", "PURE_USER_NAME", "PURE_API_TOKEN")


@pytest.fixture(scope="module")
def client():
    missing = [v for v in REQUIRED if not os.environ.get(v)]
    if missing:
        pytest.skip(f"set {', '.join(missing)} to run live tests")
    c = initialise_client(
        os.environ["PURE_FUSION_SERVER"], os.environ["PURE_USER_NAME"], os.environ["PURE_API_TOKEN"]
    )
    assert c is not None, "could not create a client (check server, user and token)"
    return c


def test_api_version_meets_minimum(client):
    assert check_api_version(client, 2.42)


def test_fleets_and_members(client):
    fleets = list_fleets(client)
    assert fleets, "no fleets visible to this account"
    assert list_members(client, fleets), "fleet has no members"


def test_volumes_readable(client):
    members = list_members(client, list_fleets(client))
    response = client.get_volumes(context_names=[members[0]], limit=1)
    assert response.status_code == 200
