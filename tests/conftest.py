"""pytest 共通フィクスチャ。"""
from __future__ import annotations

import os

import pytest
from starlette.testclient import TestClient

from tests._paths import FIXTURES_DIR, PROJECT_ROOT, TESTS_DIR


@pytest.fixture()
def project_root():
    return PROJECT_ROOT


@pytest.fixture()
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture()
def client():
    os.environ.setdefault("SECRET_KEY", "test-secret")
    import main

    with TestClient(main.app) as c:
        yield c
