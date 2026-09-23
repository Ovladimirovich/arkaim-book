"""Core architecture tests."""

from tests.test_contract import _module_imports_forbidden


class TestCoreIsolation:
    def test_core_does_not_import_gateway(self):
        assert not _module_imports_forbidden("core.main", "gateway"), "Core must NOT import gateway"

    def test_core_does_not_import_integrations(self):
        assert not _module_imports_forbidden("core.main", "integrations"), "Core must NOT import integrations"
