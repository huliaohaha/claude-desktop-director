#!/usr/bin/env python3
"""Offline package format/link/fixture checks, not model evals or a send gate.

No evidence references, fixture instructions or Markdown commands are executed.
This deliberately supports this package's single-line YAML subset only.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
SKILL_NAME = 'claude-desktop-director'


class PackageError(ValueError):
    pass


def package_path(root: Path, path: Path) -> Path:
    """Reject escapes and symlink components before reading package content."""
    root = root.resolve()
    path = Path(os.path.abspath(path if path.is_absolute() else root / path))
    if not path.is_relative_to(root):
        raise PackageError('path escapes package: ' + str(path))
    component = root
    for part in path.relative_to(root).parts:
        component /= part
        if component.is_symlink():
            raise PackageError('package path must not use a symlink: ' + str(component))
    return path


def load_checker():
    # This is reviewed local package code, never a fixture-selected module.
    path = package_path(ROOT, Path(SKILL_NAME) / 'scripts/check_state.py')
    if not path.is_file():
        raise PackageError('state checker must be a regular local file')
    spec = importlib.util.spec_from_file_location('check_state', path)
    if spec is None or spec.loader is None:
        raise PackageError('cannot load the package state checker')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scalar(value: str) -> str:
    if value.startswith('"'):
        parsed = json.loads(value)
        if type(parsed) is not str:
            raise PackageError('expected a string scalar')
        return parsed
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def validate_package(root: Path = ROOT) -> tuple[list[str], dict[str, object]]:
    root = root.resolve()
    problems: list[str] = []
    stats: dict[str, object] = {}

    def check(ok: bool, message: str) -> None:
        if not ok:
            problems.append(message)

    checker = load_checker()

    def read(path: Path) -> bytes:
        return checker.read_regular_file(package_path(root, path))

    def read_text(path: Path) -> str:
        return read(path).decode('utf-8')

    def read_json(path: Path):
        return json.loads(read_text(path), object_pairs_hook=checker.reject_duplicates,
                          parse_constant=checker.reject_constant, parse_float=checker.finite_float)

    skill = root / SKILL_NAME
    body = read_text(skill / 'SKILL.md')
    parts = body.split('---\n', 2)
    check(len(parts) == 3 and parts[0] == '', 'YAML frontmatter boundaries')
    if len(parts) == 3:
        fm = parts[1]
        for field, limit in [('name', 64), ('description', 1024)]:
            matches = re.findall(rf'^{field}: (.+)$', fm, flags=re.M)
            check(len(matches) == 1, 'expected one single-line field: ' + field)
            if len(matches) == 1:
                value = scalar(matches[0])
                check(0 < len(value) <= limit, 'frontmatter size: ' + field)
                if field == 'name':
                    check(value == skill.name, 'skill name must match directory')
        metadata = re.search(r'^metadata:\n((?:[ \t].*\n?)*)', fm, flags=re.M)
        versions = re.findall(r'^  version: (.+)$', metadata[1], flags=re.M) if metadata else []
        check(len(versions) == 1, 'expected one metadata.version scalar')
        if len(versions) == 1:
            version = scalar(versions[0])
            check(bool(re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.+-]+)?', version)),
                  'metadata.version must be a semantic version string')
            stats['version'] = version
        requirements = re.findall(r'^  requirements: (.+)$', metadata[1], flags=re.M) if metadata else []
        check(len(requirements) == 1, 'expected one metadata.requirements scalar')
        if len(requirements) == 1:
            value = scalar(requirements[0])
            check(0 < len(value) <= 500, 'metadata.requirements must contain at most 500 characters')
        check(not re.search(r'^compatibility:', fm, flags=re.M),
              'host compatibility requirements belong in metadata.requirements')
    check(len(body.splitlines()) < 500, 'SKILL.md should stay under 500 lines')

    for directory, names, files in os.walk(root, followlinks=False):
        for name in list(names):
            path = Path(directory) / name
            if name in {'.git', '__pycache__'}:
                names.remove(name)
            elif path.is_symlink():
                check(False, 'package directory must not be a symlink: ' + str(path))
                names.remove(name)
        for name in sorted(files):
            path = Path(directory) / name
            if path.suffix != '.md':
                continue
            content = read_text(path)
            for ref in re.findall(r'\[[^\]]*\]\(([^)]+)\)', content):
                parsed = urlsplit(ref.strip('<>'))
                if parsed.scheme or not parsed.path:
                    continue
                target = package_path(root, path.parent / unquote(parsed.path))
                check(target.is_file(), f'broken local link: {path}: {ref}')

    evaluation = read_json(skill / 'evals/evals.json')
    if type(evaluation) is not dict or set(evaluation) != {'skill_name', 'evals'}:
        raise PackageError('behavior fixtures require skill_name and evals fields')
    check(evaluation['skill_name'] == skill.name, 'eval skill_name')
    cases = evaluation['evals']
    if type(cases) is not list or not cases:
        raise PackageError('behavior fixtures must be a nonempty list')
    stats['behavior_fixtures'] = len(cases)
    ids = []
    for item in cases:
        if type(item) is not dict or set(item) != {'id', 'prompt', 'expected_output', 'files', 'expectations'}:
            raise PackageError('behavior fixture fields')
        if type(item['id']) is not int:
            raise PackageError('eval id must be an integer')
        ids.append(item['id'])
        for key in ('prompt', 'expected_output'):
            check(type(item[key]) is str and bool(item[key].strip()), 'empty/non-string eval ' + key)
        assertions = item['expectations']
        check(type(assertions) is list and len(assertions) >= 2,
              'eval expectations must contain at least two assertions')
        if type(assertions) is list:
            check(all(type(x) is str and bool(x.strip()) for x in assertions), 'empty eval assertion')
        if type(item['files']) is not list:
            raise PackageError('eval files must be a list')
        for filename in item['files']:
            if type(filename) is not str or not filename.strip() or Path(filename).is_absolute():
                raise PackageError('eval input file must be a nonempty relative path')
            path = package_path(root, skill / filename)
            check(path.is_relative_to(skill) and path.is_file(), 'eval input file not found in skill')
    check(len(ids) == len(set(ids)), 'duplicate eval ids')

    triggers = read_json(skill / 'evals/trigger-evals.json')
    if type(triggers) is not list or not triggers:
        raise PackageError('trigger fixtures must be a nonempty list')
    queries: list[str] = []
    for item in triggers:
        if type(item) is not dict or set(item) != {'query', 'should_trigger'}:
            raise PackageError('trigger fixture fields')
        if type(item['query']) is not str or not item['query'].strip():
            raise PackageError('trigger query must be a nonempty string')
        if type(item['should_trigger']) is not bool:
            raise PackageError('trigger label must be boolean')
        queries.append(item['query'])
    check(len(queries) == len(set(queries)), 'duplicate trigger queries')
    stats['trigger_fixtures'] = len(triggers)
    stats['positive_triggers'] = sum(item['should_trigger'] for item in triggers)

    example = read_json(skill / 'assets/task-state.example.json')
    checker.validate_state(example)
    payload = read(skill / 'assets/payload.example.txt')
    check(hashlib.sha256(payload).hexdigest() == example['message']['payload_sha256'],
          'example hash does not match exact UTF-8 payload bytes')
    check((root / 'LICENSE').is_file() and (skill / 'LICENSE').is_file(),
          'root and bundled skill license files are required')
    return problems, stats


def main() -> int:
    try:
        problems, stats = validate_package()
    except (PackageError, ValueError, OSError, UnicodeError, RecursionError) as exc:
        problems, stats = [str(exc)], {}
    if problems:
        for problem in problems:
            print('FAIL: ' + json.dumps(problem[:2000], ensure_ascii=True), file=sys.stderr)
        return 1
    print('PASS: targeted package checks; ' + json.dumps(stats, sort_keys=True))
    print('NOT RUN: model/trigger behavior, UI/evidence truth, macOS/Claude Desktop end-to-end tests.')
    print('This static validator grants no authorization and is not a runtime send gate.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
