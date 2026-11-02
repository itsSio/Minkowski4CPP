"""Validate the immutable round-9 evidence package without rerunning experiments.

Run: python validate-package.py --package <repo>/benchmarks/round9 --repo <repo>
The manifest lists every packaged file except itself, using relative path, bytes
and SHA256. Use --receipt outside the package to retain the validation result.
"""
import argparse
import collections
import datetime
import hashlib
import json
import math
import re
import statistics
import subprocess
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

RUNTIME_SOURCE = "f3f74919a64bede57fab7d5f303e94ca188c931a"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stats(values):
    require(bool(values) and all(math.isfinite(x) for x in values), "Invalid numeric samples")
    return dict(median=statistics.median(values), minimum=min(values), maximum=max(values), n=len(values))


def equal_stats(actual, expected, context):
    for key, value in expected.items():
        require(key in actual and math.isclose(actual[key], value, rel_tol=1e-12, abs_tol=1e-12),
                f"Summary mismatch: {context} {key}")


def manifest_check(package):
    manifest = read(package / "manifest.json")
    require(manifest["schema_version"] == 1, "Unsupported manifest schema")
    require(manifest["runtime_source"] == RUNTIME_SOURCE, "Manifest runtime source differs")
    indexed = set()
    for item in manifest["files"]:
        relative = item["path"]
        path = (package / relative).resolve()
        require(path.is_relative_to(package) and path != package / "manifest.json", f"Unsafe manifest path: {relative}")
        require(relative == path.relative_to(package).as_posix(), f"Noncanonical manifest path: {relative}")
        require(relative not in indexed, f"Duplicate manifest entry: {relative}")
        indexed.add(relative)
        require(path.is_file(), f"Missing manifest file: {relative}")
        require(path.stat().st_size == item["bytes"], f"File size differs: {relative}")
        require(sha(path) == item["sha256"].lower(), f"File hash differs: {relative}")
    actual = {p.relative_to(package).as_posix() for p in package.rglob("*") if p.is_file()}
    require(actual == indexed | {"manifest.json"}, f"Manifest inventory differs: {sorted(actual ^ (indexed | {'manifest.json'}))}")
    return len(indexed)


def report_links(package, repo):
    report = (package / "REPORT.md").read_text(encoding="utf-8-sig")
    require("measurements in progress" not in report.lower() and "ml analysis remains pending" not in report.lower(),
            "Report still claims pending measurements")
    report = re.sub(r"(?ms)^```.*?^```[^\n]*", "", report)
    checked = []
    for match in re.finditer(r"\[[^\]]*\]\((<[^>]+>|[^\s)]+)(?:\s+\"[^\"]*\")?\)", report):
        link = match.group(1).strip("<>")
        parsed = urllib.parse.urlsplit(link)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        path = (package / urllib.parse.unquote(parsed.path)).resolve()
        require(path.is_relative_to(repo), f"Report link escapes repository: {link}")
        require(path.exists(), f"Report has a broken relative link: {link}")
        checked.append(link)
    return checked


def integration_check(package):
    receipt = read(package / "integration-final/receipt.json")
    require(receipt["status"] == "passed" and receipt["head"] == RUNTIME_SOURCE, "Integration receipt failed or has wrong source")
    require({c["kind"] for c in receipt["configurations"]} == {"cpu", "cuda"}, "Missing build configuration")
    hashes = {}
    for config in receipt["configurations"]:
        require(config["build_exit"] == config["test_exit"] == 0, "Build/test exit not zero")
        kind = config["kind"]
        junit = ET.parse(package / "integration-final" / f"ctest-{kind}.xml").getroot()
        cases = junit.findall(".//testcase")
        require(int(junit.attrib["tests"]) == len(cases) == 9 and int(junit.attrib["failures"]) == 0,
                f"JUnit count differs: {kind}")
        require(not junit.findall(".//failure") and not junit.findall(".//error"), f"JUnit failure: {kind}")
        log = (package / "integration-final" / f"ctest-{kind}.txt").read_text(encoding="utf-8-sig")
        require("100% tests passed, 0 tests failed out of 9" in log, f"CTest text does not agree: {kind}")
        hashes[kind] = {b["name"]: b["sha256"].lower() for b in config["binaries"]}
        require(len(hashes[kind]) == 6 and all(re.fullmatch(r"[a-f0-9]{64}", h) for h in hashes[kind].values()),
                f"Invalid binary hashes: {kind}")
    return hashes


def benchmark_receipt(package, tag, binary, hashes, count):
    receipt = read(package / tag / "receipt.json")
    require(receipt["status"] == "passed" and receipt["head"] == RUNTIME_SOURCE, f"Bad receipt: {tag}")
    require(receipt["executable_sha256"].lower() == hashes["cuda"][binary], f"Benchmark executable differs: {tag}")
    require(len(receipt["runs"]) == count and all(r["exit"] == 0 for r in receipt["runs"]), f"Incomplete runs: {tag}")
    return receipt


