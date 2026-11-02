"""Summarize immutable round-9 raw measurements, failing on incomplete receipts."""
import argparse
import json
import math
import re
import statistics as st
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def stats(values):
    assert values
    assert all(math.isfinite(v) for v in values), values
    return dict(median=st.median(values), minimum=min(values), maximum=max(values), n=len(values))


def cell(values, scale=1):
    s = stats([v * scale for v in values])
    return f"{s['median']:.3f} [{s['minimum']:.3f}, {s['maximum']:.3f}]"


def delta(a, b):
    return 100 * (st.median(b) / st.median(a) - 1) if st.median(a) else None


def validate_integration(receipt, binary):
    validation = read(ROOT / "integration-final" / "receipt.json")
    assert validation["status"] == "passed" and validation["head"] == receipt["head"]
    for config in validation["configurations"]:
        assert config["build_exit"] == config["test_exit"] == 0
        suite = ET.parse(ROOT / "integration-final" / f"ctest-{config['kind']}.xml").getroot()
        assert suite.attrib["tests"] == "9" and suite.attrib["failures"] == "0"
        if config["kind"] == "cuda":
            matching = [b for b in config["binaries"] if b["name"] == binary]
            assert len(matching) == 1 and matching[0]["sha256"] == receipt["executable_sha256"]


