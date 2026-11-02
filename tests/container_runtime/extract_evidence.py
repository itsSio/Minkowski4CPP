"""Extract and verify a runtime evidence bundle embedded in a GitHub job log."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile


def extract(log, output):
    blocks = re.findall(r'MINK_RUNTIME_BUNDLE_BEGIN (\{[^\r\n]+\})(.*?)MINK_RUNTIME_BUNDLE_END', log, re.S)
    if not blocks:
        raise ValueError("No complete runtime evidence bundle in log")
    identities = set()
    for header, body in blocks:
        meta = json.loads(header)
        payload = ''.join(re.findall(r'MINK_RUNTIME_BUNDLE ([A-Za-z0-9+/=]+)', body))
        blob = base64.b64decode(payload, validate=True)
        digest = hashlib.sha256(blob).hexdigest()
        if len(blob) != meta['bytes'] or digest != meta['sha256']:
            raise ValueError("Corrupt or truncated runtime evidence bundle")
        identities.add(digest)
        if len(identities) != 1:
            raise ValueError("Multiple different bundles: extract each job separately")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    names = set()
    with tarfile.open(fileobj=io.BytesIO(blob), mode='r:gz') as archive:
        for member in archive.getmembers():
            destination = (output / member.name).resolve()
            if not member.isfile() or not destination.is_relative_to(output) or member.name in names:
                raise ValueError("Unsafe or duplicate evidence member: " + member.name)
            names.add(member.name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.extractfile(member).read())
    manifest = json.loads((output / 'evidence-manifest.json').read_text())
    if names != {item['path'] for item in manifest} | {'evidence-manifest.json'}:
        raise ValueError("Evidence manifest inventory differs")
    for item in manifest:
        path = output / item['path']
        if path.stat().st_size != item['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError("Evidence file checksum differs: " + item['path'])
    receipt = json.loads((output / 'receipt.json').read_text())
    return dict(bundle_sha256=digest, files=len(names), status=receipt['status'], receipt=receipt)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = extract(args.log.read_text(encoding='utf-8-sig'), args.output)
    (args.output / 'extraction-receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
