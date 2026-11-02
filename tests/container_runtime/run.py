"""Rebuild current source using an existing image and execute its CPU tests.

No dependency installation or imported installed Minkowski library is used.
Source checksums, the CMake codemodel and archive/binary hashes identify the run.
A compressed evidence bundle is emitted into CI logs because the inherited image
build workflow has no artifact-upload step. Failures emit evidence before exit.
"""
import argparse
import base64
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import platform
try:
    import resource
except ImportError:
    resource = None  # Allows the evidence-verifier self-tests on Windows.
import shutil
import subprocess
import sys
import tarfile
import time
import xml.etree.ElementTree as ET

TARGETS = ["adaptive_tests", "gaussian_tests", "core_tests", "memory_growth_tests",
           "adaptive_vs_uniform_bench", "ml_representations", "test_framework_contract"]
LIBRARY_TARGETS = TARGETS[:-1]
EXPECTED_SUITES = {"cmake_source_filter", "ab_compare_selftest", "adaptive_tests",
                   "adaptive_vs_uniform_bench_smoke", "gaussian_tests", "core_tests",
                   "ml_representations_smoke", "memory_growth_tests", "test_framework_contract"}


def configuration(source):
    """Require known optional suites from source presence, never from CTest output."""
    targets, suites = list(TARGETS), set(EXPECTED_SUITES)
    standalone = {"test_framework_contract"}
    if (source / "tests/adaptive/test_part_split.cpp").is_file():
        targets.append("adaptive_split_tests")
        standalone.add("adaptive_split_tests")
        suites.add("adaptive_split_tests")
    if (source / "tests/tools/point_dataset_tests.cpp").is_file():
        targets.append("point_dataset_tests")
        standalone.add("point_dataset_tests")
        suites.add("point_dataset_tests")
        suites.add("modelnet_preprocessing_tests")
    if (source / "benchmarks/test_ml_representations_summary.py").is_file():
        suites.add("ml_summary_tests")
    return targets, suites, standalone


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_source(source, manifest):
    paths = set()
    for item in manifest["files"]:
        relative = item["path"]
        path = (source / relative).resolve()
        require(path.is_relative_to(source) and path.is_file(), "Missing or escaping source path: " + relative)
        require(relative not in paths, "Duplicate source path: " + relative)
        paths.add(relative)
        require(sha(path) == item["sha256"], "Source checksum differs: " + relative)
    require("CMakeLists.txt" in paths and any(p.startswith("MinkowskiEngine/") for p in paths), "Incomplete source manifest")
    for path in (source / "MinkowskiEngine").rglob("*"):
        if path.is_file() and path.suffix in {".cpp", ".c", ".cc", ".cu", ".cuh", ".h", ".hpp"}:
            require(path.relative_to(source).as_posix() in paths, "Unmanifested engine source: " + str(path))
    return len(paths)


def check_codemodel(source, build, target_names=None, standalone=None):
    target_names = TARGETS if target_names is None else target_names
    standalone = {"test_framework_contract"} if standalone is None else standalone
    replies = build / ".cmake/api/v1/reply"
    indices = sorted(replies.glob("index-*.json"))
    require(bool(indices), "CMake codemodel index missing")
    index = read(indices[-1])
    model = read(replies / index["reply"]["codemodel-v2"]["jsonFile"])
    require(Path(model["paths"]["source"]).resolve() == source, "CMake source root differs")
    targets = {t["name"]: read(replies / t["jsonFile"]) for t in model["configurations"][0]["targets"]}
    library = targets["minkowski_cpp"]
    require(library["type"] == "STATIC_LIBRARY", "Expected a source-built static library")
    manager_sources = {Path(item["path"]).name for item in library.get("sources", [])
                       if Path(item["path"]).stem == "coordinate_manager"}
    require(manager_sources == {"coordinate_manager.cu"}, "Legacy or missing CoordinateManager source: " + str(manager_sources))
    archive = (build / library["artifacts"][0]["path"]).resolve()
    require(archive.is_relative_to(build), "Minkowski archive is outside this build")
    artifacts = {"minkowski_cpp": archive}
    linkage = {}
    for name in target_names:
        target = targets[name]
        artifacts[name] = (build / target["artifacts"][0]["path"]).resolve()
        require(artifacts[name].is_relative_to(build), "Executable is outside this build: " + name)
        if name in standalone:
            continue
        dependency_ids = {item["id"] for item in target.get("dependencies", [])}
        require(library["id"] in dependency_ids, "Target does not depend on rebuilt library: " + name)
        fragments = [f["fragment"] for f in target.get("link", {}).get("commandFragments", [])]
        require(any(archive.name in f for f in fragments), "Rebuilt archive missing from linker command: " + name)
        require(not any("/usr/local/lib/libminkowski_cpp" in f for f in fragments), "Installed stale archive linked: " + name)
        linkage[name] = dict(dependency=library["id"], fragments=fragments)
    return dict(source=str(source), build=str(build), archive=str(archive), targets=linkage), artifacts


