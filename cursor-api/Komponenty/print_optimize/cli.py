"""CLI: optymalizacja pod druk + kalibracja vs Whitewall."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .calibrate import batch_calibrate_directory
from .compare import compare_images
from .optimize import optimize_to_file
from .paths import test_photos_dir, ww_pairs_dir
from .whitewall_collect import collect_from_image_id, collect_pairs_for_directory


def _cmd_optimize(args: argparse.Namespace) -> int:
    result = optimize_to_file(
        args.input,
        args.output,
        strength=args.strength,
        use_gemini=not args.no_gemini,
        save_params_path=args.params,
    )
    print(result.params_json())
    print(f"Zapisano: {result.output_path}")
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    metrics = compare_images(args.reference, args.candidate)
    print(metrics.summary())
    return 0


def _cmd_collect_pairs(args: argparse.Namespace) -> int:
    input_dir = args.input_dir or test_photos_dir(for_write=True)
    output_dir = args.output_dir or ww_pairs_dir(for_write=True)
    manifests = collect_pairs_for_directory(
        Path(input_dir),
        Path(output_dir),
        product=args.product,
        locale=args.locale,
        headless=not args.visible,
    )
    print(f"Zebrano {len(manifests)} par -> {Path(output_dir) / 'index.json'}")
    return 0


def _cmd_collect_id(args: argparse.Namespace) -> int:
    output_dir = args.output_dir or ww_pairs_dir(for_write=True)
    manifest = collect_from_image_id(
        args.image_id,
        Path(output_dir),
        label=args.label,
    )
    print(json_dump(manifest.to_dict()))
    return 0


def _cmd_calibrate(args: argparse.Namespace) -> int:
    pairs_dir = args.pairs_dir or ww_pairs_dir()
    batch_calibrate_directory(
        Path(pairs_dir),
        strength=args.strength,
        reference_strength=str(int(args.reference_strength)),
        use_gemini=not args.no_gemini,
    )
    return 0


def json_dump(obj) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False, indent=2)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="print_optimize",
        description="Optymalizacja zdjec pod druk (Gemini scene + korekcja + strength).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    opt = sub.add_parser("optimize", help="Analizuj i zapisz obraz ze strength 0-100")
    opt.add_argument("input", type=Path)
    opt.add_argument("-o", "--output", type=Path, required=True)
    opt.add_argument("--strength", type=float, default=70.0)
    opt.add_argument("--params", type=Path, help="Zapis JSON parametrow korekcji")
    opt.add_argument("--no-gemini", action="store_true", help="Tylko domyslne parametry")
    opt.set_defaults(func=_cmd_optimize)

    cmp = sub.add_parser("compare", help="Porownaj dwa obrazy (ΔE LAB, SSIM, PSNR)")
    cmp.add_argument("reference", type=Path, help="Np. ww70.jpg z Whitewall")
    cmp.add_argument("candidate", type=Path, help="Np. ours70.jpg")
    cmp.set_defaults(func=_cmd_compare)

    col = sub.add_parser(
        "collect-pairs",
        help="Upload folderu testowego do Whitewall (Playwright) i pobierz pary 0/70/100",
    )
    col.add_argument(
        "--input-dir",
        type=Path,
        help="Folder zdjęć; domyślnie bezpieczny workspace Local AppData",
    )
    col.add_argument(
        "--output-dir",
        type=Path,
        help="Folder par; domyślnie bezpieczny workspace Local AppData",
    )
    col.add_argument("--product", default="item-acrylglasversieglung")
    col.add_argument("--locale", default="eu")
    col.add_argument("--visible", action="store_true", help="Przegladarka widoczna (debug)")
    col.set_defaults(func=_cmd_collect_pairs)

    cid = sub.add_parser(
        "collect-id",
        help="Pobierz pary z imageserver gdy masz recznie `id=` z DevTools",
    )
    cid.add_argument("image_id", help="Np. 0:643531663637:5fb3b1b7c81a0:1df0f0")
    cid.add_argument(
        "--output-dir",
        type=Path,
        help="Folder par; domyślnie bezpieczny workspace Local AppData",
    )
    cid.add_argument("--label", default="manual")
    cid.set_defaults(func=_cmd_collect_id)

    cal = sub.add_parser(
        "calibrate",
        help="Dla kazdej pary w dataset: ours70 + metryki vs ww70",
    )
    cal.add_argument(
        "pairs_dir",
        type=Path,
        nargs="?",
        help="Folder par; domyślnie bezpieczny workspace Local AppData",
    )
    cal.add_argument("--strength", type=float, default=70.0)
    cal.add_argument("--reference-strength", type=float, default=70.0)
    cal.add_argument("--no-gemini", action="store_true")
    cal.set_defaults(func=_cmd_calibrate)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nPrzerwano.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Blad: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
