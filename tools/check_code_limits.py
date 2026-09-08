#!/usr/bin/env python3
"""Enforce the structural code limits from §14.1 that linters omit.

Checks, per Python file under the given paths:

* at most 5 public functions/methods (names not starting with ``_``);
* at most 25 real code lines per function body (blank lines, comments
  and the docstring do not count).

Line length, cyclomatic complexity and nesting depth are enforced by
ruff; this script covers only the two limits ruff cannot express.

Usage: ``python tools/check_code_limits.py app``
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

MAX_PUBLIC_FUNCS = 5
MAX_BODY_LINES = 25

Function = ast.FunctionDef | ast.AsyncFunctionDef


def _is_public(name: str) -> bool:
    """Return whether ``name`` denotes a public function/method."""
    return not name.startswith("_")


def _body_lines(func: Function, lines: list[str]) -> int:
    """Count real code lines in a function body."""
    body = func.body
    first = body[0]
    start = first.lineno
    if _is_docstring(first):
        if len(body) == 1:
            return 0
        start = body[1].lineno
    end = func.end_lineno or start
    return sum(
        1
        for number in range(start, end + 1)
        if _is_code(lines[number - 1])
    )


def _is_docstring(node: ast.stmt) -> bool:
    """Return whether ``node`` is a docstring expression."""
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _is_code(line: str) -> bool:
    """Return whether a source line carries executable code."""
    stripped = line.strip()
    return bool(stripped) and not stripped.startswith("#")


def _check_file(path: Path) -> list[str]:
    """Return the list of limit violations found in ``path``."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines()
    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    problems = _long_bodies(path, functions, lines)
    problems.extend(_too_many_public(path, tree))
    return problems


def _long_bodies(
    path: Path, functions: list[Function], lines: list[str]
) -> list[str]:
    """Report functions whose body exceeds the line limit."""
    problems: list[str] = []
    for func in functions:
        length = _body_lines(func, lines)
        if length > MAX_BODY_LINES:
            problems.append(
                f"{path}:{func.lineno} {func.name}(): "
                f"{length} body lines > {MAX_BODY_LINES}"
            )
    return problems


def _too_many_public(path: Path, tree: ast.Module) -> list[str]:
    """Report files declaring too many public functions/methods."""
    count = sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and _is_public(node.name)
    )
    if count > MAX_PUBLIC_FUNCS:
        return [f"{path}: {count} public functions > {MAX_PUBLIC_FUNCS}"]
    return []


def main(argv: list[str]) -> int:
    """Scan the given paths and print any violations."""
    roots = [Path(arg) for arg in argv] or [Path("app")]
    problems: list[str] = []
    for root in roots:
        files = root.rglob("*.py") if root.is_dir() else [root]
        for path in sorted(files):
            problems.extend(_check_file(path))
    for problem in problems:
        print(problem)
    print(f"checked limits: {len(problems)} violation(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
