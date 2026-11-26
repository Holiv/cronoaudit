// The still images of the README and the LEIA-ME, in English and in Portuguese:
//   banner.png           the banner at the top (2x)
//   social-preview.png   the same content at exactly 1280 x 640, for the repository settings
//   how-it-works.png     the engine, the skill and the three ways to use them (2x)
//   hero.png ... install.png   the report crops of crops/<lang>/, inside the brand frame
//
// Run through build.sh. The crops are real output of the engine for the fictitious
// example. The frame adds paper, a browser bar and, where the README talks about one
// number, a red outline around it. No pixel inside a crop is changed: it is drawn at
// exactly its own size (2 device pixels per CSS pixel).
const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer-core");
const CHROME = process.env.CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const HERE = __dirname;
const REPO = "github.com/Holiv/cronoaudit";
const URL_CYCLE = "~/cronoaudit-exemplo/rodovia-ficticia-rev03--to--rodovia-ficticia-rev04-cycle.html";
const URL_REVIEW = "~/cronoaudit-exemplo/rodovia-ficticia-rev04-review.html";

let LANG = "en";
const L = (en, pt) => (LANG === "pt" ? pt : en);
const wm = 'crono<em>audit</em>';

// ---- the crops: which report each comes from, and the number the README points at.
// key = [x, y, w, h] in the crop's own pixels; { en, pt } where the two layouts differ.
const CROPS = [
  { name: "hero", url: URL_CYCLE, key: { en: [82, 1362, 210, 110], pt: [82, 1448, 210, 110] } },             // +21 days
  { name: "past-rewritten", url: URL_CYCLE, key: [1540, 84, 212, 66] },                                      // 2 activities
  { name: "progress", url: URL_CYCLE, key: [1458, 388, 340, 236] },                                          // the residue
  { name: "deadlines", url: URL_CYCLE, key: { en: [1296, 1196, 90, 54], pt: [1432, 1196, 90, 54] } },        // 1 day of margin
  { name: "review-top", url: URL_REVIEW, key: [86, 656, 392, 124] },                                         // weighted progress
  { name: "s-curve", url: URL_REVIEW, key: { en: [928, 370, 428, 198], pt: [928, 416, 428, 198] } },         // SPI
  { name: "ask", url: URL_CYCLE },
  { name: "install", plain: true },                                                                          // a terminal, no browser bar
];
function pngSize(file) {
  const b = fs.readFileSync(file);
  if (b.toString("ascii", 12, 16) !== "IHDR") throw new Error("not a PNG: " + file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}

function banner(cls) {
  return `<div class="shot strip banner ${cls}" data-out="${cls === "social" ? "social-preview" : "banner"}" data-scale="${cls === "social" ? 1 : 2}">
  <p class="logo">${wm}</p>
  <div class="rule"></div>
  <h1>${L("An audit for construction schedules that runs <em>on your computer.</em>", "Auditoria de cronograma de obra, <em>no seu computador.</em>")}</h1>
  <p class="parts">${L("A <b>local Python engine</b>, plus an <b>Agent Skill</b> for your AI agent.", "Um <b>motor local em Python</b> e uma <b>Agent Skill</b> para o seu agente de IA.")}</p>
  <div class="foot"><span>${REPO}</span><span>${L("open source · reads MS Project · sends nothing", "código aberto · lê MS Project · não envia nada")}</span></div>
</div>`;
}

function how() {
  // fixed layout, so the arrows can be drawn between known points
  const way = (y, n, h3, p) => `<div class="box way" style="left:48px;top:${y}px;width:292px;height:120px"><span class="n">${n}</span><h3>${h3}</h3><p>${p}</p></div>`;
  const arrow = (x1, y, x2) => `<path d="M${x1} ${y} H${x2}" stroke="#17191C" stroke-width="2.5" fill="none" marker-end="url(#ah)"/>`;
  return `<div class="shot strip how" data-out="how-it-works" data-scale="2">
  <div class="head"><span class="wm">${wm}</span><span class="tag">${L("How it works", "Como funciona")}</span></div>
  <h2>${L("An engine that measures. <em>Three ways to use it.</em>", "Um motor que mede. <em>Três formas de usar.</em>")}</h2>
  <span class="col" style="left:48px;top:164px">${L("You prefer", "Você prefere")}</span>
  ${way(186, "A", L("Talking to an AI agent", "Conversar com um agente de IA"), L("<code>analyse Rev04.mpp</code>", "<code>analise o Rev04.mpp</code>"))}
  ${way(318, "B", L("Clicking a button inside MS Project", "Clicar num botão dentro do MS Project"), "")}
  ${way(450, "C", L("No AI at all", "Sem IA nenhuma"), L("one command, on the exported XML", "um comando, sobre o XML exportado"))}
  <div class="box" style="left:394px;top:166px;width:300px;height:160px"><p class="lab">${L("The skill", "A skill")}</p>
    <h3>${L("Lets your AI agent run the engine", "Deixa o seu agente de IA rodar o motor")}</h3>
    <p>${L("and talk about the measured numbers.", "e conversar sobre os números medidos.")}</p></div>
  <div class="box engine" style="left:800px;top:176px;width:226px;height:390px"><p class="lab">${L("The engine", "O motor")}</p>
    <h3>${L("Measures on your computer", "Mede no seu computador")}</h3>
    <ul><li>${L("Local", "Local")}</li><li>${L("Python only", "Só Python")}</li><li>${L("Reads the MS Project XML", "Lê o XML do MS Project")}</li><li><b>${L("Sends nothing", "Não envia nada")}</b></li></ul></div>
  <div class="box report" style="left:1076px;top:296px;width:156px;height:150px"><p class="lab">${L("Result", "Resultado")}</p>
    <h3>${L("Report in the browser", "Relatório no navegador")}</h3></div>
  <svg width="1280" height="640" viewBox="0 0 1280 640">
    <defs><marker id="ah" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="#17191C"/></marker></defs>
    ${arrow(340, 246, 392)}
    ${arrow(694, 222, 798)}<text x="746" y="212" text-anchor="middle">${L("runs", "roda")}</text>
    ${arrow(800, 274, 696)}<text x="746" y="296" text-anchor="middle">${L("numbers", "números")}</text>
    ${arrow(340, 378, 798)}<text x="570" y="368" text-anchor="middle">${L("the Cronoaudit tab", "a aba Cronoaudit")}</text>
    ${arrow(340, 510, 798)}
    ${arrow(1026, 371, 1074)}
  </svg>
  <div class="note"><span><b>${L("In all three, the engine runs on your computer and sends nothing.", "Nos três, o motor roda no seu computador e não envia nada.")}</b></span><span>${REPO}</span></div>
</div>`;
}

function framed(c) {
  const file = path.join(HERE, "crops", LANG, c.name + ".png");
  const { w, h } = pngSize(file);
  if (w % 2 || h % 2) throw new Error("odd crop size: " + file);
  const cw = w / 2, ch = h / 2;                                   // the crop was captured at 2x
  const k = c.key ? (Array.isArray(c.key) ? c.key : c.key[LANG]) : null;
  const key = k ? `<div class="key" style="left:${k[0] / 2}px;top:${k[1] / 2}px;width:${k[2] / 2}px;height:${k[3] / 2}px"></div>` : "";
  const img = `<div class="crop" style="width:${cw}px;height:${ch}px"><img src="../crops/${LANG}/${c.name}.png" width="${cw}" height="${ch}">${key}</div>`;
  const body = c.plain ? `<div class="plain">${img}</div>`
    : `<div class="browser"><div class="bar"><i></i><i></i><i></i><span class="url">${c.url}</span><span class="mark real">${L("real report", "relatório real")}</span></div>${img}</div>`;
  const width = cw + (c.plain ? 0 : 4) + 76;
  return `<div class="shot frame" data-out="${c.name}" data-scale="2" style="width:${width}px">
  <div class="top"><span class="wm">${wm}</span><span class="tag">${c.plain ? L("real installer output", "saída real do instalador") : L("real output · fictitious example", "saída real · exemplo fictício")}</span></div>
  ${body}
</div>`;
}

(async () => {
  const css = fs.readFileSync(path.join(HERE, "style.css"), "utf8");
  fs.mkdirSync(path.join(HERE, "build"), { recursive: true });
  const rects = [];
  const chrome = await puppeteer.launch({ executablePath: CHROME, headless: "new", args: ["--force-color-profile=srgb"] });
  for (const lang of ["en", "pt"]) {
    LANG = lang;
    const out = path.join(HERE, "..", lang);
    fs.mkdirSync(out, { recursive: true });
    const html = `<!doctype html><html lang="${lang === "pt" ? "pt-BR" : "en"}"><head><meta charset="utf-8"><title>cronoaudit README images</title><style>${css}</style></head><body>
${banner("readme")}\n${banner("social")}\n${how()}\n${CROPS.map(framed).join("\n")}\n</body></html>`;
    const src = path.join(HERE, "build", `stills-${lang}.html`);
    fs.writeFileSync(src, html);
    for (const scale of [2, 1]) {
      const page = await chrome.newPage();
      await page.setViewport({ width: 1400, height: 900, deviceScaleFactor: scale });
      await page.goto("file://" + src, { waitUntil: "networkidle0" });
      await page.evaluate(async () => { await document.fonts.ready; await Promise.all([...document.images].map((i) => i.decode())); });
      const fonts = await page.evaluate(() => ["600 40px Fraunces", "italic 400 40px Fraunces", "400 30px 'Source Sans 3'", "500 20px 'Source Code Pro'"].map((f) => document.fonts.check(f)));
      if (fonts.includes(false)) throw new Error("fonts not loaded (network?): " + fonts);
      // nothing may run out of its box
      const over = await page.evaluate(() => [...document.querySelectorAll(".shot")].flatMap((s) => {
        const sr = s.getBoundingClientRect();
        return [...s.querySelectorAll(".box, .banner > *")].filter((e) => {
          const r = e.getBoundingClientRect();
          return (e.classList.contains("box") && e.scrollHeight > e.clientHeight + 1) || r.right > sr.right + 1 || r.bottom > sr.bottom + 1;
        }).map((e) => s.dataset.out + ": " + (e.className || e.tagName) + " " + (e.textContent || "").trim().slice(0, 40));
      }));
      if (scale === 2) for (const o of over) console.log("  !! overflow in " + lang + " " + o);
      for (const el of await page.$$(`.shot[data-scale="${scale}"]`)) {
        const name = await el.evaluate((e) => e.dataset.out);
        await el.screenshot({ path: path.join(out, name + ".png") });
        // where the crop sits inside the framed image, in device pixels (build.sh checks it is untouched)
        const r = await el.evaluate((e) => {
          const i = e.querySelector(".crop img"); if (!i) return null;
          const a = e.getBoundingClientRect(), b = i.getBoundingClientRect();
          return [b.left - a.left, b.top - a.top, b.width, b.height];
        });
        if (r) rects.push([lang, name, ...r.map((v) => Math.round(v * scale))].join(" "));
      }
      await page.close();
    }
  }
  fs.writeFileSync(path.join(HERE, "build", "crop-rects.txt"), rects.join("\n") + "\n");
  // close() has been seen to hang with headless Chrome; do not wait for it forever
  await Promise.race([chrome.close(), new Promise((r) => setTimeout(r, 5000))]);
  process.exit(0);
})().catch((e) => { console.error(e); process.exit(1); });
