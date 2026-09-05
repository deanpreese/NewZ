"""Shared fixtures for the phases that have a store."""

from __future__ import annotations

import pytest

from newz.catalog import epochs
from newz.control.budget import DailyBudget
from newz.store.db import open_store
from tests import canaries


@pytest.fixture
def store(tmp_path):
    opened = open_store(tmp_path / "newz.db", tmp_path / "artifacts")
    yield opened
    opened.close()


@pytest.fixture
def catalog(store):
    """The four canary sources, enabled in epoch 1."""
    canaries.install(store)
    plan = epochs.plan(
        store,
        [canary.revision.id for canary in canaries.CANARIES],
        DailyBudget(),
    )
    epochs.activate(store, plan, "epoch:1", "the canary diet", "operator:dean")
    return store


@pytest.fixture
def transport():
    return canaries.transport_for()
