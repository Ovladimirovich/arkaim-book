# -*- coding: utf-8 -*-
"""dump_rbac_matrix.py — слепок фактической RBAC-матрицы backend.

Прохождение по include-дереву FastAPI (метод forensic-аудита 2026-09-08):
обход _IncludedRouter/_EffectiveRouteContext, извлечение ролей из
замыканий require_role (router-level dependencies + endpoint-level Depends).

ВАЖНО (поправка 2026-09-08): пути маршрутов в include-дереве НЕ содержат
префиксы родительских композитных роутеров (например /book из
core/book_routes.py). Кросс-проверка: paths в /openapi.json — 289 путей
С префиксами. Поэтому слепок выравнивается по OpenAPI: к каждому
маршруту подбирается соответствующий путь из OpenAPI-спецификации
(совпадение методов + суффиксного соответствия пути).

Выход: contracts/rbac-matrix.json
  { "generated_at": ..., "total_routes": N,
    "routes": [ {"path":..., "methods":[...], "roles":[...]}, ... ] }

Запуск (из arkaim-web-v2/):
  ../runtime/.venv/Scripts/python scripts/dump_rbac_matrix.py

Это DEV-инструмент синхронизации слепка; CI-верификация работает
только от committed JSON (node-only), живой backend не нужен.
"""
import json
import sys
from datetime import date
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[2] / "runtime"
sys.path.insert(0, str(RUNTIME))

from core.main import app  # noqa: E402
from fastapi.routing import APIRoute, _IncludedRouter  # noqa: E402


def _roles_from_callable(fn) -> list:
    roles = []
    for cell in (getattr(fn, "__closure__", None) or ()):
        try:
            v = cell.cell_contents
        except Exception:
            continue
        if isinstance(v, tuple) and v and all(isinstance(x, str) for x in v):
            roles.extend(v)
    return roles


def _ctx_route(ctx):
    for attr in ("route", "api_route", "original_route"):
        r = getattr(ctx, attr, None)
        if isinstance(r, APIRoute):
            return r
    return None


def flatten(routes, out, prefix=""):
    """Обход include-дерева; prefix — накопленные префиксы композитных роутеров.

    У APIRoute.path из include-дерева префиксы родителей уже СТЁРТЫ,
    поэтому собираем их сами: у _IncludedRouter.owner_router есть .prefix
    (префикс композитного роутера), а сам маршрут добавляет свой path.
    """
    for r in routes:
        if isinstance(r, APIRoute):
            out.append((prefix + r.path, r))
        elif isinstance(r, _IncludedRouter):
            owner = getattr(r, "owner_router", None)
            sub_prefix = getattr(owner, "prefix", "") if owner is not None else ""
            flatten(r.effective_candidates(), out, prefix + sub_prefix)
        else:
            inner = _ctx_route(r)
            if isinstance(inner, APIRoute):
                out.append((prefix + inner.path, inner))


def rbac_of(route):
    found = []
    for d in list(route.dependencies or []):
        fn = getattr(d, "dependency", d)
        found.extend(_roles_from_callable(fn))
    import inspect
    try:
        sig = inspect.signature(route.endpoint)
        for p in sig.parameters.values():
            dep = getattr(p.default, "dependency", None)
            if dep is not None:
                found.extend(_roles_from_callable(dep))
    except Exception:
        pass
    return sorted(set(found))


def main():
    # 1. Матрица из include-дерева (пути — как в дереве, без родительских префиксов)
    api_routes = []
    flatten(list(app.routes), api_routes)
    matrix_routes = {}
    for path, r in api_routes:
        methods = tuple(sorted(m for m in r.methods if m not in ("HEAD", "OPTIONS")))
        key = (path, methods)
        if key not in matrix_routes or not matrix_routes[key]:
            matrix_routes[key] = rbac_of(r)

    # 2. Эталон путей — OpenAPI (289 путей, полные пути с префиксами).
    # Матрица может содержать ДВА вида ключей: уже полные (auth, _ui, analytics)
    # и локальные (без /book). Матчим по методу + суффиксу, однозначно.
    openapi = app.openapi()
    openapi_paths = openapi.get("paths", {})

    def op_methods(op):
        return [m for m, spec in openapi_paths[op].items()
                if isinstance(spec, dict) and m in ("get", "post", "put", "delete", "patch")]

    # методы матрицы — UPPERCASE, OpenAPI — lowercase: сравнение регистронезависимо
    def has_op(op, method):
        return method.lower() in op_methods(op)

    routes = []
    unmatched = []
    used_openapi = set()
    for (path, methods), roles in sorted(matrix_routes.items()):
        if path in openapi_paths and all(has_op(path, m) for m in methods):
            # Путь уже полный (например /auth/*) — берём как есть
            routes.append({"path": path, "methods": list(methods), "roles": roles})
            for m in methods:
                used_openapi.add((path, m))
            continue
        # Суффиксный матч: путь матрицы — суффикс полного пути OpenAPI
        cand = [
            (op, m) for op in openapi_paths
            for m in methods
            if op.endswith(path) and has_op(op, m) and (op, m) not in used_openapi
        ]
        # Каждая пара (метод матрицы → полный путь) должна резолвиться однозначно
        by_method = {}
        ok = True
        for m in methods:
            ops_m = [op for (op, mm) in cand if mm == m]
            if len(ops_m) == 1:
                by_method[m] = ops_m[0]
            else:
                ok = False
                break
        if ok and by_method and len(set(by_method.values())) == 1:
            full = next(iter(by_method.values()))
            routes.append({"path": full, "methods": list(methods), "roles": roles})
            for m, op in by_method.items():
                used_openapi.add((op, m))
        else:
            unmatched.append({"path": path, "methods": list(methods), "roles": roles})

    # 3. Unmatched сохраняем как есть (не теряем данные слепка)
    for u in unmatched:
        routes.append(u)

    routes.sort(key=lambda x: (x["path"], ",".join(sorted(x["methods"]))))
    matrix = {
        "generated_at": date.today().isoformat(),
        "source": "runtime/core/main.py (живой импорт; пути выровнены с /openapi.json)",
        "total_routes": len(routes),
        "total_openapi_paths": len(openapi_paths),
        "unmatched": len(unmatched),
        "routes": routes,
    }
    out = Path(__file__).resolve().parents[1] / "contracts" / "rbac-matrix.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"rbac-matrix: {len(routes)} routes (unmatched-as-is: {len(unmatched)}, openapi paths: {len(openapi_paths)}) -> {out}")


if __name__ == "__main__":
    main()
