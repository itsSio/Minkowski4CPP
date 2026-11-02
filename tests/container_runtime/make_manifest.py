"""Freeze canonical Git source blobs before rebuilding them in the existing image."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--commit', default='HEAD')
    args = parser.parse_args()
    def git(*command):
        return subprocess.check_output(['git', '-C', str(args.source), *command])
    commit = git('rev-parse', args.commit).decode().strip()
    files = []
    for name in git('ls-tree', '-r', '--name-only', commit).decode().splitlines():
        if name.startswith('tests/container_runtime/'):
            continue
        if not (name.startswith(('MinkowskiEngine/', 'tests/', 'benchmarks/')) or
                name in {'CMakeLists.txt', 'detect_cuda_compute_capabilities.cu', 'detect_cuda_version.cc'}):
            continue
        blob = git('show', commit + ':' + name)
        files.append(dict(path=name, bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest()))
    output = args.source / 'tests/container_runtime/source-manifest.json'
    output.write_text(json.dumps(dict(source_base_commit=commit,
                      format='Canonical Git blob bytes; Linux checkout', files=files), indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(commit=commit, files=len(files), output=str(output))))


if __name__ == '__main__':
    main()
