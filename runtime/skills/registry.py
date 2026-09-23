import importlib
import importlib.util
import logging
import pkgutil
from pathlib import Path

from skills.base import Skill

log = logging.getLogger(__name__)


def _load_skill_from_file(filepath: Path, modname: str):
    spec = importlib.util.spec_from_file_location(modname, str(filepath))
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {filepath}")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _collect_skills_from(module) -> list[Skill]:
    return [
        attr()
        for attr_name in dir(module)
        for attr in [getattr(module, attr_name)]
        if isinstance(attr, type) and issubclass(attr, Skill) and attr is not Skill
    ]


class SkillRegistry:
    @classmethod
    def discover(cls, business_pack: str | None = None) -> list[Skill]:
        skills = []

        # 1. Discover runtime built-in skills
        runtime_skills = Path(__file__).resolve().parent
        for importer, modname, is_pkg in pkgutil.iter_modules([str(runtime_skills)]):
            if is_pkg or modname in ("registry", "base"):
                continue
            try:
                module = importlib.import_module(f"skills.{modname}")
                skills.extend(_collect_skills_from(module))
            except Exception as exc:
                log.warning("skill_discover_error module=%s error=%s", modname, exc)

        # 2. Load business pack skills
        if business_pack:
            bp = Path(business_pack).resolve()
            bp_skills = bp / "skills"
            if bp_skills.is_dir():
                # Pre-register _synonyms module
                syn_file = bp_skills / "_synonyms.py"
                if syn_file.exists():
                    import sys
                    if "skills._synonyms" not in sys.modules:
                        spec = importlib.util.spec_from_file_location("skills._synonyms", str(syn_file))
                        if spec and spec.loader:
                            m = importlib.util.module_from_spec(spec)
                            sys.modules["skills._synonyms"] = m
                            spec.loader.exec_module(m)
                # Load each skill file
                for f in sorted(bp_skills.iterdir()):
                    if f.suffix != ".py" or f.name.startswith("_") or f.name == "__init__.py":
                        continue
                    try:
                        module = _load_skill_from_file(f, f"__bp_{f.stem}__")
                        skills.extend(_collect_skills_from(module))
                    except Exception as exc:
                        log.warning("bp_skill_load_error file=%s error=%s", f.name, exc)

        skills.sort(key=lambda s: s.priority)
        log.info("skills_discovered count=%d", len(skills))
        return skills
