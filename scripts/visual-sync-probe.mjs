import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const localStackJs = fs.readFileSync(path.join(__dirname, '..', 'assets', 'giclee-home-stack.js'), 'utf8');

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 953 } });
await page.route('**/giclee-home-stack.js*', (route) =>
  route.fulfill({ status: 200, contentType: 'application/javascript', body: localStackJs })
);

try {
  const response = await page.goto('http://127.0.0.1:9292/', {
    waitUntil: 'commit',
    timeout: 120000,
  });
  console.log('status', response?.status());
  await page.waitForTimeout(15000);
  const info = await page.evaluate(() => ({
    url: location.href,
    stack: window.GICLEE_HOME_STACK,
    helper: typeof window.GICLEE_HOME_STACK_VISUAL_SYNC_CHECK,
    htmlClass: document.documentElement.className,
    bodyText: document.body?.innerText?.slice(0, 120),
    stackSections: document.querySelectorAll('[data-giclee-home-stack]').length,
  }));
  console.log(JSON.stringify(info, null, 2));
} catch (e) {
  console.error('ERR', e.message);
}
await browser.close();
