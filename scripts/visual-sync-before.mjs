/**
 * BEFORE harness — continuous scroll through all transitions (60s default).
 */
import { chromium, devices } from 'playwright';
import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.join(__dirname, '..');
const fixturePath = path.join(__dirname, 'fixtures', 'home-stack-visual-sync.html');
const durationMs = Number(process.argv[2]) || 60000;
const viewport = { width: 1440, height: 953 };
const port = 8765;

function contentType(filePath) {
  if (filePath.endsWith('.css')) return 'text/css';
  if (filePath.endsWith('.js')) return 'application/javascript';
  if (filePath.endsWith('.html')) return 'text/html';
  return 'application/octet-stream';
}

function startServer() {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const url = new URL(req.url, `http://127.0.0.1:${port}`);
      if (url.pathname === '/' || url.pathname === '/index.html') {
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(fs.readFileSync(fixturePath));
        return;
      }
      const rel = url.pathname.replace(/^\/+/, '');
      const filePath = path.join(rootDir, rel);
      if (!filePath.startsWith(rootDir) || !fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
        res.writeHead(404);
        res.end('Not found');
        return;
      }
      res.writeHead(200, { 'Content-Type': contentType(filePath) });
      res.end(fs.readFileSync(filePath));
    });
    server.listen(port, '127.0.0.1', () => resolve(server));
  });
}

async function continuousScroll(page, totalMs) {
  const maxScroll = await page.evaluate(() =>
    Math.max(document.documentElement.scrollHeight - window.innerHeight, 0)
  );
  const start = Date.now();
  while (Date.now() - start < totalMs) {
    const t = Math.min(1, (Date.now() - start) / totalMs);
    const y = Math.round(maxScroll * t);
    await page.evaluate((scrollY) => window.scrollTo(0, scrollY), y);
    await page.waitForTimeout(16);
  }
}

async function main() {
  const server = await startServer();
  const baseUrl = `http://127.0.0.1:${port}/`;

  try {
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
      viewport,
      reducedMotion: 'no-preference',
    });
    const page = await context.newPage();

    await page.goto(baseUrl, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForFunction(
      () =>
        typeof window.GICLEE_HOME_STACK_VISUAL_SYNC_CHECK === 'function' &&
        document.documentElement.classList.contains('giclee-home-stack'),
      { timeout: 30000 }
    );

    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(500);

    const reportPromise = page.evaluate(async (ms) => {
      return window.GICLEE_HOME_STACK_VISUAL_SYNC_CHECK(ms);
    }, durationMs);

    await continuousScroll(page, durationMs);
    const desktopReport = await reportPromise;

    const mobileContext = await browser.newContext({
      ...devices['iPhone 12'],
      reducedMotion: 'no-preference',
    });
    const mobilePage = await mobileContext.newPage();
    await mobilePage.goto(baseUrl, { waitUntil: 'networkidle' });
    const mobileReport = await mobilePage.evaluate(() =>
      window.GICLEE_HOME_STACK_VISUAL_SYNC_CHECK(3000)
    );

    const rmContext = await browser.newContext({ viewport, reducedMotion: 'reduce' });
    const rmPage = await rmContext.newPage();
    await rmPage.goto(baseUrl, { waitUntil: 'networkidle' });
    const reducedMotionReport = await rmPage.evaluate(() =>
      window.GICLEE_HOME_STACK_VISUAL_SYNC_CHECK(3000)
    );

    await browser.close();

    const summary = {
      environment: 'local-fixture',
      note: 'Shopify preview unavailable; fixture uses live stack CSS/JS + production-like DOM',
      viewport,
      durationMs,
      layers: ['3', '4', '5', '6'].map((layer) => {
        const l = desktopReport.layers?.[layer] || {};
        return {
          layer,
          sampleCount: l.sampleCount ?? 0,
          baseline: l.baseline,
          minDeltaTop: l.minDeltaTop,
          maxDeltaTop: l.maxDeltaTop,
          maxDeltaVariation: l.maxDeltaVariation,
          variableMismatches: l.variableMismatches ?? 0,
          visualMismatches: l.visualMismatches ?? 0,
        };
      }),
      variableMismatches: desktopReport.variableMismatches,
      visualMismatches: desktopReport.visualMismatches,
      maxVisualDeltaVariation: desktopReport.maxVisualDeltaVariation,
      mobileNative: mobileReport,
      reducedMotion: reducedMotionReport,
    };

    console.log('\n=== BEFORE SUMMARY ===');
    console.log(JSON.stringify(summary, null, 2));
  } finally {
    server.close();
  }
}

main().catch((err) => {
  console.error('FAILED:', err.message);
  process.exitCode = 1;
});
