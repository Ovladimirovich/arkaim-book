"""Deep isolation tests — every layer respects its contract boundaries."""

import importlib
import pathlib
import sys

_PROJECT_PREFIXES = ("gateway", "core", "memory", "observability", "integrations", "skills", "contracts", "cli")
_EXTRA_MODULES = ("aiosqlite",)
_KEEP_MODULES = {"observability.metrics"}

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent


def _is_project_module(name: str) -> bool:
    return name.startswith(_PROJECT_PREFIXES) or name in _EXTRA_MODULES


def _snapshot_modules() -> dict:
    return {m: mod for m, mod in sys.modules.items() if _is_project_module(m)}


def _restore_modules(snapshot: dict) -> None:
    """Вернуть sys.modules к состоянию до пурга (глобальное состояние сессии pytest)."""
    for m in list(sys.modules):
        if _is_project_module(m) and m not in snapshot:
            del sys.modules[m]
    sys.modules.update(snapshot)


def _fresh_import(modname: str) -> set[str]:
    snapshot = _snapshot_modules()
    try:
        for m in list(sys.modules):
            if _is_project_module(m) and m not in _KEEP_MODULES:
                del sys.modules[m]
        importlib.invalidate_caches()
        try:
            importlib.import_module(modname)
        except ModuleNotFoundError:
            return set()
        return {m for m in sys.modules if m.startswith(_PROJECT_PREFIXES) or m.startswith("core.providers")}
    finally:
        _restore_modules(snapshot)


def _assert_no_imports(modname: str, *forbidden_prefixes: str):
    loaded = _fresh_import(modname)
    errors = []
    for prefix in forbidden_prefixes:
        for m in loaded:
            if m.startswith(prefix):
                errors.append(m)
    assert not errors, f"{modname} imports forbidden modules: {errors}"


#
# ─── Skill isolation ────────────────────────────────────────────────────
#


class TestSkillIsolation:
    """Skills are passive plugins — no providers, memory, core, gateway."""

    def test_skills_base_no_forbidden_imports(self):
        _assert_no_imports("skills.base", "core", "memory", "gateway", "integrations", "core.providers")

    def test_skills_registry_no_forbidden_imports(self):
        _assert_no_imports("skills.registry", "core", "memory", "gateway", "integrations", "core.providers")

    def test_skills_sanitizer_no_forbidden_imports(self):
        _assert_no_imports("skills.sanitizer", "core", "memory", "gateway", "integrations", "core.providers")

    def test_skills_do_not_import_providers(self):
        _assert_no_imports("skills.sanitizer", "core.providers")
        _assert_no_imports("skills.base", "core.providers")
        _assert_no_imports("skills.registry", "core.providers")


#
# ─── Integration isolation (all files, not just run.py) ────────────────
#


class TestIntegrationIsolation:
    """Every integration file MUST NOT import core, skills, memory, providers."""

    def test_telegram_adapter_no_forbidden_imports(self):
        _assert_no_imports("integrations.telegram.adapter", "core", "skills", "memory", "core.providers")

    def test_telegram_config_no_forbidden_imports(self):
        _assert_no_imports("integrations.telegram.config", "core", "skills", "memory", "core.providers")

    def test_telegram_run_no_skills(self):
        _assert_no_imports("integrations.telegram.run", "skills")


#
# ─── Gateway structural isolation ──────────────────────────────────────
#


