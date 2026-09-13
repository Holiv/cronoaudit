// Print the assembled manual to PDF with running heads and page numbers.
//
//   node topdf.js manual-pt.html manual-pt.pdf "cronoaudit · manual técnico"
//
// Uses puppeteer-core driving the Chrome already installed on the machine, so
// nothing large is downloaded. Chromium does not render CSS @page margin boxes,
// which is where page numbers would otherwise live; the header and footer
// templates below are the supported way to get them.
const path = require("path");
const fs = require("fs");

const [,, input, output, running] = process.argv;
if (!input || !output) {
  console.error("usage: node topdf.js <manual.html> <manual.pdf> [running head]");
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
  await page.goto("file://" + path.resolve(input), { waitUntil: "networkidle0" });
  await page.evaluateHandle("document.fonts.ready");
  const foot = `
    <div style="width:100%;font:8.5px 'Source Code Pro',monospace;color:#6B6E74;padding:0 20mm;display:flex;justify-content:space-between;">
      <span>${running || ""}</span><span class="pageNumber"></span>
    </div>`;
  await page.pdf({
    path: output, format: "A4", printBackground: true, preferCSSPageSize: true,
    displayHeaderFooter: true, headerTemplate: "<div></div>", footerTemplate: foot,
    margin: { top: "22mm", right: "20mm", bottom: "24mm", left: "20mm" },
    outline: true,
  });
  await browser.close();
  console.log(output);
})().catch(e => { console.error(e.message); process.exit(1); });
