"""Copy explicit final research artifacts into the integration support branch."""
import json
import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TREE = Path(r"C:\Users\User\Work\mink-wt\integration")
DEST = TREE / "benchmarks" / "round9"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def copy(source, relative):
    target = DEST / relative
    assert target.resolve().is_relative_to(DEST.resolve())
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target.relative_to(TREE).as_posix()


if __name__ == "__main__":
    assert read(ROOT / "integration-final" / "receipt.json")["status"] == "passed"
    for tag in ("adam-stack", "gather-stack", "all-fusions", "ml-budgets"):
        assert read(ROOT / tag / "receipt.json")["status"] == "passed"
        assert (ROOT / tag / "summary.md").exists()
    report = (ROOT / "REPORT.md").read_text(encoding="utf-8")
    assert "REPORT-DRAFT" not in report and "Measurements remain pending" not in report
    paths = []
    DEST.mkdir(parents=True, exist_ok=True)
    attributes = DEST / ".gitattributes"
    attributes.write_bytes(b"# Keep archived evidence byte-for-byte across platforms.\n* -text\n")
    paths.append(attributes.relative_to(TREE).as_posix())
    for name in ("REPORT.md", "REPRODUCTION.md", "environment.json", "metrics-final.json", "pr-index.md",
                 "integration-ancestry.json", "summarize-final.py", "run-integration.ps1",
                 "run-gaussian-ab.ps1", "run-ml-budgets.ps1", "source-provenance.json",
                 "restart-audit-testing.md", "restart-audit-gaussian.md", "restart-audit-adaptive.md",
                 "pr-evidence-index.py", "package-evidence.py", "validate-package.py"):
        paths.append(copy(ROOT / name, name))
    # The lab report links to its historical sibling; the portable copy retains that evidence locally.
    packaged_report = DEST / "REPORT.md"
    portable_report = report.replace("../final/original-vs-optimized.md", "historical-original-vs-optimized.md")
    for tag in ("adam", "adaptive", "gaussian"):
        portable_report = portable_report.replace(f"{tag}/ci-final.json", f"docker-ci/{tag}.json")
    packaged_report.write_text(portable_report, encoding="utf-8")
    paths.append(copy(ROOT.parent / "final" / "original-vs-optimized.md", "historical-original-vs-optimized.md"))
    for source in sorted((ROOT / "ml-deterministic-check").iterdir()):
        if source.is_file():
            paths.append(copy(source, Path("ml-deterministic-check") / source.name))
    for name in ("compare-deterministic.py", "ml-deterministic.ps1", "ml-audit-summary.json", "ml-audit-summary.md"):
        paths.append(copy(ROOT / "adaptive" / name, Path("adaptive") / name))
    lab = ROOT.parent.parent
    for name in ("mink-env.ps1", "mink-build.ps1", "with-lock.ps1", "cpu-only-fix.cmake"):
        paths.append(copy(lab / "tools" / name, Path("native-helpers") / name))
    paths.append(copy(ROOT.parent / "bridge-ml" / "r3" / "hostload.ps1", "native-helpers/hostload.ps1"))
    for tag in ("adam-stack", "gather-stack", "all-fusions", "ml-budgets"):
        names = ["receipt.json", "summary.md", "hostload.log"]
        if (ROOT / tag / "interpretation.md").exists():
            names.append("interpretation.md")
        names += [p.name for p in (ROOT / tag).glob("train_a*_r*.json")]
        names += [p.name for p in (ROOT / tag).glob("adaptive_b*_r*.json")]
        if tag == "ml-budgets":
            names.append("summary.json")
        for name in sorted(names):
            paths.append(copy(ROOT / tag / name, Path(tag) / name))
    for name in ("receipt.json", "ctest-cpu.xml", "ctest-cuda.xml", "ctest-cpu.txt", "ctest-cuda.txt", "pipeline.log"):
        paths.append(copy(ROOT / "integration-final" / name, Path("integration-final") / name))
    for tag in ("adam", "adaptive", "gaussian"):
        receipt = ROOT / tag / "ci-final.json"
        assert receipt.exists(), f"CI receipt missing: {tag}"
        ci = read(receipt)["run"]
        assert ci["conclusion"] == "success"
        jobs = [j for j in ci["jobs"] if j["name"].startswith("build-and-publish (")]
        assert {j["name"] for j in jobs} == {f"build-and-publish ({v})" for v in (124, 132, 134)}
        assert all(j["conclusion"] == "success" for j in jobs)
        paths.append(copy(receipt, Path("docker-ci") / f"{tag}.json"))
    paths.append(copy(ROOT / "pr-snapshot" / "all.json", "pr-snapshot.json"))
    entries = []
    for path in sorted(paths):
        file = TREE / path
        entries.append(dict(path=file.relative_to(DEST).as_posix(), bytes=file.stat().st_size,
                            sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
    manifest = dict(schema_version=1, runtime_source=read(ROOT / "integration-final" / "receipt.json")["head"], files=entries)
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    paths.append((DEST / "manifest.json").relative_to(TREE).as_posix())
    (ROOT / "package-paths.json").write_text(json.dumps(paths, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(files=len(paths), destination=str(DEST))))
