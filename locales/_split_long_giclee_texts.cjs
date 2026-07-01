const fs = require('fs');
const path = require('path');

const MAX = 980;
const ALL_PATH = path.join(__dirname, '_giclee_i18n_all.json');
const data = JSON.parse(fs.readFileSync(ALL_PATH, 'utf8'));

function splitHtml(html) {
  if (html.length <= MAX) return null;
  const parts = [];
  let rest = html;
  while (rest.length > MAX) {
    let cut = rest.lastIndexOf('</p>', MAX);
    if (cut < 200) cut = rest.lastIndexOf('<br/>', MAX);
    if (cut < 200) cut = MAX;
    else cut += 4;
    parts.push(rest.slice(0, cut));
    rest = rest.slice(cut);
  }
  if (rest) parts.push(rest);
  return parts;
}

let splitCount = 0;
for (const locale of Object.keys(data)) {
  const blocks = data[locale].giclee.blocks;
  for (const [blockId, fields] of Object.entries(blocks)) {
    const html = fields.text;
    if (typeof html !== 'string' || html.length <= MAX) continue;

    const parts = splitHtml(html);
    if (!parts || parts.length < 2) {
      console.warn('could not split', locale, blockId, html.length);
      continue;
    }

    delete fields.text;
    parts.forEach((part, i) => {
      fields[`text_part${i + 1}`] = part;
      if (part.length > MAX) {
        console.warn('part still long', locale, blockId, i + 1, part.length);
      }
    });
    if (locale === 'en') splitCount++;
  }
}

fs.writeFileSync(ALL_PATH, JSON.stringify(data, null, 2) + '\n', 'utf8');
console.log('split blocks (en count):', splitCount);