def gaussian_check(package, tag, hashes, metrics):
    receipt = benchmark_receipt(package, tag, "gaussian_render_bench", hashes, 20)
    require(receipt["rounds"] == 10 and receipt["iterations"] == 10 and receipt["warmup"] == 3, f"Wrong sample budget: {tag}")
    require(re.fullmatch(r"[a-fA-F0-9]{64}", receipt["input_sha256"]) is not None, "Invalid input hash")
    for rnd in range(1, 11):
        pair = [run["arm"] for run in receipt["runs"] if run["round"] == rnd]
        require(pair == ([0, 1] if rnd % 2 else [1, 0]), f"Unbalanced Gaussian order: {tag}/{rnd}")
    measurements = collections.defaultdict(lambda: {0: [], 1: []})
    for arm in (0, 1):
        for rnd in range(1, 11):
            raw = read(package / tag / f"train_a{arm}_r{rnd}.json")
            require(raw["iterations"] == 10 and raw["warmup"] == 3, "Raw sample budget differs")
            require({r["size"] for r in raw["records"]} == {512, 1024} and len(raw["records"]) == 2,
                    "Incorrect image size set")
            for row in raw["records"]:
                for phase in ("train", "forward", "backward", "forward_backward"):
                    samples = row[phase + "_ms"]
                    require(len(samples) == 10 and all(math.isfinite(x) and x > 0 for x in samples), "Invalid timing samples")
                    # JSON samples and serialized medians have independent six-digit rounding.
                    require(math.isclose(statistics.median(samples), row[phase + "_median_ms"], rel_tol=1e-5), "Raw median differs beyond output precision")
                for key, value in row.items():
                    if isinstance(value, (int, float)) and (key.endswith("median_ms") or key.startswith("cuda_peak") or key == "process_peak_working_set"):
                        measurements[row["size"], key][arm].append(value)
                measurements[row["size"], "training_steps_per_second_derived"][arm].append(1000 / row["train_median_ms"])
    summarized = {(r["size"], r["metric"]): r for r in metrics[tag]["records"]}
    require(set(measurements) == set(summarized), f"Missing summary metrics: {tag}")
    for key, arms in measurements.items():
        report = summarized[key]
        a, b = arms[0], arms[1]
        equal_stats(report["off"], stats(a), f"{tag}/{key}/off")
        equal_stats(report["on"], stats(b), f"{tag}/{key}/on")
        expected = 100 * (statistics.median(b) / statistics.median(a) - 1) if statistics.median(a) else None
        require(report["change_percent"] == expected, f"Percent change differs: {tag}/{key}")
        require(report["on_lower_rounds"] == sum(y < x for x, y in zip(a, b)), f"Pair count differs: {tag}/{key}")
    return 20


def ml_check(package, hashes, metrics):
    receipt = benchmark_receipt(package, "ml-budgets", "ml_representations", hashes, 18)
    require(receipt["rounds"] == 6 and receipt["budgets_mb"] == [-1, 32, 0], "ML budget differs")
    require(receipt["deterministic_algorithms"] is False and receipt["fused_apply_requested"] is True, "ML mode differs")
    orders = [tuple(r["arm"] for r in receipt["runs"] if r["round"] == rnd) for rnd in range(1, 7)]
    require(len(set(orders)) == 6 and all(sorted(order) == [0, 1, 2] for order in orders), "ML order is not six permutations")
    output = read(package / "ml-budgets/summary.json")
    require(output == metrics["ml-budgets"], "Standalone ML summary differs from combined metrics")
    for arm, budget in enumerate([-1, 32, 0]):
        rows = [read(package / "ml-budgets" / f"adaptive_b{arm}_r{rnd}.json") for rnd in range(1, 7)]
        for row in rows:
            require(row["seed"] == 1 and row["data_seed"] == 2026 and row["epochs"] == len(row["curve"]) == 3, "ML configuration differs")
            require(row["train_samples"] == 300 and row["test_samples"] == 200 and row["kmap_part_device_mb"] == budget, "ML data/budget differs")
            if budget >= 0:
                require(0 <= row["kmap_part_device_bytes"] <= budget * 1048576, "ML retained budget exceeded")
                require(0 <= row["kmap_part_device_peak_bytes"] <= budget * 1048576, "ML peak retained budget exceeded")
            row["train_samples_per_s_derived"] = row["train_samples"] * row["epochs"] / row["train_time_s"]
        for metric, summaries in output.items():
            if metric.startswith("curve_epoch_"):
                match = re.fullmatch(r"curve_epoch_(\d+)_arm_(\d+)", metric)
                require(match is not None, f"Unknown curve summary: {metric}")
                if int(match[2]) == arm:
                    for field, summary in summaries.items():
                        equal_stats(summary, stats([r["curve"][int(match[1])-1][field] for r in rows]), metric + "/" + field)
            else:
                equal_stats(summaries[str(arm)], stats([r[metric] for r in rows]), metric + "/" + str(arm))
    deterministic = benchmark_receipt(package, "ml-deterministic-check", "ml_representations", hashes, 3)
    require(deterministic["deterministic_algorithms"] is True, "Deterministic check mode differs")
    raw = [read(package / "ml-deterministic-check" / f"adaptive_b{arm}.json") for arm in range(3)]
    for key in ("accuracy", "macro_precision", "macro_recall", "macro_f1", "confusion"):
        require(raw[0][key] == raw[1][key] == raw[2][key], f"Deterministic output differs: {key}")
    for epoch in range(3):
        for key in ("train_loss", "train_acc", "test_acc"):
            require(len({row["curve"][epoch][key] for row in raw}) == 1, f"Deterministic curve differs: {epoch}/{key}")
    return 18


