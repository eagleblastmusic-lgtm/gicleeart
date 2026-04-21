/**
 * Minimal OAuth server: offline session token for Admin API (read/write products).
 *
 * 1. Copy .env.example -> .env and fill SHOPIFY_API_KEY / SHOPIFY_API_SECRET (Partner Dashboard → Credentials).
 * 2. Set HOST to match an allowed redirect URL (see shopify.app.toml [auth] redirect_urls).
 * 3. In Partner Dashboard → App setup, add the same redirect URL if not synced: {HOST}/auth/callback
 * 4. npm run oauth
 * 5. Open http://127.0.0.1:3000 (or your HOST), click the auth link with ?shop=TWOJ-SKLEP.myshopify.com
 * 6. After approval, token is saved to .shopify_session.json (gitignored).
 */
import dotenv from 'dotenv';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import express from 'express';
import '@shopify/shopify-api/adapters/node';
import { shopifyApi, ApiVersion } from '@shopify/shopify-api';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// Zawsze plik z folderu cursor-api (nie zależy od cwd). override: nadpisuje np. SHOPIFY_API_KEY=test z testów w terminalu.
dotenv.config({ path: path.join(__dirname, '.env'), override: true });

const API_KEY = String(process.env.SHOPIFY_API_KEY || '')
  .trim()
  .replace(/^\uFEFF/, '');
const API_SECRET = String(process.env.SHOPIFY_API_SECRET || '')
  .trim()
  .replace(/^\uFEFF/, '');

const PORT = Number(process.env.PORT || 3000);
const HOST = process.env.HOST || `http://127.0.0.1:${PORT}`;
const TOKEN_FILE =
  process.env.SHOPIFY_SESSION_FILE ||
  path.join(__dirname, '.shopify_session.json');

const url = new URL(HOST);
const hostName = url.host;
const hostScheme = url.protocol === 'https:' ? 'https' : 'http';

if (!API_KEY || !API_SECRET) {
  console.error('Missing SHOPIFY_API_KEY or SHOPIFY_API_SECRET. Copy .env.example to .env and fill values.');
  process.exit(1);
}
if (API_KEY === 'test') {
  console.error(
    'SHOPIFY_API_KEY jest ustawione na "test" (stara zmienna w terminalu?). Zamknij terminal, otwórz nowy, albo usuń: Remove-Item Env:SHOPIFY_API_KEY'
  );
  process.exit(1);
}
console.log('[oauth] Client ID wczytany (początek):', API_KEY.slice(0, 6) + '…');

const shopify = shopifyApi({
  apiKey: API_KEY,
  apiSecretKey: API_SECRET,
  apiVersion: ApiVersion.April26,
  scopes: (process.env.SCOPES || 'read_products,write_products')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean),
  hostName,
  hostScheme,
  isEmbeddedApp: false,
});

const app = express();

/** Diagnostyka: czy ten proces widzi dobry Client ID (powinno zaczynać się jak w Partner Dashboard, NIE "test"). */
app.get('/debug', (req, res) => {
  const key = String(shopify.config.apiKey || '').trim();
  const payload = {
    cwd: process.cwd(),
    envFile: path.join(__dirname, '.env'),
    clientIdPrefix: key.slice(0, 8),
    clientIdLength: key.length,
    looksLikeTest: key === 'test',
    shopFromEnv: (process.env.SHOP || '').trim() || null,
  };
  res.json(payload);
});

app.get('/', (req, res) => {
  const exampleShop = process.env.SHOP || 'twoj-sklep.myshopify.com';
  const start = `${HOST}/auth?shop=${encodeURIComponent(exampleShop)}`;
  res.type('html').send(`<!doctype html>
<html><head><meta charset="utf-8"><title>Shopify OAuth</title></head>
<body>
  <h1>OAuth — Cursor API</h1>
  <p>Ustaw w <code>.env</code> zmienną <code>SHOP</code> na adres sklepu (np. <code>gicleeart.myshopify.com</code>), albo otwórz link ręcznie:</p>
  <p><a href="${start}">${start}</a></p>
  <p>Po zalogowaniu i zatwierdzeniu uprawnień token zapisze się w pliku <code>.shopify_session.json</code>.</p>
</body></html>`);
});

app.get('/auth', async (req, res) => {
  const shopRaw = req.query.shop || process.env.SHOP;
  if (!shopRaw || typeof shopRaw !== 'string') {
    res.status(400).send('Missing ?shop=twoj-sklep.myshopify.com (or set SHOP in .env)');
    return;
  }
  const shop = shopify.utils.sanitizeShop(shopRaw, true);
  console.log(
    '[auth] OAuth begin, shop=',
    shop,
    'client_id prefix=',
    String(shopify.config.apiKey).slice(0, 8)
  );
  await shopify.auth.begin({
    shop,
    callbackPath: '/auth/callback',
    isOnline: false,
    rawRequest: req,
    rawResponse: res,
  });
});

app.get('/auth/callback', async (req, res) => {
  try {
    const callback = await shopify.auth.callback({
      rawRequest: req,
      rawResponse: res,
    });
    const session = callback.session;
    const payload = {
      shop: session.shop,
      accessToken: session.accessToken,
      scope: session.scope,
      isOnline: session.isOnline,
    };
    await fs.writeFile(TOKEN_FILE, JSON.stringify(payload, null, 2), 'utf8');
    const safe = {
      ...payload,
      accessToken: payload.accessToken
        ? `***${String(payload.accessToken).slice(-6)}`
        : null,
    };
    res.type('html').send(`<!doctype html>
<html><head><meta charset="utf-8"><title>OK</title></head>
<body>
  <h1>Token zapisany</h1>
  <p>Plik: <code>${TOKEN_FILE}</code></p>
  <pre>${JSON.stringify(safe, null, 2)}</pre>
  <p>Możesz zamknąć serwer (Ctrl+C).</p>
</body></html>`);
  } catch (err) {
    console.error(err);
    res.status(500).type('html').send(`<pre>${String(err && err.message ? err.message : err)}</pre>`);
  }
});

const server = app.listen(PORT, '127.0.0.1', () => {
  console.log(`OAuth server listening on ${HOST}`);
  console.log(`Open: ${HOST}/`);
  console.log('Serwer działa — zostaw ten terminal otwarty do końca logowania (Ctrl+C kończy).');
});

server.on('error', (err) => {
  console.error('Nie można nasłuchiwać na porcie', PORT, ':', err.message);
  if (err.code === 'EADDRINUSE') {
    console.error('Port zajęty — zamknij inny proces (np. stary node) albo ustaw PORT=3001 w .env');
  }
  process.exit(1);
});
