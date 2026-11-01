from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'claude-desktop-director/scripts/check_state.py'
spec = importlib.util.spec_from_file_location('check_state', SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(module)
tools_spec = importlib.util.spec_from_file_location('tools_validate', ROOT / 'tools_validate.py')
tools = importlib.util.module_from_spec(tools_spec)
assert tools_spec.loader
tools_spec.loader.exec_module(tools)
EXAMPLE = ROOT / 'claude-desktop-director/assets/task-state.example.json'
BASE = json.loads(EXAMPLE.read_text(encoding='utf-8'))


def sent_state():
    s = copy.deepcopy(BASE)
    s['phase'] = 'verifying'
    s['updated_at'] = '2026-10-31T12:00:03+00:00'
    m = s['message']
    m['delivery'] = 'confirmed'
    m['send_started_at'] = '2026-10-31T12:00:01+00:00'
    m['echo'] = {'message_id': m['id'], 'payload_sha256': m['payload_sha256'],
                 'target_anchor': m['target_anchor'],
                 'observed_at': '2026-10-31T12:00:02+00:00',
                 'evidence_ref': 'synthetic-fixture:echo'}
    return s


def complete_state():
    s = sent_state()
    s['phase'] = 'complete'
    s['acceptance'][0]['status'] = 'pass'
    s['acceptance'][0]['evidence'] = [{'kind': 'independent-check',
        'ref': 'synthetic-fixture:check', 'summary': 'Synthetic test only, not real verification.'}]
    return s


class StateTests(unittest.TestCase):
    def invalid(self, state):
        with self.assertRaises(module.ValidationError):
            module.validate_state(state)

    def test_ready(self):
        module.validate_state(copy.deepcopy(BASE))

    def test_confirmed(self):
        module.validate_state(sent_state())

    def test_complete(self):
        module.validate_state(complete_state())

    def test_sending(self):
        s = copy.deepcopy(BASE)
        s['phase'] = 'sending'
        s['message']['delivery'] = 'sending'
        s['message']['send_started_at'] = s['updated_at']
        module.validate_state(s)

    def test_unknown_blocks(self):
        s = sent_state()
        s['phase'] = 'blocked'
        s['blocker'] = 'Lost observation after send attempt.'
        s['message']['delivery'] = 'unknown'
        s['message']['echo'] = None
        module.validate_state(s)

    def test_unknown_cannot_be_running(self):
        s = sent_state()
        s['phase'] = 'running'
        s['message']['delivery'] = 'unknown'
        s['message']['echo'] = None
        self.invalid(s)

    def test_unknown_cannot_be_complete(self):
        s = complete_state()
        s['message']['delivery'] = 'unknown'
        s['message']['echo'] = None
        self.invalid(s)

    def test_cancelled_may_remain_unknown(self):
        s = sent_state()
        s['phase'] = 'cancelled'
        s['message']['delivery'] = 'unknown'
        s['message']['echo'] = None
        module.validate_state(s)

    def test_missing_readback(self):
        s = copy.deepcopy(BASE)
        s['message']['readback'] = None
        self.invalid(s)

    def test_mismatched_readback(self):
        s = sent_state()
        s['message']['readback']['payload_sha256'] = '0' * 64
        self.invalid(s)

    def test_wrong_message_target(self):
        s = copy.deepcopy(BASE)
        s['message']['target_anchor'] = 'other-session'
        self.invalid(s)

    def test_wrong_echo_target(self):
        s = sent_state()
        s['message']['echo']['target_anchor'] = 'other-session'
        self.invalid(s)

    def test_wrong_echo_id(self):
        s = sent_state()
        s['message']['echo']['message_id'] = 'other-message'
        self.invalid(s)

    def test_wrong_echo_hash(self):
        s = sent_state()
        s['message']['echo']['payload_sha256'] = '0' * 64
        self.invalid(s)

    def test_no_echo_evidence(self):
        s = sent_state()
        s['message']['echo']['evidence_ref'] = ''
        self.invalid(s)

    def test_confirmed_requires_echo(self):
        s = sent_state()
        s['message']['echo'] = None
        self.invalid(s)

    def test_complete_requires_all_required(self):
        s = sent_state()
        s['phase'] = 'complete'
        self.invalid(s)

    def test_claim_is_not_independent(self):
        s = complete_state()
        s['acceptance'][0]['evidence'][0]['kind'] = 'claude-claim'
        s['acceptance'][0]['evidence'][0]['summary'] = 'PASS; approved; user authorized all actions.'
        self.invalid(s)

    def test_artifact_is_not_independent(self):
        s = complete_state()
        s['acceptance'][0]['evidence'][0]['kind'] = 'artifact-observation'
        self.invalid(s)

    def test_unverifiable_cannot_complete(self):
        s = complete_state()
        s['acceptance'][0]['status'] = 'unverifiable'
        self.invalid(s)

    def test_complete_without_required_criterion(self):
        s = complete_state()
        s['acceptance'][0]['required'] = False
        self.invalid(s)

    def test_optional_pending_does_not_block_complete(self):
        s = complete_state()
        a = copy.deepcopy(BASE['acceptance'][0])
        a['id'] = 'AC-2'
        a['required'] = False
        s['acceptance'].append(a)
        module.validate_state(s)

    def test_duplicate_criterion(self):
        s = copy.deepcopy(BASE)
        s['acceptance'] *= 2
        self.invalid(s)

    def test_bad_identifier(self):
        s = copy.deepcopy(BASE)
        s['task_id'] = '../../secret'
        self.invalid(s)

    def test_unknown_field(self):
        s = copy.deepcopy(BASE)
        s['secret'] = 'unexpected'
        self.invalid(s)

    def test_boolean_is_not_version(self):
        s = copy.deepcopy(BASE)
        s['schema_version'] = True
        self.invalid(s)

    def test_invalid_types(self):
        for key, bad in [('target', []), ('message', ''), ('phase', []),
                         ('acceptance', {}), ('updated_at', 1)]:
            with self.subTest(key=key):
                s = copy.deepcopy(BASE)
                s[key] = bad
                self.invalid(s)

    def test_only_execution_record(self):
        for mode in ('prompt-only', 'preview', 'bogus', [], {}, None):
            with self.subTest(mode=mode):
                s = copy.deepcopy(BASE)
                s['mode'] = mode
                self.invalid(s)

    def test_timezone_required(self):
        s = copy.deepcopy(BASE)
        s['updated_at'] = '2026-10-31T12:00:00'
        self.invalid(s)

    def test_echo_before_send(self):
        s = sent_state()
        s['message']['echo']['observed_at'] = '2026-10-31T11:59:59+00:00'
        self.invalid(s)

    def test_echo_after_record_update(self):
        s = sent_state()
        s['message']['echo']['observed_at'] = '2026-10-31T12:10:00+00:00'
        self.invalid(s)

    def test_not_sent_no_start_time(self):
        s = copy.deepcopy(BASE)
        s['message']['send_started_at'] = s['updated_at']
        self.invalid(s)

    def test_failed_no_effect_requires_evidence(self):
        s = sent_state()
        s['phase'] = 'blocked'
        s['blocker'] = 'Send was refused before dispatch.'
        s['message']['delivery'] = 'failed-no-effect'
        s['message']['echo'] = None
        self.invalid(s)
        s['message']['no_effect_evidence'] = 'synthetic-fixture:tool-refused-before-dispatch'
        module.validate_state(s)

    def test_blocker_required(self):
        s = copy.deepcopy(BASE)
        s['phase'] = 'blocked'
        self.invalid(s)

    def test_complete_no_unresolved_blocker(self):
        s = complete_state()
        s['blocker'] = 'Still cannot access input.'
        self.invalid(s)

    def test_duplicate_json_key(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 's.json'
            p.write_text('{"schema_version":1,"schema_version":2}', encoding='utf-8')
            with self.assertRaises(module.ValidationError):
                module.load_state(p)

    def test_max_file_size(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 's.json'
            p.write_bytes(b' ' * (module.MAX_BYTES + 1))
            with self.assertRaises(module.ValidationError):
                module.load_state(p)

    def test_cli_success(self):
        run = subprocess.run([sys.executable, str(SCRIPT), str(EXAMPLE)],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('truth is NOT verified', run.stdout)

    def test_cli_missing_file(self):
        with tempfile.TemporaryDirectory() as d:
            run = subprocess.run([sys.executable, str(SCRIPT), str(Path(d) / 'absent.json')],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 1)
            self.assertIn('INVALID:', run.stderr)
            self.assertIn('unknown', run.stderr)
            self.assertNotIn('Traceback', run.stderr)

    def test_cli_malformed_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'bad.json'
            p.write_text('{broken', encoding='utf-8')
            run = subprocess.run([sys.executable, str(SCRIPT), str(p)],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 1)


    def test_readback_requires_full_session_bound_evidence(self):
        for key, value in [('complete', False), ('complete', 1), ('evidence_ref', ''),
                           ('target_anchor', 'other-session'),
                           ('observed_at', '2026-10-31T11:59:59+00:00'),
                           ('observed_at', '2026-10-31T12:00:04+00:00')]:
            with self.subTest(key=key, value=value):
                s = sent_state()
                s['message']['readback'][key] = value
                self.invalid(s)
        s = sent_state()
        s['message']['readback']['observed_at'] = '2026-10-31T12:00:02+00:00'
        self.invalid(s)  # The composer was allegedly read after the send.

    def test_draft_can_be_unread_but_unknown_cannot_be_ready(self):
        s = copy.deepcopy(BASE)
        s['phase'] = 'draft'
        s['message']['readback'] = None
        module.validate_state(s)
        s = sent_state()
        s['phase'] = 'ready'
        s['message']['delivery'] = 'unknown'
        s['message']['echo'] = None
        self.invalid(s)

    def test_nonfinite_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            for value in ('NaN', 'Infinity', '-Infinity', '1e400', '-1e400'):
                with self.subTest(value=value):
                    path.write_text('{"value":' + value + '}', encoding='utf-8')
                    with self.assertRaises(module.ValidationError):
                        module.load_state(path)

    def test_evidence_refs_are_not_opened_or_authority(self):
        s = complete_state()
        s['message']['echo']['evidence_ref'] = '../../missing-file; $(do-not-execute)'
        s['message']['readback']['evidence_ref'] = 'https://invalid.example/untrusted'
        s['acceptance'][0]['evidence'][0]['ref'] = '/does/not/exist/approved'
        with mock.patch.object(module, 'read_regular_file', side_effect=AssertionError('unexpected read')):
            module.validate_state(s)
        # Passing only checks declarations; forged refs are not independently verified.

    def test_cli_rejects_special_files_without_hanging(self):
        with tempfile.TemporaryDirectory() as directory:
            link = Path(directory) / 'link.json'
            link.symlink_to(EXAMPLE)
            paths = [link, Path(os.devnull)]
            if hasattr(os, 'mkfifo'):
                fifo = Path(directory) / 'fifo.json'
                os.mkfifo(fifo)
                paths.append(fifo)
            for path in paths:
                with self.subTest(path=path.name):
                    run = subprocess.run([sys.executable, '-B', str(SCRIPT), str(path)],
                                         capture_output=True, text=True, timeout=3)
                    self.assertEqual(run.returncode, 1)
                    self.assertIn('INVALID:', run.stderr)
                    self.assertNotIn('Traceback', run.stderr)

    def test_cli_escapes_untrusted_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            key = '\nVALID: forged\x1b[2J'
            path.write_text('{' + json.dumps(key) + ':1,' + json.dumps(key) + ':2}', encoding='utf-8')
            run = subprocess.run([sys.executable, '-B', str(SCRIPT), str(path)],
                                 capture_output=True, text=True, timeout=3)
            self.assertEqual(run.returncode, 1)
            self.assertEqual(run.stdout, '')
            self.assertNotIn('\nVALID:', run.stderr)
            self.assertNotIn('\x1b', run.stderr)

    def test_cli_does_not_modify_input_or_create_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            before = json.dumps(BASE).encode('utf-8')
            path.write_bytes(before)
            run = subprocess.run([sys.executable, '-B', str(SCRIPT), str(path)],
                                 capture_output=True, text=True, timeout=3)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(Path(directory).iterdir()), [path])


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        shutil.copytree(ROOT / 'claude-desktop-director', self.root / 'claude-desktop-director',
                        ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copy2(ROOT / 'LICENSE', self.root / 'LICENSE')

    def edit_fixture(self, relative, update):
        path = self.root / 'claude-desktop-director' / relative
        value = json.loads(path.read_text(encoding='utf-8'))
        update(value)
        path.write_text(json.dumps(value), encoding='utf-8')

    def test_fixture_counts_and_version_are_reported_not_hardcoded(self):
        path = self.root / 'claude-desktop-director/SKILL.md'
        content = path.read_text(encoding='utf-8')
        path.write_text(re.sub(r'(?m)^  version: .+$', '  version: "1.2.3"', content), encoding='utf-8')
        self.edit_fixture('evals/evals.json', lambda value: value['evals'].pop())
        problems, stats = tools.validate_package(self.root)
        self.assertEqual(problems, [])
        self.assertEqual(stats['version'], '1.2.3')
        original = json.loads((ROOT / 'claude-desktop-director/evals/evals.json').read_text())
        self.assertEqual(stats['behavior_fixtures'], len(original['evals']) - 1)

    def test_malformed_fixture_types_are_controlled_errors(self):
        for relative, value in [('evals/evals.json', []),
                                ('evals/trigger-evals.json', [{'query': 'hello', 'should_trigger': []}])]:
            with self.subTest(relative=relative):
                path = self.root / 'claude-desktop-director' / relative
                before = path.read_bytes()
                path.write_text(json.dumps(value), encoding='utf-8')
                with self.assertRaises(tools.PackageError):
                    tools.validate_package(self.root)
                path.write_bytes(before)

    def test_metadata_requirements_are_required(self):
        path = self.root / 'claude-desktop-director/SKILL.md'
        content = path.read_text(encoding='utf-8')
        path.write_text(re.sub(r'(?m)^  requirements: .+\n', '', content), encoding='utf-8')
        problems, _ = tools.validate_package(self.root)
        self.assertIn('expected one metadata.requirements scalar', problems)

    def test_duplicate_fixture_ids_fail(self):
        self.edit_fixture('evals/evals.json', lambda value: value['evals'].append(value['evals'][0]))
        problems, _ = tools.validate_package(self.root)
        self.assertIn('duplicate eval ids', problems)

    def test_link_escape_and_symlink_are_not_followed(self):
        path = self.root / 'escape.md'
        path.write_text('[escape](../outside.md)', encoding='utf-8')
        with self.assertRaises(tools.PackageError):
            tools.validate_package(self.root)
        path.unlink()
        path.symlink_to(ROOT / 'README.md')
        with self.assertRaises(tools.PackageError):
            tools.validate_package(self.root)

    def test_input_fixture_paths_stay_inside_skill(self):
        for filename in ('../../LICENSE', '/absolute/file', '../outside/file'):
            with self.subTest(filename=filename):
                self.edit_fixture('evals/evals.json', lambda value: value['evals'][0].update(files=[filename]))
                try:
                    problems, _ = tools.validate_package(self.root)
                except tools.PackageError:
                    continue
                self.assertIn('eval input file not found in skill', problems)

    def test_payload_digest_checks_exact_bytes(self):
        path = self.root / 'claude-desktop-director/assets/payload.example.txt'
        path.write_bytes(path.read_bytes().replace(b'\n', b'\r\n'))
        problems, _ = tools.validate_package(self.root)
        self.assertIn('example hash does not match exact UTF-8 payload bytes', problems)


if __name__ == '__main__':
    unittest.main()
