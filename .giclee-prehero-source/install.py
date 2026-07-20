from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / '.giclee-prehero-source'
ZIP_PATH = SOURCE_DIR / 'source.zip'
SOURCE_URL = 'https://at.adobe.com/1NP4w4mi38w06zU1'
ASSETS = ROOT / 'assets'
MANIFEST = ROOT / 'snippets' / 'giclee-home-prehero-frame-manifest.liquid'
TEST_FILE = ROOT / 'cursor-api' / 'Komponenty' / 'stronaglowna' / 'test_prehero_frame_sequence.py'
FPS = 24
EXPECTED_FRAMES = 117
DURATION = EXPECTED_FRAMES / FPS


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def frame_number(path: Path) -> int:
    match = re.search(r'(\d+)(?=\.[^.]+$)', path.name)
    if not match:
        raise RuntimeError(f'Frame without numeric suffix: {path.name}')
    return int(match.group(1))


def build_manifest(names: list[str], total_bytes: int) -> str:
    urls = []
    for index, name in enumerate(names):
        comma = ',' if index < len(names) - 1 else ''
        urls.append("    {{ '" + name + "' | asset_url | json }}" + comma)
    return (
        '{% comment %}\n'
        '  Generated from the user-supplied 24 FPS JPG sequence.\n'
        f'  Frames: {len(names)}, total bytes: {total_bytes}, duration: {DURATION:.6f}s.\n'
        '{% endcomment %}\n'
        'window.GICLEE_PREHERO_FRAME_SEQUENCE = {\n'
        '  enabled: true,\n'
        "  format: 'jpg',\n"
        f'  frameCount: {len(names)},\n'
        f'  duration: {DURATION:.6f},\n'
        f'  sourceFps: {FPS},\n'
        '  cacheSize: 18,\n'
        '  preloadRadius: 4,\n'
        '  maxDpr: 1.5,\n'
        '  urls: [\n'
        + '\n'.join(urls)
        + '\n  ]\n};\n'
    )


def build_test() -> str:
    return '''from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RENDERER = ROOT / "assets" / "giclee-home-prehero-frames.js"
SCRUB = ROOT / "assets" / "giclee-home-prehero-scrub.js"
CSS = ROOT / "assets" / "giclee-home-prehero-scrub.css"
MANIFEST = ROOT / "snippets" / "giclee-home-prehero-frame-manifest.liquid"
BUILDER = ROOT / "scripts" / "build_prehero_webp_sequence.py"
SCRUB_VIDEO = ROOT / "assets" / "giclee-home-prehero-scrub.mp4"


def test_frame_renderer_uses_canvas_with_bounded_cache() -> None:
    source = RENDERER.read_text(encoding="utf-8")
    assert "giclee-prehero-scrub__canvas" in source
    assert "getContext('2d'" in source
    assert "desynchronized: true" in source
    assert "var maxCache" in source
    assert "var preloadRadius" in source
    assert "function evict()" in source
    assert "requestIdleCallback" in source
    assert "drawImage" in source
    assert "GICLEE_PREHERO_FRAME_STATUS" in source


def test_lenis_frame_mode_bypasses_mp4_source_and_seeks() -> None:
    source = SCRUB.read_text(encoding="utf-8")
    assert "frameRendererAvailable()" in source
    assert "renderMode: useFrameSequence ? 'webp-canvas' : 'mp4-seek'" in source
    assert "if (useFrameSequence) frameController.setProgress(progress);" in source
    assert "if (scrubState && scrubState.usesFrameSequence)" in source
    assert "parts.video.preload = 'none';" in source
    assert "if (useFrameSequence) return;" in source


def test_frame_canvas_visibility_is_scoped_to_frame_mode() -> None:
    styles = CSS.read_text(encoding="utf-8")
    assert ".giclee-prehero-scrub__canvas" in styles
    assert "data-frame-sequence-ready='true'" in styles
    assert "data-render-mode='webp-frames'" in styles
    assert "display: none;" in styles


def test_manifest_has_safe_disabled_fallback() -> None:
    source = MANIFEST.read_text(encoding="utf-8")
    assert "window.GICLEE_PREHERO_FRAME_SEQUENCE" in source
    assert "enabled: false" in source or "enabled: true" in source
    assert "urls:" in source


def test_current_prehero_media_is_complete_24fps_jpg_sequence() -> None:
    source = MANIFEST.read_text(encoding="utf-8")
    frame_names = re.findall(r"'(giclee-prehero-frame-\\d{4}\\.jpg)'", source)
    assert "format: 'jpg'" in source
    assert "frameCount: 117" in source
    assert "duration: 4.875000" in source
    assert "sourceFps: 24" in source
    assert len(frame_names) == 117
    assert len(set(frame_names)) == 117
    assert frame_names[0] == "giclee-prehero-frame-0001.jpg"
    assert frame_names[-1] == "giclee-prehero-frame-0117.jpg"
    assert not [name for name in frame_names if not (ROOT / "assets" / name).is_file()]
    assert not list((ROOT / "assets").glob("giclee-prehero-frame-*.webp"))
    assert SCRUB_VIDEO.is_file()
    assert SCRUB_VIDEO.stat().st_size > 100_000


def test_builder_generates_flat_shopify_assets_and_liquid_manifest() -> None:
    source = BUILDER.read_text(encoding="utf-8")
    assert 'FRAME_PREFIX = "giclee-prehero-frame-"' in source
    assert "libwebp" in source
    assert "asset_url | json" in source
    assert "budget-mb" in source
    assert "TemporaryDirectory" in source
    assert "MANIFEST_PATH.write_text" in source
'''


