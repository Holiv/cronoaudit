// Screenshot parts of a cronoaudit report, for the illustrated guide.
//
//   NODE_PATH=<manual>/node_modules node shots.js <report.html> <out.png> <selector> [width] [maxHeight] [scale]
//
// The report is the engine's own HTML, opened untouched in the Chrome already on
// the machine and forced to its light theme. A selector of "page" captures the
// top of the page. maxHeight crops the capture (CSS pixels).
const path = require("path");
const fs = require("fs");

const [,, input, output, selector, width, maxHeight, scale] = process.argv;
if (!input || !output || !selector) {
  console.error("usage: node shots.js <report.html> <out.png> <selector|page> [width] [maxHeight] [scale]");
  process.exit(2);
}
const CHROME = process.env.CHROME_PATH || [
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
].find(p => fs.existsSync(p));
if (!CHROME) { console.error("no Chrome found; set CHROME_PATH"); process.exit(1); }

(async () => {
  const puppeteer = require("puppeteer-core");
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: "new" });
  const page = await browser.newPage();
  const w = parseInt(width || "1040", 10);
  await page.setViewport({ width: w, height: 900, deviceScaleFactor: parseFloat(scale || "2") });
  await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: "light" }]);
  await page.goto("file://" + path.resolve(input), { waitUntil: "networkidle0" });
  await page.evaluate(() => document.documentElement.setAttribute("data-theme", "light"));
  let clip;
  if (selector === "page") {
    clip = { x: 0, y: 0, width: w, height: parseInt(maxHeight || "900", 10) };
  } else {
    const el = await page.$(selector);
    if (!el) { console.error("selector not found: " + selector); process.exit(1); }
    await el.evaluate(e => e.scrollIntoView());
    const box = await el.evaluate(e => { const r = e.getBoundingClientRect(); return { x: r.left + scrollX, y: r.top + scrollY, width: r.width, height: r.height }; });
    clip = { x: Math.max(0, box.x - 8), y: Math.max(0, box.y - 8), width: box.width + 16, height: box.height + 16 };
    if (maxHeight) clip.height = Math.min(clip.height, parseInt(maxHeight, 10));
  }
  await page.screenshot({ path: output, clip });
  await browser.close();
  console.log(output);
})().catch(e => { console.error(e.message); process.exit(1); });
