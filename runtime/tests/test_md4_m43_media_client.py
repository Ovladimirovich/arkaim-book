"""DELETED: MediaClient bridge route tests.

The routes tested here (/comfyui/status, /providers/list, /assets/generate
through MediaClient bridge) have been removed from Arkaim (Arkaim Media Boundary ADR).
MediaClient module itself remains as the sanctioned bridge for future
arkaim-media connection, but no routes expose it.
This test file is kept as a stub to document the removal.
"""
import pytest

@pytest.mark.skip(reason="Bridge routes removed from Arkaim (Media Boundary ADR)")
def test_bridge_routes_removed():
    pass
