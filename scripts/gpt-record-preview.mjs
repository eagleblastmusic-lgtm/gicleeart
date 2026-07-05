#!/usr/bin/env node
/**
 * Nagranie podglądu (Playwright): webm + png + console-errors.txt
 *
 * Desktop: 1920×1080. Scroll przez natywne animacje section-scroll (jak PageDown).
 */
import { chromium } from "playwright";
import { mkdir, rename, readdir, unlink, writeFile } from "node:fs/promises";
import path from "node:path";

const DESKTOP_VIEWPORT = { width: 1920, height: 1080 };
const MOBILE_VIEWPORT = { width: 390, height: 844 };

/** Hero + fade_in collage (pierwszy klip ~3 s). */
const HERO_HOLD_MS = 4500;
/** Postój po dojechaniu do sekcji — stack lerp + podgląd slajdu. */
const SECTION_HOLD_MS = 4200;
const MAX_SECTION_STEPS = 16;

function parseArgs(argv) {
  const out = {
    url: "http://127.0.0.1:9292/?giclee_skip_splash=1&giclee_skip_notice=1",
    outDir: "docs/review-demos",
    scrollSeconds: 55,
    desktopOnly: false,
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--url") out.url = argv[++i];
    else if (a === "--out-dir") out.outDir = argv[++i];
    else if (a === "--scroll-seconds") out.scrollSeconds = parseFloat(argv[++i]);
    else if (a === "--desktop-only") out.desktopOnly = true;
    else if (a === "--wait-hero" || a === "--pre-scroll-hold") argv[++i];
  }
  return out;
}

async function pickNewestWebm(dir) {
  let files;
  try {
    files = await readdir(dir);
  } catch {
    return null;
  }
  const webms = files.filter((f) => f.endsWith(".webm"));
  if (!webms.length) return null;
  return path.join(dir, webms[webms.length - 1]);
}

function attachConsoleCollector(page, bucket) {
  page.on("console", (msg) => {
    const type = msg.type();
    if (type === "error" || type === "warning") {
      bucket.push(`[${type}] ${msg.text()}`);
    }
  });
  page.on("pageerror", (err) => {
    bucket.push(`[pageerror] ${err.message}`);
  });
}

async function waitForHeroReady(page, timeoutMs = 45000) {
  await page
    .waitForFunction(
      () => {
        const html = document.documentElement;
        if (document.readyState !== "complete") return false;

        const collageRoot = document.querySelector("[data-giclee-video-collage]");
        if (collageRoot) {
          const stage = collageRoot.querySelector(".giclee-collage__stage");
          if (stage && stage.dataset.gicleeCollageBooting === "1") return false;
          const video = collageRoot.querySelector("video");
          if (video && video.readyState < 2) return false;
        }

        if (
          html.classList.contains("giclee-home-stack") &&
          !html.classList.contains("giclee-home-stack-ready")
        ) {
          return false;
        }

        return true;
      },
      { timeout: timeoutMs },
    )
    .catch(() => {
      console.warn("[record] waitForHeroReady: timeout — kontynuuję nagranie");
    });
}

async function waitStackVisualSettled(page, timeoutMs = 8000) {
  await page
    .waitForFunction(
      () =>
        new Promise((resolve) => {
          let lastSig = "";
          let stable = 0;
          const t0 = performance.now();
          function frame() {
            const html = document.documentElement;
            if (html.classList.contains("giclee-home-stack-scrolling")) {
              stable = 0;
              requestAnimationFrame(frame);
              return;
            }
            const els = document.querySelectorAll("[data-giclee-home-stack]");
            const sig = Array.from(els)
              .map(
                (el) =>
                  `${el.style.getPropertyValue("--home-stack-slip-y")}|${el.style.getPropertyValue("--home-stack-overlap-eased")}|${el.style.getPropertyValue("--home-stack-under-dim")}`,
              )
              .join(";");
            if (sig === lastSig) stable += 1;
            else {
              stable = 0;
              lastSig = sig;
            }
            if (stable >= 15 || performance.now() - t0 > timeoutMs) resolve(true);
            else requestAnimationFrame(frame);
          }
          requestAnimationFrame(frame);
        }),
      { timeout: timeoutMs + 2000 },
    )
    .catch(() => {});
}

async function waitSectionScrollIdle(page) {
  await page.waitForFunction(
    () => {
      const api = window.GICLEE_HOME_SECTION_SCROLL;
      if (api && typeof api.isNavigationIdle === "function") {
        return api.isNavigationIdle();
      }
      return !document.documentElement.classList.contains("giclee-home-stack-scrolling");
    },
    { timeout: 20000 },
  );
  const extraMs = await page.evaluate(() => {
    const api = window.GICLEE_HOME_SECTION_SCROLL;
    return api && typeof api.maxAnimMs === "function" ? api.maxAnimMs() : 1400;
  });
  await page.waitForTimeout(Math.min(extraMs, 2500));
  await waitStackVisualSettled(page);
}

