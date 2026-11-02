"""Compare numerical output from the three cache budgets under deterministic fallback."""
import json
import math
from pathlib import Path
import re

OUT = Path(__file__).resolve().parent.parent / "ml-deterministic-check"
HEAD = "f3f74919a64bede57fab7d5f303e94ca188c931a"
HASH = "F66BB23A370DA9C7F4AF3BB5647C34337AE49A2BF7A093765B482280020DB35A"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def flatten(value, prefix=""):
    if isinstance(value, dict):
        return {k: v for key, val in value.items() for k, v in flatten(val, f"{prefix}/{key}").items()}
    if isinstance(value, list):
        return {k: v for i, val in enumerate(value) for k, v in flatten(val, f"{prefix}/{i}").items()}
    return {prefix: value}


receipt = read(OUT / "receipt.json")
assert receipt["status"] == "passed" and len(receipt["runs"]) == 3
assert receipt["head"] == HEAD and receipt["executable_sha256"] == HASH
assert receipt["deterministic_algorithms"] is True and receipt["deterministic_warn_only"] is True
assert all(r["exit"] == 0 for r in receipt["runs"])
rows = [read(OUT / f"adaptive_b{a}.json") for a in range(3)]
selected = []
warnings = {}
for a, row in enumerate(rows):
    assert row["kmap_part_device_mb"] == [-1, 32, 0][a]
    assert row["seed"] == 1 and row["data_seed"] == 2026
    assert row["method"] == "adaptive" and row["device"] == "cuda"
    assert row["train_samples"] == 300 and row["test_samples"] == 200
    assert row["epochs"] == 3 and row["batch_size"] == 16 and row["points_per_sample"] == 2048
    if a:
        assert 0 <= row["kmap_part_device_bytes"] <= row["kmap_part_device_peak_bytes"] <= [0, 32, 0][a] * 1048576
    keys = ["accuracy", "macro_precision", "macro_recall", "macro_f1", "confusion", "per_class",
            "active_elements_mean", "active_elements_min", "active_elements_max", "level_histogram_train"]
    values = {k: row[k] for k in keys}
    values["curve"] = [{k: epoch[k] for k in ("epoch", "train_loss", "train_acc", "test_acc")} for epoch in row["curve"]]
    selected.append(flatten(values))
    lines = (OUT / f"adaptive_b{a}.log").read_text(encoding="utf-8-sig", errors="replace").splitlines()
    warnings[str(a)] = [line for line in lines if re.search(r"warn|non.?determin|deterministic implementation", line, re.I)]
differences = {}
for a in (1, 2):
    assert selected[a].keys() == selected[0].keys()
    diff = []
    for key, before in selected[0].items():
        after = selected[a][key]
        if isinstance(before, (int, float)):
            assert math.isfinite(before) and math.isfinite(after)
        if before != after:
            diff.append(dict(field=key, unlimited=before, candidate=after,
                             absolute_difference=abs(after-before) if isinstance(before, (int, float)) else None))
    differences[str(a)] = diff
result = dict(status="compared", source=HEAD, executable_sha256=HASH,
              numerical_values_compared=len(selected[0]),
              exact_across_all_budgets=all(not d for d in differences.values()),
              differences=differences, warnings=warnings,
              accuracy=[r["accuracy"] for r in rows],
              last_epoch_loss=[r["curve"][-1]["train_loss"] for r in rows],
              timing_claims=False,
              limitations="One process per budget; deterministic algorithms requested in warn-only mode. Equality is evidence for this workload, not universal CUDA determinism.")
(OUT / "numerical-comparison.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
text = ["# Deterministic fallback cache-policy check", "",
        f"Source `{HEAD}`, executable SHA256 `{HASH}`; one process per budget, same seed and controls. "
        "This is a correctness follow-up and makes no timing claim.", "",
        f"Compared {len(selected[0])} numerical and categorical output fields, excluding timings/cache accounting. "
        f"All budgets exactly equal: **{result['exact_across_all_budgets']}**.", "",
        "| Budget | Accuracy | Final training loss | Detected warning lines |", "|---|---|---|---|"]
for a, row in enumerate(rows):
    text.append(f"| {[-1,32,0][a]} MiB | {row['accuracy']:.6g} | {row['curve'][-1]['train_loss']:.12g} | {len(warnings[str(a)])} |")
text += ["", result["limitations"], "", "All output differences and warning lines are retained in `numerical-comparison.json`.", ""]
(OUT / "summary.md").write_text("\n".join(text), encoding="utf-8")
print(json.dumps(result))