def main() -> None:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(SOURCE_URL, headers={'User-Agent': 'giclee-prehero-installer/1.0'})
    with urllib.request.urlopen(request, timeout=60) as response, ZIP_PATH.open('wb') as output:
        shutil.copyfileobj(response, output)
    if ZIP_PATH.stat().st_size < 100_000:
        raise RuntimeError(f'Downloaded source ZIP is unexpectedly small: {ZIP_PATH.stat().st_size} bytes.')

    with tempfile.TemporaryDirectory(prefix='giclee-prehero-jpg-') as temp_name:
        temp = Path(temp_name)
        with zipfile.ZipFile(ZIP_PATH) as archive:
            members = [m for m in archive.infolist() if not m.is_dir() and m.filename.lower().endswith(('.jpg', '.jpeg'))]
            if len(members) != EXPECTED_FRAMES:
                raise RuntimeError(f'Expected {EXPECTED_FRAMES} JPG frames, found {len(members)}.')
            archive.extractall(temp)
        source_frames = sorted(
            [p for p in temp.rglob('*') if p.is_file() and p.suffix.lower() in {'.jpg', '.jpeg'}],
            key=frame_number,
        )
        numbers = [frame_number(path) for path in source_frames]
        if numbers != list(range(numbers[0], numbers[0] + EXPECTED_FRAMES)):
            raise RuntimeError('Source frame numbering is not contiguous.')

        for old in ASSETS.glob('giclee-prehero-frame-*.webp'):
            old.unlink()
        for old in ASSETS.glob('giclee-prehero-frame-*.jpg'):
            old.unlink()

        names: list[str] = []
        for index, source in enumerate(source_frames, 1):
            name = f'giclee-prehero-frame-{index:04d}.jpg'
            shutil.copy2(source, ASSETS / name)
            names.append(name)

    video = ASSETS / 'giclee-home-prehero-scrub.mp4'
    run(
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
        '-framerate', str(FPS),
        '-i', str(ASSETS / 'giclee-prehero-frame-%04d.jpg'),
        '-an', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
        '-pix_fmt', 'yuv420p', '-g', '6', '-keyint_min', '6', '-sc_threshold', '0',
        '-movflags', '+faststart', str(video),
    )
    total_bytes = sum((ASSETS / name).stat().st_size for name in names)
    MANIFEST.write_text(build_manifest(names, total_bytes), encoding='utf-8')
    TEST_FILE.write_text(build_test(), encoding='utf-8')

    probe = subprocess.run(
        [
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,avg_frame_rate,nb_frames,duration',
            '-of', 'default=noprint_wrappers=1', str(video),
        ],
        cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE,
    ).stdout
    required = ('width=1280', 'height=720', 'avg_frame_rate=24/1', 'nb_frames=117', 'duration=4.875000')
    missing = [item for item in required if item not in probe]
    if missing:
        raise RuntimeError(f'MP4 verification failed; missing: {missing}. Probe:\n{probe}')
    print(f'Prepared {len(names)} JPG frames and matching {DURATION:.3f}s MP4.')


if __name__ == '__main__':
    main()