def gaussian(tag):
    folder = ROOT / tag
    receipt = read(folder / "receipt.json")
    assert receipt["status"] == "passed", (tag, receipt)
    validate_integration(receipt, "gaussian_render_bench")
    rounds = receipt["rounds"]
    assert len(receipt["runs"]) == 2 * rounds
    assert all(r["exit"] == 0 for r in receipt["runs"])
    measures = {}
    for arm in (0, 1):
        for rnd in range(1, rounds + 1):
            data = read(folder / f"train_a{arm}_r{rnd}.json")
            for row in data["records"]:
                assert len(row["train_ms"]) == receipt["iterations"]
                assert all(math.isfinite(v) and v > 0 for v in row["train_ms"])
                for key, value in row.items():
                    if isinstance(value, (int, float)) and (
                        key.endswith("median_ms") or key.startswith("cuda_peak")
                        or key == "process_peak_working_set"
                    ):
                        measures.setdefault((row["size"], key), {0: [], 1: []})[arm].append(value)
                measures.setdefault((row["size"], "training_steps_per_second_derived"), {0: [], 1: []})[arm].append(1000 / row["train_median_ms"])
    lines = [f"# {tag}: same-binary paired comparison", "",
             f"Source `{receipt['head']}`; executable SHA256 `{receipt['executable_sha256']}`.", "",
             f"{rounds} balanced rounds; median [minimum, maximum] of per-process medians. "
             "Training throughput is derived from synchronized step latency. Byte metrics are converted to MiB. "
             "Peak allocated/reserved measurements are allocator statistics, not whole-device usage. "
             "Process working set covers the entire process. Host contention remains a limitation.", "",
             "| Pixels | Metric | Toggle off | Toggle on | Change | On lower |",
             "|---|---|---|---|---|---|"]
    records = []
    for (size, metric), arms in sorted(measures.items()):
        a, b = arms[0], arms[1]
        assert len(a) == len(b) == rounds, (tag, size, metric)
        scale = 1 / 1048576 if "peak" in metric else 1
        change = delta(a, b)
        change_s = f"{change:+.2f}%" if change is not None else "n/a"
        wins = sum(y < x for x, y in zip(a, b))
        lines.append(f"| {size} | {metric} | {cell(a, scale)} | {cell(b, scale)} | {change_s} | {wins}/{rounds} |")
        records.append(dict(size=size, metric=metric, off=stats(a), on=stats(b), change_percent=change,
                            on_lower_rounds=wins))
    control_note = "Unchanged render-only paths in this optimizer/loss toggle are noise controls. " if receipt["feature"] in ("fused-adam", "fused-ssim") else ""
    lines += ["", "Lower is better for latency and memory; higher is better for derived throughput. " + control_note +
              "Only `cuda_peak_*_train` fields cover the training phase; older forward/backward fields do not. "
              "Sizes run in order within each process, so 1024-pixel allocator reservations may retain prior "
              "512-pixel training state. Process peak working set is cumulative, not an isolated per-size allocation.", ""]
    (folder / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    return dict(tag=tag, source=receipt["head"], records=records)


def ml():
    folder = ROOT / "ml-budgets"
    receipt = read(folder / "receipt.json")
    assert receipt["status"] == "passed"
    validate_integration(receipt, "ml_representations")
    rounds = receipt["rounds"]
    assert rounds == 6 and receipt["budgets_mb"] == [-1, 32, 0]
    assert receipt["deterministic_algorithms"] is False and receipt["fused_apply_requested"] is True
    assert len(receipt["runs"]) == 3 * rounds
    assert all(r["exit"] == 0 for r in receipt["runs"])
    arms = {a: [read(folder / f"adaptive_b{a}_r{r}.json") for r in range(1, rounds + 1)] for a in range(3)}
    for rows in arms.values():
        for row in rows:
            row["train_samples_per_s_derived"] = row["train_samples"] * row["epochs"] / row["train_time_s"]
    metrics = ["accuracy", "macro_precision", "macro_recall", "macro_f1", "train_time_s", "train_samples_per_s_derived",
               "inference_latency_ms_median_b1", "throughput_samples_per_s", "peak_cuda_alloc_mb_train",
               "peak_cuda_reserved_mb_train", "peak_rss_mb", "kmap_part_device_bytes",
               "kmap_part_device_peak_bytes", "kmap_part_device_hits", "kmap_part_device_misses",
               "kmap_part_device_groups", "active_elements_mean"]
    lines = ["# Adaptive training with device cache budgets", "",
             f"Source `{receipt['head']}`; executable SHA256 `{receipt['executable_sha256']}`.", "",
             "Six balanced order permutations, fixed seed1 and dataset seed2026; these are repeat measurements "
             "of one training seed, not independent accuracy trials. Three epochs, 300 training and 200 test samples, "
             "2048 points/sample, batch16, 512MiB host part cache. Median [minimum, maximum]. "
             "Deterministic mode is off to exercise the default fused CUDA apply path, which deterministic mode bypasses. "
             "Seeds are fixed, but atomic summation may vary.", "",
             "| Metric | Unlimited | 32 MiB | 0 MiB | 32 MiB change | 0 MiB change |",
             "|---|---|---|---|---|---|"]
    output = {}
    for arm, rows in arms.items():
        for row in rows:
            assert row["kmap_part_device_mb"] == receipt["budgets_mb"][arm]
            assert row["epochs"] == 3 and len(row["curve"]) == 3
            assert row["seed"] == 1 and row["data_seed"] == 2026
            assert row["train_samples"] == 300 and row["test_samples"] == 200
            if arm:
                assert row["kmap_part_device_bytes"] <= (32 if arm == 1 else 0) * 1048576
                assert row["kmap_part_device_peak_bytes"] <= (32 if arm == 1 else 0) * 1048576
    for metric in metrics:
        vals = {a: [row[metric] for row in rows] for a, rows in arms.items()}
        quality = metric in ("accuracy", "macro_precision", "macro_recall", "macro_f1")
        scale = 100 if quality else (1 / 1048576 if metric.endswith("bytes") else 1)
        changes = [delta(vals[0], vals[a]) for a in (1, 2)]
        changes_s = ([f"{100*(st.median(vals[a])-st.median(vals[0])):+.2f} pp" for a in (1,2)] if quality else
                     [f"{v:+.2f}%" if v is not None else "n/a" for v in changes])
        lines.append("| " + " | ".join([metric + (" (%)" if quality else (" (MiB)" if metric.endswith("bytes") else "")),
                     *[cell(vals[a], scale) for a in range(3)], *changes_s]) + " |")
        output[metric] = {str(a): stats(vals[a]) for a in range(3)}
    lines += ["", "Cache statistics are sampled at experiment end, including evaluation and single-item inference. "
              "They are conservative retained-upload accounting, not total model/device memory. Training allocator peaks "
              "and whole-process working set are measured separately. Legacy *_train allocator peaks cover the epoch loop "
              "including per-epoch evaluation; train_time_s excludes evaluation. "
              "No inference about multi-seed generalization is justified.", "",
              "| Epoch | Budget | Loss | Training accuracy (%) | Test accuracy (%) | Epoch seconds |", "|---|---|---|---|---|---|"]
    for epoch in range(3):
        for arm in range(3):
            curves = [row["curve"][epoch] for row in arms[arm]]
            # Preserve all keys in structured output; field names are inspected from the actual harness JSON.
            output[f"curve_epoch_{epoch+1}_arm_{arm}"] = {key: stats([c[key] for c in curves])
                                                        for key in curves[0] if isinstance(curves[0][key], (float, int))}
            labels = ["train_loss", "train_acc", "test_acc", "epoch_train_s"]
            lines.append("| " + " | ".join([str(epoch + 1), str(receipt["budgets_mb"][arm]),
                         *[cell([c[k] for c in curves], 100 if k.endswith("_acc") else 1) if k in curves[0] else "See raw curve" for k in labels]]) + " |")
    (folder / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (folder / "summary.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tags", nargs="*", default=["adam-stack", "gather-stack", "all-fusions"])
    parser.add_argument("--ml", action="store_true")
    args = parser.parse_args()
    result = {tag: gaussian(tag) for tag in args.tags}
    if args.ml:
        result["ml-budgets"] = ml()
    target = ROOT / ("metrics-final.json" if args.ml else "metrics-gaussian.json")
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"written": str(target), "sections": list(result)}))
