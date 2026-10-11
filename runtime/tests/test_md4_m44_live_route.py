"""DELETED: live route generation tests.

These tests verified /assets/generate through the MediaClient bridge with a
live Media server. The generation routes have been removed from Arkaim
(Arkaim Media Boundary ADR). Generation execution now lives in arkaim-media.
This test file is kept as a stub to document the removal.
"""

import pytest


@pytest.mark.skip(reason="Live generation routes removed from Arkaim (Media Boundary ADR)")
def test_live_routes_removed():
    pass
