const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const REPO_ROOT = path.resolve(ROOT, '..', '..');
const LOCALES_ROOT = path.join(REPO_ROOT, 'locales');
const MASTER_PATH = path.join(ROOT, 'giclee_i18n_all.json');
const FALLBACK_SNIPPET_PATH = path.join(
  REPO_ROOT,
  'snippets',
  'giclee-i18n-defaults-json.liquid',
);
const CHECK_ONLY = process.argv.includes('--check');

const LOCALE_FILES = {
  en: 'en.default.json',
  de: 'de.json',
  fr: 'fr.json',
  es: 'es.json',
  nl: 'nl.json',
  it: 'it.json',
  pl: 'pl.json',
};

function detectEol(raw) {
  return raw.includes('\r\n') ? '\r\n' : '\n';
}

function normalizeEol(value, eol) {
  return value.replace(/\r\n|\r|\n/g, eol);
}

function parseShopifyJson(raw, fileName) {
  const headerMatch = raw.match(/^(\s*\/\*[\s\S]*?\*\/\s*)/);
  const header = headerMatch ? headerMatch[1] : '';
  let body = headerMatch ? raw.slice(header.length) : raw;

  body = body.replace(/^\s*\/\/.*$/gm, '');
  body = body.replace(/,\s*([}\]])/g, '$1');

  try {
    return {
      header,
      data: JSON.parse(body),
    };
  } catch (error) {
    throw new Error(`${fileName}: invalid Shopify JSON: ${error.message}`);
  }
}

function buildLocaleOutput(locale, fileName, master) {
  const filePath = path.join(LOCALES_ROOT, fileName);
  const raw = fs.readFileSync(filePath, 'utf8');
  const eol = detectEol(raw);
  const { header, data } = parseShopifyJson(raw, fileName);

  const masterGiclee = master[locale] && master[locale].giclee;

  if (!masterGiclee || typeof masterGiclee !== 'object') {
    throw new Error(`Missing master translations for locale: ${locale}`);
  }

  if (locale === 'pl') {
    const ui = masterGiclee.ui;

    if (!ui || typeof ui !== 'object' || Array.isArray(ui)) {
      throw new Error('Master locale pl must contain giclee.ui');
    }

    data.giclee = { ui };
  } else {
    data.giclee = masterGiclee;
  }

  const serialized = header + JSON.stringify(data, null, 2) + '\n';

  return {
    label: `${fileName} ${locale}`,
    filePath,
    raw,
    nextRaw: normalizeEol(serialized, eol),
  };
}

function buildFallbackOutput(master) {
  const ui = master.pl &&
    master.pl.giclee &&
    master.pl.giclee.ui;

  if (!ui || typeof ui !== 'object' || Array.isArray(ui)) {
    throw new Error('Master locale pl must contain giclee.ui');
  }

  const raw = fs.readFileSync(FALLBACK_SNIPPET_PATH, 'utf8');
  const eol = detectEol(raw);

  const header = (
    '{%- comment -%} ' +
    'Auto: Polish defaults for giclee.ui when locale keys missing. ' +
    'Source: tools/i18n/giclee_i18n_all.json ' +
    '{%- endcomment -%}\n'
  );

  const serialized = header + JSON.stringify(ui, null, 2) + '\n';

  return {
    label: 'giclee-i18n-defaults-json.liquid pl-fallback',
    filePath: FALLBACK_SNIPPET_PATH,
    raw,
    nextRaw: normalizeEol(serialized, eol),
  };
}

function processOutput(output) {
  if (output.raw === output.nextRaw) {
    console.log(`unchanged ${output.label}`);
    return false;
  }

  if (CHECK_ONLY) {
    console.error(`out-of-date ${output.label}`);
    return true;
  }

  fs.writeFileSync(output.filePath, output.nextRaw, 'utf8');
  console.log(`generated ${output.label}`);
  return true;
}

function main() {
  const master = JSON.parse(fs.readFileSync(MASTER_PATH, 'utf8'));
  const outputs = [];

  for (const [locale, fileName] of Object.entries(LOCALE_FILES)) {
    outputs.push(buildLocaleOutput(locale, fileName, master));
  }

  outputs.push(buildFallbackOutput(master));

  let changedCount = 0;

  for (const output of outputs) {
    if (processOutput(output)) {
      changedCount += 1;
    }
  }

  if (CHECK_ONLY && changedCount > 0) {
    console.error(
      `\n${changedCount} generated output(s) differ from the canonical source.`,
    );
    process.exitCode = 1;
    return;
  }

  if (CHECK_ONLY) {
    console.log(
      '\nRESULT: all generated outputs match the canonical source',
    );
  }
}

main();
