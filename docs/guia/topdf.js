// Print the assembled guide to PDF and check that no sheet overflows.
//
//   NODE_PATH=<manual>/node_modules node topdf.js guia-pt.html guia-pt.pdf
//
// The guide is set as fixed A4 sheets with their own running foot, so the PDF is
// printed with no margins and no header or footer template. Uses puppeteer-core
// driving the Chrome already installed on the machine, as the manual does.
const path = require("path");
const fs = require("fs");

const [,, input, output] = process.argv;
if (!input || !output) {
  console.error("usage: node topdf.js <guia.html> <guia.pdf>");
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
  await page.emulateMediaType("print");
  await page.goto("file://" + path.resolve(input), { waitUntil: "networkidle0" });
  await page.evaluateHandle("document.fonts.ready");
  // A sheet overflows when anything in it reaches past the line of its running foot.
  const problems = await page.evaluate((process_verbose) => {
    const out = [];
    document.querySelectorAll(".page").forEach((sheet, i) => {
      const box = sheet.getBoundingClientRect();
      const foot = sheet.querySelector(".foot");
      const limit = foot ? foot.getBoundingClientRect().top - 4 : box.bottom - 30;
      let low = 0, wide = 0;
      sheet.querySelectorAll("*").forEach(el => {
        if (el === foot || (foot && foot.contains(el))) return;
        if (el.closest(".shot")) return;  // report captures are cropped on purpose
        const r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) return;
        low = Math.max(low, r.bottom);
        wide = Math.max(wide, r.right);
      });
      if (process_verbose) out.push(`page ${i + 1}: filled ${Math.round((low - box.top) / (limit - box.top) * 100)}%`);
      if (low > limit) out.push(`page ${i + 1}: content runs ${Math.round((low - limit) / 3.78)} mm past the foot`);
      if (wide > box.right + 1) out.push(`page ${i + 1}: content runs ${Math.round((wide - box.right) / 3.78)} mm past the right edge`);
    });
    const fonts = [...document.fonts].filter(f => f.status === "loaded").map(f => f.family.replace(/"/g, ""));
    for (const need of ["Fraunces", "Source Sans 3", "Source Code Pro"]) {
      if (!fonts.includes(need)) out.push(`font not loaded: ${need}`);
    }
    return out;
  }, !!process.env.GUIA_VERBOSE);
  await page.pdf({
    path: output, format: "A4", printBackground: true, preferCSSPageSize: true,
    displayHeaderFooter: false, margin: { top: 0, right: 0, bottom: 0, left: 0 },
  });
  await browser.close();
  console.log(output);
  const bad = problems.filter(p => !/filled \d+%$/.test(p));
  problems.forEach(p => console.error("CHECK " + p));
  if (bad.length) process.exit(3);
})().catch(e => { console.error(e.message); process.exit(1); });
