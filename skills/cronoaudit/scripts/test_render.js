// Execute the generated report's own renderer against a minimal DOM shim.
//
// This exists because of a real bug: the data marker sits where a value goes and
// the template keeps a `null` after it so it stays valid JavaScript un-filled.
// Replacing only the comment left `const DATA = {...} null;` -- a syntax error
// that renders a BLANK PAGE with no error anywhere a person would look. The HTML
// was well-formed, the JSON was valid, the file size was right, and the report
// was empty. Checking that the file exists proves nothing; this runs it.
const fs = require('fs');
const file = process.argv[2];
// Arguments after the file are sections that must be present; `--forbid=<regex>`
// names a pattern that must NOT appear in what a person reads (a local path, a
// raw ISO timestamp, a negative zero).
const rest = process.argv.slice(3);
const required = rest.filter(a => !a.startsWith('--forbid='));
const forbidden = rest.filter(a => a.startsWith('--forbid=')).map(a => a.slice(9));

const src = fs.readFileSync(file, 'utf8');
const m = src.match(/<script>([\s\S]*?)<\/script>\s*<\/body>/);
if (!m) { console.error('no script block found in ' + file); process.exit(2); }

const store = {};
global.document = {
  getElementById: id => store[id] || (store[id] = {
    id,
    set innerHTML(v) { this._h = v },
    get innerHTML() { return this._h || '' },
  }),
  documentElement: { style: { setProperty() {} }, setAttribute() {} },
};
global.getComputedStyle = () => ({ getPropertyValue: () => '#fbfaf8' });
global.window = { print() {} };

try {
  new Function(m[1])();
} catch (e) {
  console.error('the report script threw: ' + e.message);
  process.exit(1);
}

const html = (store.app && store.app.innerHTML) || '';
if (!html || /^Rendering/.test(html)) {
  console.error('the renderer produced nothing -- the page would be blank');
  process.exit(1);
}
const missing = required.filter(s => !html.includes(s));
if (missing.length) {
  console.error('missing expected sections: ' + JSON.stringify(missing));
  process.exit(1);
}
const text = html.replace(/<[^>]*>/g, ' ');
const leaked = forbidden
  .map(p => [p, text.match(new RegExp(p))])
  .filter(([, hit]) => hit)
  .map(([p, hit]) => `${p} matched "${hit[0]}"`);
if (leaked.length) {
  console.error('forbidden content in the rendered report: ' + leaked.join('; '));
  process.exit(1);
}
console.log(`rendered ${html.length} chars, ${required.length} sections present`);