def git_check(repo):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True, encoding="utf-8").strip()
    changed = git("diff", "--name-only", RUNTIME_SOURCE, "--").splitlines()
    native_suffixes = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".cu", ".cuh", ".cmake"}
    untracked = git("ls-files", "--others", "--exclude-standard").splitlines()
    # The archived helper .cmake file is evidence, not an active build input.
    candidates = [p for p in changed + untracked if not p.startswith(("docs/", "benchmarks/round9/"))]
    native = [p for p in candidates if Path(p).suffix.lower() in native_suffixes or Path(p).name in {"CMakeLists.txt", "Dockerfile"}]
    require(not native, f"Native source/build inputs changed after validated source: {native}")
    require(all(p.startswith(("docs/", "benchmarks/")) for p in changed), f"Changes outside documentation/evidence: {changed}")
    return dict(head=git("rev-parse", "HEAD"), runtime_source=RUNTIME_SOURCE, changed_documentation_files=len(changed))


def validate(package, repo):
    files = manifest_check(package)
    links = report_links(package, repo)
    hashes = integration_check(package)
    metrics = read(package / "metrics-final.json")
    runs = sum(gaussian_check(package, tag, hashes, metrics) for tag in ("adam-stack", "gather-stack", "all-fusions"))
    runs += ml_check(package, hashes, metrics)
    dataset = repo / "tests/data/test.ply"
    require(dataset.is_file(), "Missing reproduction dataset")
    for tag in ("adam-stack", "gather-stack", "all-fusions"):
        require(sha(dataset) == read(package / tag / "receipt.json")["input_sha256"].lower(),
                f"Current dataset differs from benchmark input: {tag}")
    provenance = read(package / "source-provenance.json")
    require(provenance["runtime_source"] == RUNTIME_SOURCE and provenance["native_source_unchanged"] is True,
            "Source provenance contradicts validated runtime")
    provenance_paths = subprocess.check_output(["git", "-C", str(repo), "diff", "--name-only", RUNTIME_SOURCE,
                                                provenance["evidence_merge_head"], "--"], text=True, encoding="utf-8").splitlines()
    require(provenance_paths == provenance["changed_paths_since_runtime"], "Provenance changed-path snapshot differs from Git")
    for tag in ("adam", "adaptive", "gaussian"):
        ci = read(package / "docker-ci" / f"{tag}.json")
        ci_source = ci.get("source", ci.get("expected_head"))
        require(ci_source == ci["run"]["headSha"] and ci["run"]["conclusion"] == "success", f"CI head/result differs: {tag}")
        jobs = {job["name"]: job["conclusion"] for job in ci["run"]["jobs"] if job["name"].startswith("build-and-publish (")}
        require(jobs == {f"build-and-publish ({v})": "success" for v in (124, 132, 134)}, f"Incomplete Docker matrix: {tag}")
    return dict(status="passed", checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), package=str(package),
                manifest_files=files, report_links=links, junit_suites=18, benchmark_processes=runs, deterministic_processes=3,
                git=git_check(repo), scope="Evidence integrity only; does not rerun runtime tests or benchmarks")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    package = args.package.resolve()
    repo = args.repo.resolve() if args.repo else package.parents[1]
    try:
        if args.receipt:
            require(not args.receipt.resolve().is_relative_to(package), "Validation receipt must be outside hashed package")
        result = validate(package, repo)
        code = 0
    except (ValueError, KeyError, FileNotFoundError, ET.ParseError, subprocess.CalledProcessError) as exc:
        result, code = dict(status="failed", error=str(exc)), 1
    if args.receipt:
        args.receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
