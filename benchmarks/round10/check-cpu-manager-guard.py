import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent / 'cpu-manager-link'
root.mkdir(exist_ok=True)
configured = Path(r'C:\Users\User\Work\mink-build\cpu-manager-link-cpu\mink-cpu-library-sources.txt').read_text()
script = r'C:\Users\User\Work\mink-wt\cpu-manager-link\tests\cmake\check_cpu_coordinate_manager.cmake'
cmake = r'C:\Users\User\Work\mink-env\cmake-4.2.3\bin\cmake.exe'
rows = []
for name, sources, success in (
    ('configured-target', configured, True),
    ('legacy-duplicate', configured + ';MinkowskiEngine/coordinate_manager.cpp', False),
    ('unified-duplicate', configured + ';MinkowskiEngine/coordinate_manager.cu', False),
    ('missing-unified', ';'.join(s for s in configured.split(';') if not s.endswith('/coordinate_manager.cu')), False),
):
    path = root / (name + '.txt')
    path.write_text(sources)
    command = [cmake, '-DSOURCE_FILE=' + str(path), '-P', script]
    result = subprocess.run(command, capture_output=True, text=True)
    (root / (name + '.log')).write_text(result.stdout + result.stderr)
    assert (result.returncode == 0) == success, (name, result.stdout, result.stderr)
    rows.append(dict(name=name, command=command, exit=result.returncode, expected_success=success))
(root / 'guard-receipt.json').write_text(json.dumps(dict(status='passed', cases=rows), indent=2) + '\n')
print('4 source-selection guard cases passed')
