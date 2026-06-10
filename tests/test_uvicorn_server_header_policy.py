import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _uvicorn_run_calls(path: Path) -> list[ast.Call]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "run"
            and isinstance(func.value, ast.Name)
            and func.value.id == "uvicorn"
        ):
            calls.append(node)
    return calls


def _kwarg(call: ast.Call, name: str):
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _is_false_literal(node) -> bool:
    return isinstance(node, ast.Constant) and node.value is False


def test_tracked_uvicorn_entrypoints_suppress_server_headers():
    for rel_path in ("app/main.py", "scan_server.py", "payment_server.py"):
        calls = _uvicorn_run_calls(ROOT / rel_path)
        assert calls, f"{rel_path} must contain a uvicorn.run call"
        for call in calls:
            assert _is_false_literal(_kwarg(call, "server_header")), rel_path
            assert _is_false_literal(_kwarg(call, "date_header")), rel_path