async function runNativeSectionScroll(page, { outDir, label }) {
  const meta = await page.evaluate(() => {
    const api = window.GICLEE_HOME_SECTION_SCROLL;
    if (!api || typeof api.sectionCount !== "function") {
      return { mode: "none", count: 0 };
    }
    return { mode: "native", count: api.sectionCount() };
  });

  if (meta.mode !== "native" || meta.count < 2) {
    console.warn(`[${label}] brak section-scroll — pomijam natywny scroll`);
    return false;
  }

  console.log(
    `[${label}] scroll: natywny section-scroll (${meta.count} sekcji, hold ${SECTION_HOLD_MS}ms)`,
  );

  await page.waitForTimeout(HERO_HOLD_MS);

  let midCaptured = false;
  const maxScroll = await page.evaluate(() =>
    Math.max(
      0,
      Math.max(document.body.scrollHeight, document.documentElement.scrollHeight) -
        window.innerHeight,
    ),
  );
  const midTarget = maxScroll * 0.5;

  for (let step = 0; step < MAX_SECTION_STEPS; step++) {
    const result = await page.evaluate(() => {
      const api = window.GICLEE_HOME_SECTION_SCROLL;
      if (!api || typeof api.stepDown !== "function") return "no-api";
      if (!api.isNavigationIdle()) return "busy";
      return api.stepDown() ? "moved" : "done";
    });

    if (result === "no-api") return false;
    if (result === "done") break;
    if (result === "busy") {
      await waitSectionScrollIdle(page);
      continue;
    }

    await waitSectionScrollIdle(page);

    const scrollY = await page.evaluate(() => window.scrollY);
    if (!midCaptured && scrollY >= midTarget) {
      const midPath = path.join(outDir, `latest-${label}-midscroll.png`);
      await page.screenshot({ path: midPath, fullPage: false });
      console.log(`[${label}] Zapisano ${midPath}`);
      midCaptured = true;
    }

    await page.waitForTimeout(SECTION_HOLD_MS);
  }

  if (!midCaptured) {
    const midPath = path.join(outDir, `latest-${label}-midscroll.png`);
    await page.screenshot({ path: midPath, fullPage: false });
    console.log(`[${label}] Zapisano ${midPath}`);
  }

  await page.evaluate(() => {
    const max = Math.max(
      document.body.scrollHeight,
      document.documentElement.scrollHeight,
    );
    window.scrollTo(0, max - window.innerHeight);
  });
  await waitStackVisualSettled(page);
  await page.waitForTimeout(SECTION_HOLD_MS);
  return true;
}

async function recordViewport({
  url,
  outDir,
  label,
  viewport,
  scrollSeconds,
  consoleLines,
}) {
  const tmpVideoDir = path.join(outDir, `_tmp_${label}`);
  await mkdir(tmpVideoDir, { recursive: true });

  const browser = await chromium.launch({
    headless: true,
    args: [
      "--headless=new",
      "--disable-background-timer-throttling",
      "--disable-renderer-backgrounding",
      "--disable-backgrounding-occluded-windows",
    ],
  });
  const context = await browser.newContext({
    viewport,
    deviceScaleFactor: 1,
    recordVideo: { dir: tmpVideoDir },
    userAgent:
      label === "mobile"
        ? "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        : undefined,
  });

  const page = await context.newPage();
  attachConsoleCollector(page, consoleLines);

  console.log(`[${label}] Otwieram ${url} (${viewport.width}×${viewport.height})`);
  await page.goto(url, { waitUntil: "load", timeout: 90000 });
  await waitForHeroReady(page);

  const pngPath = path.join(outDir, `latest-${label}.png`);
  await page.screenshot({ path: pngPath, fullPage: false });
  console.log(`[${label}] Zapisano ${pngPath}`);

  const usedNative = await runNativeSectionScroll(page, { outDir, label, scrollSeconds });
  if (!usedNative) {
    console.warn(`[${label}] fallback scroll wyłączony — nagranie tylko do hero`);
  }

  await page.waitForTimeout(2500);
  await context.close();
  await browser.close();

  const raw = await pickNewestWebm(tmpVideoDir);
  if (!raw) {
    throw new Error(`Brak pliku webm po nagraniu (${label})`);
  }
  const dest = path.join(outDir, `latest-${label}.webm`);
  await rename(raw, dest);
  try {
    const rest = await readdir(tmpVideoDir);
    for (const f of rest) await unlink(path.join(tmpVideoDir, f));
  } catch {
    /* ignore */
  }
  console.log(`[${label}] Zapisano ${dest}`);
  return dest;
}

async function writeConsoleLog(outDir, lines) {
  const file = path.join(outDir, "console-errors.txt");
  let body;
  if (!lines.length) {
    body = "Brak błędów i warningów w konsoli (Playwright).\n";
  } else {
    body = lines.join("\n") + "\n";
  }
  await writeFile(file, body, "utf8");
  console.log(`Zapisano ${file}`);
}

async function main() {
  const args = parseArgs(process.argv);
  const outDir = path.resolve(args.outDir);
  await mkdir(outDir, { recursive: true });
  const consoleLines = [];

  await recordViewport({
    url: args.url,
    outDir,
    label: "desktop",
    viewport: DESKTOP_VIEWPORT,
    scrollSeconds: args.scrollSeconds,
    consoleLines,
  });

  if (!args.desktopOnly) {
    await recordViewport({
      url: args.url,
      outDir,
      label: "mobile",
      viewport: MOBILE_VIEWPORT,
      scrollSeconds: args.scrollSeconds,
      consoleLines,
    });
  }

  await writeConsoleLog(outDir, consoleLines);
  console.log("Nagranie zakończone.");
}

main().catch((err) => {
  console.error(err.message || err);
  process.exit(1);
});
