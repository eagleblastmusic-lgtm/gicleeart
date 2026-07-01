const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname);
const ALL = JSON.parse(fs.readFileSync(path.join(ROOT, '_giclee_i18n_all.json'), 'utf8'));

const LOCALE_FILES = {
  en: 'en.default.json',
  de: 'de.json',
  fr: 'fr.json',
  es: 'es.json',
  nl: 'nl.json',
  it: 'it.json',
  pl: 'pl.json',
};

function stripComments(raw) {
  const headerMatch = raw.match(/^(\/\*[\s\S]*?\*\/\s*)/);
  const header = headerMatch ? headerMatch[1] : '';
  let body = headerMatch ? raw.slice(headerMatch[1].length) : raw;
  body = body.replace(/^\s*\/\/.*$/gm, '');
  body = body.replace(/,\s*([}\]])/g, '$1');
  return { header, body };
}

function mergeGiclee(locale, fileName) {
  const filePath = path.join(ROOT, fileName);
  const { header, body } = stripComments(fs.readFileSync(filePath, 'utf8'));
  const data = JSON.parse(body);
  if (locale === 'pl') {
    data.giclee = { ui: ALL.pl.giclee.ui };
  } else {
    data.giclee = ALL[locale].giclee;
  }
  fs.writeFileSync(filePath, header + JSON.stringify(data, null, 2) + '\n', 'utf8');
  console.log('merged', fileName, locale);
}

for (const [locale, fileName] of Object.entries(LOCALE_FILES)) {
  mergeGiclee(locale, fileName);
}
