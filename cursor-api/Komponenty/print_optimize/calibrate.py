"""Batch: optymalizuj oryginaly z datasetu i porownaj z Whitewall ww70."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from .compare import compare_images
from .optimize import optimize_to_file

LogFn = Callable[[str], None] | None


def batch_calibrate_directory(
    pairs_dir: Path | str,
    *,
    strength: float = 70.0,
    reference_strength: str = "70",
    use_gemini: bool = True,
    on_log: LogFn = None,
) -> list[dict]:
    """Dla kazdego podfolderu z original.jpg + ww70.jpg generuje ours70.jpg i metryki."""
    root = Path(pairs_dir)
    rows: list[dict] = []

    def log(msg: str) -> None:
        if on_log:
            on_log(msg)
        else:
            print(msg)

    for manifest_path in sorted(root.glob("*/manifest.json")):
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        rel = data.get("strengths") or {}
        orig_rel = rel.get("0")
        ref_rel = rel.get(reference_strength)
        if not orig_rel or not ref_rel:
            continue

        orig_path = root / orig_rel
        ref_path = root / ref_rel
        pair_dir = manifest_path.parent
        ours_path = pair_dir / f"ours{int(strength)}.jpg"
        params_path = pair_dir / f"ours{int(strength)}.params.json"

        log(f"[calibrate] {pair_dir.name} -> ours{int(strength)}.jpg")
        result = optimize_to_file(
            orig_path,
            ours_path,
            strength=strength,
            use_gemini=use_gemini,
            save_params_path=params_path,
            on_status=on_log,
        )
        metrics = compare_images(ref_path, ours_path)
        row = {
            "pair": pair_dir.name,
            "reference": str(ref_path.relative_to(root)),
            "ours": str(ours_path.relative_to(root)),
            "params": result.params.to_dict(),
            "metrics": {
                "delta_e_mean": metrics.delta_e_mean,
                "delta_e_p95": metrics.delta_e_p95,
                "ssim": metrics.ssim,
                "psnr": metrics.psnr,
            },
        }
        rows.append(row)
        log(f"  {metrics.summary()}")

    report_path = root / "calibration_report.json"
    report_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    if rows:
        avg_de = sum(r["metrics"]["delta_e_mean"] for r in rows) / len(rows)
        avg_ssim = sum(r["metrics"]["ssim"] for r in rows) / len(rows)
        log(f"[calibrate] srednia dE={avg_de:.2f}  SSIM={avg_ssim:.4f}  ({len(rows)} par)")
        log(f"[calibrate] raport: {report_path}")
    return rows