def verify_junit(path, count, expected_suites=None):
    expected_suites = EXPECTED_SUITES if expected_suites is None else expected_suites
    root = ET.parse(path).getroot()
    cases = root.findall(".//testcase")
    require(int(root.attrib["tests"]) == len(cases) == count, "JUnit test count differs")
    require(int(root.attrib["failures"]) == 0 and not root.findall(".//failure") and not root.findall(".//error"), "JUnit contains failures")
    require(int(root.attrib.get("skipped", "0")) == 0 and not root.findall(".//skipped"), "A registered suite was skipped")
    require({case.attrib["name"] for case in cases} == expected_suites, "JUnit did not execute complete suite set")
    return dict(tests=len(cases), failures=0, suites=sorted(expected_suites))


def emit_evidence(output):
    files = sorted(p for p in output.rglob("*") if p.is_file())
    manifest = [{"path": str(p.relative_to(output)), "sha256": sha(p), "bytes": p.stat().st_size} for p in files]
    (output / "evidence-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for path in sorted(output.rglob("*")):
            if path.is_file():
                archive.add(path, arcname=path.relative_to(output).as_posix())
    blob = stream.getvalue()
    print("MINK_RUNTIME_BUNDLE_BEGIN " + json.dumps(dict(bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest())), flush=True)
    encoded = base64.b64encode(blob).decode("ascii")
    for start in range(0, len(encoded), 160):
        print("MINK_RUNTIME_BUNDLE " + encoded[start:start + 160], flush=True)
    print("MINK_RUNTIME_BUNDLE_END", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--expected-tests", type=int, help="Optional assertion; suites are required from source presence")
    parser.add_argument("--image-digest", required=True)
    args = parser.parse_args()
    source, build, output = (p.resolve() for p in (args.source, args.build, args.output))
    target_names, expected_suites, standalone = configuration(source)
    require(args.expected_tests is None or args.expected_tests == len(expected_suites), "Requested suite count differs from source profile")
    build.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    receipt = dict(status="running", started=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   image_digest=args.image_digest, source=str(source), build=str(build),
                   mode="CPU_ONLY; CUDA-enabled image dependencies, no GPU runtime claimed",
                   platform=platform.platform(), python=sys.version, stages=[],
                   image_cuda_profile=os.environ.get("CUDA_VERSION"), cpu_count=os.cpu_count(),
                   disk_free_before=shutil.disk_usage(build).free)

    def save():
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

    def run(stage, command):
        started = time.monotonic()
        print("MINK_RUNTIME_STAGE " + stage + " " + json.dumps(command), flush=True)
        with (output / (stage + ".log")).open("w") as log:
            result = subprocess.run(command, cwd=build, stdout=log, stderr=subprocess.STDOUT)
        item = dict(name=stage, command=command, exit_code=result.returncode, wall_seconds=time.monotonic() - started,
                    peak_child_rss_kib_so_far=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss if resource else None)
        receipt["stages"].append(item)
        save()
        print("MINK_RUNTIME_RESULT " + json.dumps(item), flush=True)
        if result.returncode:
            print((output / (stage + ".log")).read_text(errors="replace")[-24000:], flush=True)
        require(result.returncode == 0, f"{stage} failed with exit {result.returncode}")

    save()
    try:
        manifest_path = source / "tests/container_runtime/source-manifest.json"
        manifest = read(manifest_path)
        receipt["source_base_commit"] = manifest["source_base_commit"]
        receipt["verified_source_files"] = verify_source(source, manifest)
        shutil.copy2(manifest_path, output / "source-manifest.json")
        run("versions", ["bash", "-c", "cmake --version && c++ --version && nvcc --version && df -h / && cat /proc/meminfo && cat /opt/libtorch/build-version"])
        query = build / ".cmake/api/v1/query"
        query.mkdir(parents=True, exist_ok=True)
        (query / "codemodel-v2").touch()
        run("configure", ["cmake", "-S", str(source), "-B", str(build), "-GNinja", "-DCMAKE_BUILD_TYPE=Release",
                          "-DCMAKE_PREFIX_PATH=/opt/libtorch", "-DCMAKE_CUDA_ARCHITECTURES=75", "-DCPU_ONLY=ON",
                          "-DMINK_BUILD_TESTS=ON", "-DMINK_BUILD_ADAPTIVE_TESTS=ON", "-DMINK_BUILD_ML_EXPERIMENTS=ON",
                          "-DMINKOWSKI_ENABLE_GAUSSIAN=ON", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"])
        linkage, artifacts = check_codemodel(source, build, target_names, standalone)
        (output / "linkage.json").write_text(json.dumps(linkage, indent=2) + "\n")
        shutil.copy2(build / "compile_commands.json", output / "compile_commands.json")
        shutil.copy2(build / "CMakeCache.txt", output / "CMakeCache.txt")
        run("build", ["cmake", "--build", str(build), "--parallel", str(args.jobs), "--target", *target_names])
        receipt["artifacts"] = [{"target": name, "path": str(path), "sha256": sha(path), "bytes": path.stat().st_size}
                                for name, path in artifacts.items()]
        run("ctest-list", ["ctest", "--test-dir", str(build), "--show-only=json-v1"])
        discovered = read(output / "ctest-list.log")
        require(len(discovered["tests"]) == len(expected_suites), "Wrong number of registered CTest suites")
        require({t["name"] for t in discovered["tests"]} == expected_suites, "Registered CTest suite set differs")
        run("ctest", ["ctest", "--test-dir", str(build), "--parallel", "1", "--verbose", "--output-on-failure",
                      "--timeout", "420", "--output-junit", str(output / "ctest.xml")])
        receipt["junit"] = verify_junit(output / "ctest.xml", len(expected_suites), expected_suites)
        if "adaptive_split_tests" in standalone:
            sanitized = build / "adaptive_split_sanitized"
            run("split-sanitizer-build", ["c++", "-std=c++17", "-O1", "-g", "-fsanitize=address,undefined",
                 "-fno-omit-frame-pointer", "-I" + str(source), "-I" + str(source / "tests"),
                 str(source / "tests/adaptive/test_part_split.cpp"), "-o", str(sanitized)])
            receipt["split_sanitizer_sha256"] = sha(sanitized)
            run("split-sanitizer-test", [str(sanitized)])
        require(all(sha(Path(a["path"])) == a["sha256"] for a in receipt["artifacts"]), "Built artifacts changed during tests")
        verify_source(source, manifest)
        receipt["status"] = "passed"
    except Exception as exc:
        receipt["status"] = "failed"
        receipt["error"] = str(exc)
        print("MINK_RUNTIME_FAILURE " + str(exc), flush=True)
    finally:
        receipt["completed"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        receipt["disk_free_after"] = shutil.disk_usage(build).free
        save()
        emit_evidence(output)
        print("MINK_RUNTIME_FINAL " + json.dumps(receipt), flush=True)
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
