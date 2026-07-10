import { chromium } from 'playwright';
import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.join(__dirname, '..');
const fixturePath = path.join(__dirname, 'fixtures', 'home-stack-visual-sync.html');
const port = 8767;

function startServer() {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      if (req.url === '/') {
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(fs.readFileSync(fixturePath));
        return;
      }
      const filePath = path.join(rootDir, req.url.replace(/^\/+/, ''));
      res.writeHead(200);
      res.end(fs.readFileSync(filePath));
    });
    server.listen(port, '127.0.0.1', () => resolve(server));
  });
}

const server = await startServer();
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 953 } });
await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: 'networkidle' });
await page.waitForTimeout(2000);

for (const scrollY of [2640, 2760, 3000, 4000, 5000]) {
  await page.evaluate((y) => window.scrollTo(0, y), scrollY);
  await page.waitForTimeout(300);
  const sample = await page.evaluate(() => {
    const layer = '4';
    const pairIndex = parseInt(layer, 10) - 2;
    const stackEls = Array.from(document.querySelectorAll('.shopify-section[data-giclee-home-stack]:not(.giclee-home-stack-divider)'));
    // wrong - need actual stackEls from closure - use debug
    const snap = window.GICLEE_HOME_STACK_DEBUG();
    const section = document.querySelector(
      `.shopify-section[data-giclee-home-stack="${layer}"]:not(.giclee-home-stack-divider)`
    );
    const divider = document.querySelector(
      `.giclee-home-stack-divider--scroll[data-giclee-home-stack="${layer}"]`
    );
    const line = divider?.querySelector('.divider__line');
    const clipHost = section?.querySelector('.background-image-container');
    const lineRect = line?.getBoundingClientRect();
    const clipRect = clipHost?.getBoundingClientRect();
    const vh = window.innerHeight;
    const vw = window.innerWidth;
    const inVp = (r) => r && r.bottom > 0 && r.top < vh && r.right > 0 && r.left < vw;
    const activePair = snap.pairs[pairIndex];
    return {
      scrollY: window.scrollY,
      activePair: activePair?.layer,
      phase: activePair?.phase,
      lineRect: lineRect
        ? {
            top: Math.round(lineRect.top * 10) / 10,
            bottom: Math.round(lineRect.bottom * 10) / 10,
          }
        : null,
      clipRect: clipRect
        ? {
            top: Math.round(clipRect.top * 10) / 10,
            bottom: Math.round(clipRect.bottom * 10) / 10,
          }
        : null,
      lineInVp: inVp(lineRect),
      clipInVp: inVp(clipRect),
      deltaTop: lineRect && clipRect ? Math.round((clipRect.top - lineRect.bottom) * 10) / 10 : null,
    };
  });
  console.log(JSON.stringify(sample));
}

await browser.close();
server.close();
