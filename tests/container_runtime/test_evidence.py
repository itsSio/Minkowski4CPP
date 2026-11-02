"""Corruption, stale-library and false-success guards for runtime evidence."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load('run')
extractor = load('extract_evidence')


class EvidenceGuards(unittest.TestCase):
    def test_split_sanitizer_uses_project_cpp_standard(self):
        # The production key uses C++20 defaulted equality. A C++17 standalone
        # sanitizer invocation can fail after the entire real suite has passed.
        source = Path(__file__).resolve().parents[2]
        project = (source / 'CMakeLists.txt').read_text()
        self.assertIn('set(CMAKE_CXX_STANDARD 20)', project)
        command = runner.split_sanitizer_command(source, self.root / 'sanitized')
        self.assertIn('-std=c++20', command)
        self.assertIn('-fsanitize=address,undefined', command)
        self.assertIn(str(source / 'tests/adaptive/test_part_split.cpp'), command)
        self.assertNotIn('-std=c++17', command)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mink-runtime-evidence-')
        self.root = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def test_modified_source_rejected(self):
        engine = self.root / 'MinkowskiEngine'
        engine.mkdir()
        (engine / 'part.cpp').write_text('original')
        (self.root / 'CMakeLists.txt').write_text('original')
        manifest = dict(files=[dict(path=p.relative_to(self.root).as_posix(), sha256=runner.sha(p))
                               for p in [engine / 'part.cpp', self.root / 'CMakeLists.txt']])
        self.assertEqual(runner.verify_source(self.root, manifest), 2)
        (engine / 'part.cpp').write_text('modified')
        with self.assertRaisesRegex(RuntimeError, 'checksum differs'):
            runner.verify_source(self.root, manifest)

    def test_unmanifested_source_rejected(self):
        engine = self.root / 'MinkowskiEngine'
        engine.mkdir()
        (engine / 'part.cpp').write_text('original')
        (self.root / 'CMakeLists.txt').write_text('original')
        manifest = dict(files=[dict(path=p.relative_to(self.root).as_posix(), sha256=runner.sha(p))
                               for p in [engine / 'part.cpp', self.root / 'CMakeLists.txt']])
        (engine / 'extra.cpp').write_text('unaccounted')
        with self.assertRaisesRegex(RuntimeError, 'Unmanifested'):
            runner.verify_source(self.root, manifest)

    def test_skipped_suite_rejected(self):
        path = self.root / 'ctest.xml'
        path.write_text('<testsuite tests="1" failures="0" skipped="1"><testcase name="adaptive_tests"><skipped/></testcase></testsuite>')
        with self.assertRaisesRegex(RuntimeError, 'skipped'):
            runner.verify_junit(path, 1)

    def test_failed_suite_rejected(self):
        path = self.root / 'ctest.xml'
        path.write_text('<testsuite tests="1" failures="1"><testcase name="adaptive_tests"><failure/></testcase></testsuite>')
        with self.assertRaisesRegex(RuntimeError, 'failures'):
            runner.verify_junit(path, 1)

    def test_missing_suite_rejected(self):
        path = self.root / 'ctest.xml'
        path.write_text('<testsuite tests="1" failures="0"><testcase name="adaptive_tests"/></testsuite>')
        with self.assertRaisesRegex(RuntimeError, 'complete suite'):
            runner.verify_junit(path, 1)

    def test_source_profile_requires_new_suites_and_targets(self):
        targets, suites, standalone = runner.configuration(self.root)
        self.assertEqual(suites, runner.EXPECTED_SUITES)
        self.assertEqual(targets, runner.TARGETS)
        for relative in ['tests/adaptive/test_part_split.cpp', 'tests/tools/point_dataset_tests.cpp',
                         'benchmarks/test_ml_representations_summary.py',
                         'tests/tools/benchmark_memory_tests.cpp']:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        targets, suites, standalone = runner.configuration(self.root)
        self.assertEqual(suites - runner.EXPECTED_SUITES,
                         {'adaptive_split_tests', 'point_dataset_tests', 'modelnet_preprocessing_tests',
                          'ml_summary_tests', 'benchmark_memory_tests'})
        self.assertTrue({'adaptive_split_tests', 'point_dataset_tests', 'benchmark_memory_tests'} <= set(targets) & standalone)

    def test_new_suite_cannot_be_silently_omitted(self):
        path = self.root / 'ctest.xml'
        names = sorted(runner.EXPECTED_SUITES)
        path.write_text('<testsuite tests="9" failures="0">' +
                        ''.join('<testcase name="' + name + '"/>' for name in names) + '</testsuite>')
        with self.assertRaisesRegex(RuntimeError, 'complete suite'):
            runner.verify_junit(path, 9, runner.EXPECTED_SUITES | {'adaptive_split_tests'})

    def test_installed_archive_link_rejected(self):
        build = self.root / 'build'
        replies = build / '.cmake/api/v1/reply'
        replies.mkdir(parents=True)
        targets = [{'name': 'minkowski_cpp', 'jsonFile': 'library.json'}]
        library = dict(id='library', type='STATIC_LIBRARY', artifacts=[dict(path='libminkowski_cpp.a')],
                       sources=[dict(path='MinkowskiEngine/coordinate_manager.cu')])
        (replies / 'library.json').write_text(json.dumps(library))
        for name in runner.TARGETS:
            targets.append(dict(name=name, jsonFile=name + '.json'))
            target = dict(artifacts=[dict(path=name)], dependencies=[dict(id='library')],
                          link=dict(commandFragments=[dict(fragment='libminkowski_cpp.a')]))
            (replies / (name + '.json')).write_text(json.dumps(target))
        (replies / 'model.json').write_text(json.dumps(dict(paths=dict(source=str(self.root)), configurations=[dict(targets=targets)])))
        (replies / 'index-1.json').write_text(json.dumps(dict(reply={'codemodel-v2': dict(jsonFile='model.json')})))
        runner.check_codemodel(self.root, build)
        path = replies / 'adaptive_tests.json'
        target = json.loads(path.read_text())
        target['link']['commandFragments'] = [dict(fragment='/usr/local/lib/libminkowski_cpp.a')]
        path.write_text(json.dumps(target))
        with self.assertRaisesRegex(RuntimeError, 'Installed stale archive'):
            runner.check_codemodel(self.root, build)

        # Preserve the discovered Linux static-link failure as a configure-time guard.
        target['link']['commandFragments'] = [dict(fragment='libminkowski_cpp.a')]
        path.write_text(json.dumps(target))
        library['sources'].append(dict(path='MinkowskiEngine/coordinate_manager.cpp'))
        (replies / 'library.json').write_text(json.dumps(library))
        with self.assertRaisesRegex(RuntimeError, 'Legacy or missing CoordinateManager'):
            runner.check_codemodel(self.root, build)

    def test_bundle_roundtrip_preserves_failed_receipt(self):
        evidence = self.root / 'evidence'
        evidence.mkdir()
        (evidence / 'receipt.json').write_text(json.dumps(dict(status='failed', error='test failure')))
        (evidence / 'ctest.log').write_text('failed\n')
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            runner.emit_evidence(evidence)
        log = '\n'.join('job-prefix #8 12.3 ' + line for line in capture.getvalue().splitlines())
        result = extractor.extract(log, self.root / 'decoded')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual((self.root / 'decoded/ctest.log').read_text(), 'failed\n')

    def test_truncated_bundle_rejected(self):
        with self.assertRaisesRegex(ValueError, 'No complete'):
            extractor.extract('MINK_RUNTIME_BUNDLE_BEGIN {}\nMINK_RUNTIME_BUNDLE eA==', self.root / 'out')


if __name__ == '__main__':
    unittest.main()
