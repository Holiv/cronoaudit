// Frames of the README demo: the terminal run, then the report scrolling.
//
//   node demo.js --lang en|pt --frames <dir> [--fps 10] [--speed 1.45]
//   node demo.js --lang en --stills 4,9,14,20 --frames <dir>      check frames at stage times
//
// Run through build.sh, which first produces build/<lang>/ (the engine's real output).
// The report shown is the engine's own HTML, live in an iframe: this script only
// scrolls it and measures where its elements are, it changes nothing in it.
// The stage is square (1080 x 1080); build.sh scales the frames and writes the GIF.
const path = require("path");
const fs = require("fs");
const puppeteer = require("puppeteer-core");

const arg = (k, d) => { const i = process.argv.indexOf("--" + k); return i > 0 ? process.argv[i + 1] : d; };
const LANG = arg("lang", "en") === "pt" ? "pt" : "en";
const HERE = __dirname, REL = "build/" + LANG, B = path.join(HERE, REL);
const W = 1080, H = 1080;
const CHROME = process.env.CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const REPORT = "rodovia-ficticia-rev03--to--rodovia-ficticia-rev04-cycle.html";

(async () => {
  const term = fs.readFileSync(path.join(B, "term.txt"), "utf8").replace(/\n+$/, "").split("\n");
  const cmd = fs.readFileSync(path.join(B, "cmd.txt"), "utf8").trim();
  const dir = path.resolve(arg("frames", path.join(B, "frames")));
  fs.mkdirSync(dir, { recursive: true });

  const browser = await puppeteer.launch({
    executablePath: CHROME, headless: "new",
    args: ["--hide-scrollbars", "--force-color-profile=srgb", "--allow-file-access-from-files"],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
  await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: "light" }]);
  await page.goto("file://" + path.join(HERE, "stage.html") + "?fmt=11&lang=" + LANG, { waitUntil: "networkidle0" });
  await page.evaluate((d) => window.init(d), { term, cmd, reportName: REPORT });

  // the engine's report, live
  await page.evaluate((src) => new Promise((ok) => { const f = document.querySelector("#rep"); f.onload = ok; f.src = src; }),
    REL + "/out/" + REPORT);
  const frame = page.frames().find((f) => f.url().endsWith(REPORT));
  if (!frame) throw new Error("report frame not found");
  await frame.evaluate(() => document.documentElement.setAttribute("data-theme", "light"));
  await new Promise((r) => setTimeout(r, 400));
  const anchors = await frame.evaluate(() => {
    const box = (e) => { if (!e) throw new Error("report element missing"); const r = e.getBoundingClientRect(); return { x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height }; };
    const q = (s) => document.querySelector(s);
    const tiles = [...document.querySelectorAll("#g-avanco .tiles > *")];
    return {
      warn: box(q(".note")), finish: box(q(".veredito > div")), past: box(q("#c5")), pastHead: box(q("#c5 > *")),
      tiles: box(q("#g-avanco .tiles")), tileMov: box(tiles[2]), tileExp: box(tiles[3]), tileRes: box(tiles[4]),
      ask: box(q("#cobrar")),
    };
  });
  await page.evaluate((a) => window.layout(a), anchors);
  await page.evaluate(async () => {
    await Promise.all(["600 60px Fraunces", "italic 400 60px Fraunces", "400 60px Fraunces", "400 20px 'Source Code Pro'", "500 20px 'Source Code Pro'",
      "600 20px 'Source Code Pro'", "400 20px 'Source Sans 3'", "500 20px 'Source Sans 3'", "600 20px 'Source Sans 3'"].map((f) => document.fonts.load(f)));
    await document.fonts.ready;
  });
  const fonts = await page.evaluate(() => [...document.fonts].filter((f) => f.status === "loaded").map((f) => f.family).filter((v, i, a) => a.indexOf(v) === i));
  for (const need of ["Fraunces", "Source Code Pro", "Source Sans 3"])
    if (!fonts.some((f) => f.replace(/"/g, "") === need)) throw new Error("font not loaded: " + need + " (network?)");
  const { T0, T1 } = await page.evaluate(() => window.META);

  const shoot = async (t) => {
    const y = await page.evaluate((tt) => window.seek(tt), t);
    await frame.evaluate((yy) => window.scrollTo(0, yy), y);
    return page.screenshot({ type: "png", clip: { x: 0, y: 0, width: W, height: H } });
  };

  if (arg("stills")) {
    for (const s of arg("stills").split(",")) {
      const f = path.join(dir, `still-${parseFloat(s).toFixed(2).padStart(5, "0")}.png`);
      fs.writeFileSync(f, await shoot(parseFloat(s))); console.log(f);
    }
  } else {
    // the two scenes, played faster than the stage's own clock; the last fade-out is left off
    const fps = parseFloat(arg("fps", "10")), speed = parseFloat(arg("speed", "1.45"));
    const start = T0 + 0.4;                        // past the fade-in, so the first frame already shows the scene
    const total = Math.floor((T1 - 0.3 - start) / speed * fps);
    for (const f of fs.readdirSync(dir)) if (/^f\d+\.png$/.test(f)) fs.unlinkSync(path.join(dir, f));
    for (let i = 0; i < total; i++)
      fs.writeFileSync(path.join(dir, `f${String(i).padStart(4, "0")}.png`), await shoot(start + i / fps * speed));
    console.log(`${LANG}: ${total} frames at ${fps} fps, ${(total / fps).toFixed(1)} s`);
  }
  // close() has been seen to hang with headless Chrome; do not wait for it forever
  await Promise.race([browser.close(), new Promise((r) => setTimeout(r, 5000))]);
  process.exit(0);
})().catch((e) => { console.error(e); process.exit(1); });