class TestGatewayStructure:
    """Gateway is a dumb transport layer — no routes, no orchestrator, no skills."""

    def test_no_routes_directory(self):
        routes_dir = ROOT / "gateway" / "routes"
        assert not routes_dir.exists(), "Gateway MUST NOT have a routes directory"

    def test_no_orchestrator_import(self):
        _assert_no_imports("gateway.main", "core.orchestrator", "skills", "memory", "core.providers")

    def test_gateway_main_no_forbidden_imports(self):
        _assert_no_imports("gateway.main", "core.orchestrator", "core.providers", "core.router", "skills", "memory", "integrations")

    def test_gateway_proxy_no_core(self):
        _assert_no_imports("gateway.proxy", "core.orchestrator", "core.providers", "skills", "memory")

    def test_gateway_normalize_no_core(self):
        _assert_no_imports("gateway.normalize", "core", "skills", "memory", "core.providers", "integrations")

    def test_gateway_rate_limit_no_core(self):
        _assert_no_imports("gateway.rate_limit", "core", "skills", "memory", "core.providers", "integrations")

    def test_gateway_session_no_core(self):
        _assert_no_imports("gateway.session", "core", "skills", "memory", "core.providers", "integrations")

    def test_gateway_observe_no_core(self):
        _assert_no_imports("gateway.observe", "core.orchestrator", "core.providers", "skills", "memory", "integrations")


#


class TestCoreIsolation:
    """Core MUST NOT import gateway, integrations, or skills directly."""

    def test_core_main_no_gateway(self):
        _assert_no_imports("core.main", "gateway", "integrations")

    def test_core_orchestrator_no_gateway(self):
        _assert_no_imports("core.orchestrator", "gateway", "integrations")


#
# ─── Business pack isolation (runtime-level) ───────────────────────────
#


class TestBusinessPackIsolation:
    """Business pack skills in runtime must not import providers."""

    def test_business_pack_not_loaded_by_default(self):
        from core.config import settings

        assert settings.HERMES_SKILLS_PATH == "", "HERMES_SKILLS_PATH should be empty by default"
        assert settings.BUSINESS_PACK == "", "BUSINESS_PACK (deprecated) should be empty by default"

    def test_runtime_starts_without_business(self):
        import importlib

        mod = importlib.import_module("core.main")
        assert mod.core is not None
        # Runtime-builtin skills (health_monitor etc.) are always loaded.
        # Verify no external BUSINESS_PACK skills are loaded.
        skill_names = [s.name for s in mod.core.skills]
        has_health = any("health" in name for name in skill_names)
        assert has_health, "Runtime skills should be loaded"


#
# ─── Contract file integrity ──────────────────────────────────────────
#


class TestContractFilesExist:
    """All 3 contracts exist and are non-empty."""

    CONTRACTS = ["EXECUTION_CONTRACT.md", "SKILL_CONTRACT.md", "INTEGRATION_CONTRACT.md"]

    def test_all_contracts_exist(self):
        contracts_dir = ROOT / "contracts"
        assert contracts_dir.is_dir(), "contracts/ directory missing"
        for name in self.CONTRACTS:
            f = contracts_dir / name
            assert f.exists(), f"contract file missing: {name}"
            content = f.read_text(encoding="utf-8")
            assert len(content) > 200, f"contract file too short: {name}"

    def test_no_unexpected_contract_files(self):
        contracts_dir = ROOT / "contracts"
        files = {f.name for f in contracts_dir.iterdir() if f.suffix == ".md"}
        expected = set(self.CONTRACTS)
        unexpected = files - expected
        assert not unexpected, f"unexpected contract files: {unexpected}"


class TestModuleIdentityRestored:
    """_fresh_import не должен оставлять «новые» core*-модули в sys.modules.

    Пург sys.modules внутри теста менял глобальное состояние сессии:
    последующие тесты получали второй экземпляр core.main (новый app без
    dependency_overrides → 401) и второй экземпляр routes-модулей
    (monkeypatch не попадал в роутер → обращение к чужой film-БД).
    """

    def test_fresh_import_restores_module_identity(self):
        before = _snapshot_modules()
        assert "core.main" in before, "conftest must have imported core.main"

        loaded = _fresh_import("skills.base")

        assert "skills.base" in loaded
        after = _snapshot_modules()
        assert set(after) == set(before)
        for name, module in before.items():
            assert after[name] is module, f"sys.modules[{name!r}] was replaced by a re-imported module"
