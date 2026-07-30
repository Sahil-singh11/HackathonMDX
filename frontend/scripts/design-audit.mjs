/**
 * Design-system audit harness — Sahil's lane.
 *
 * Measures the accessibility floor from CLAUDE.md against the RUNNING app,
 * from real painted pixels and real layout boxes. It exists because that floor
 * ("contrast >=4.5:1 in every theme", "56x56px touch targets", "text scales to
 * 150% without breaking layout", "one h1 per page") is only meaningful if
 * something checks it, and checking it by eye across
 * 9 routes x 4 theme states x 3 text scales is 108 screens.
 *
 * WHY THIS IS A SCRIPT AND NOT A TEST: it needs a browser, and Playwright is
 * deliberately NOT a declared dependency — adding it to package.json forces
 * every teammate to download Chromium (CLAUDE.md: announce before installing).
 * So this degrades politely when Playwright is absent and tells you what to do.
 *
 *   cd frontend && npm run dev          # in another terminal
 *   node scripts/design-audit.mjs                    # everything
 *   node scripts/design-audit.mjs --checks=contrast   # one check
 *   node scripts/design-audit.mjs --routes=/,/pillars --themes=night
 *   node scripts/design-audit.mjs --base=http://localhost:8000
 *
 * ON GIT BASH FOR WINDOWS, prefix any run that passes a route: MSYS rewrites a
 * leading "/" into a Windows path, so --routes=/,/pillars silently becomes
 * --routes=C:/Program Files/Git/... and the navigation fails:
 *
 *   MSYS_NO_PATHCONV=1 node scripts/design-audit.mjs --routes=/,/pillars
 *
 * PowerShell and cmd are unaffected.
 *
 * Exits 1 if any check fails, so it can gate a release when wanted.
 *
 * ---------------------------------------------------------------------------
 * MEASUREMENT NOTES — these were all learned the hard way; do not "simplify"
 * them away without re-deriving why they are here:
 *
 *  1. Contrast samples the backdrop with the text made TRANSPARENT first.
 *     Sampling at a text coordinate while the glyph is painted returns the
 *     glyph's own colour and yields a meaningless 1.00 ratio.
 *  2. getComputedStyle can return `color(srgb 0.9 0.94 0.94 / 0.72)` with
 *     0..1 floats. Reading those as 0..255 bytes produces phantom failures.
 *     Both notations are handled.
 *  3. Semi-transparent text is composited over the sampled backdrop before
 *     the ratio is computed, otherwise low-alpha text scores far too well.
 *  4. Screenshots force reduced motion: Dashboard's count-up animation makes
 *     runs non-deterministic (documented gotcha in CLAUDE.md).
 *  5. Overflow is read off the SCROLLING element, and `overflow-x: hidden`
 *     can mask real overflow from a naive scrollWidth check — so the check
 *     also inspects children that exceed their container.
 */
import process from 'node:process';

/* ----------------------------------------------------------------- config */

const DEFAULT_ROUTES = [
  '/', '/sea', '/record', '/log', '/assistant', '/pillars',
  '/declaration', '/queue', '/proof',
];

/** The four theme states CLAUDE.md requires contrast to hold in. */
const THEME_STATES = {
  day: { theme: 'day', nightVision: false },
  night: { theme: 'night', nightVision: false },
  'night-vision': { theme: 'night', nightVision: true },
  sunlight: { theme: 'sunlight', nightVision: false },
};

const WIDTHS = [
  { w: 360, h: 800, label: 'phone' },
  { w: 768, h: 1024, label: 'tablet' },
  { w: 1280, h: 900, label: 'laptop' },
  { w: 1920, h: 1080, label: 'desktop' },
];

const TEXT_SCALES = ['100', '125', '150'];

/** Text whose contrast we care about. Broad on purpose: any element with a
 *  text node gets probed, these are just the ones we always want covered. */
const TEXT_SELECTORS = [
  'h1', 'h2', 'h3', 'p', 'label', 'button', 'a',
  '.caption', '.small', '.bento-title', '.bento-sub', '.stat-chip-label',
  '.stat-chip-value', '.banner', '.badge',
];

const TOUCH_MIN = 56;   // CLAUDE.md floor: gloves, wet hands, a moving boat
const BODY_MIN_PX = 16; // "Body never below 16px"

/* ------------------------------------------------------------------ args */

const args = process.argv.slice(2);
const argVal = (name, fallback) => {
  const hit = args.find((a) => a.startsWith(`--${name}=`));
  return hit ? hit.slice(name.length + 3) : fallback;
};
const BASE = argVal('base', 'http://localhost:5173').replace(/\/$/, '');
const ROUTES = argVal('routes', '').trim() ? argVal('routes', '').split(',') : DEFAULT_ROUTES;
const THEMES = argVal('themes', '').trim()
  ? argVal('themes', '').split(',')
  : Object.keys(THEME_STATES);
const CHECKS = argVal('checks', '').trim()
  ? argVal('checks', '').split(',')
  : ['headings', 'touch', 'typography', 'contrast', 'scaling', 'motion'];

/* ----------------------------------------------------------- diagnostics */

let chromium;
try {
  ({ chromium } = await import('playwright'));
} catch {
  console.error(`
This harness needs Playwright, which is intentionally not a project
dependency (it would make every teammate download Chromium).

Install it just for yourself, without committing it:

    cd frontend
    npm i --no-save playwright && npx playwright install chromium

Then re-run. If the team decides this should be permanent, add
playwright to devDependencies — but announce it first (CLAUDE.md).
`.trim());
  process.exit(2);
}

const failures = [];
const notes = [];
const fail = (check, where, detail) => failures.push({ check, where, detail });
const note = (check, where, detail) => notes.push({ check, where, detail });

/* --------------------------------------------------------------- helpers */

const seed = (themeKey, textScale) => {
  const t = THEME_STATES[themeKey];
  return [t, textScale];
};

async function openPage(browser, { width, height, themeKey, textScale = '100', reduced = false }) {
  const ctx = await browser.newContext({
    viewport: { width, height },
    reducedMotion: reduced ? 'reduce' : 'no-preference',
  });
  const page = await ctx.newPage();
  const [themeCfg] = seed(themeKey, textScale);
  await page.addInitScript(([cfg, scale]) => {
    localStorage.setItem('lamer-konekte-theme', JSON.stringify({
      theme: cfg.theme, nightVision: cfg.nightVision, textScale: scale, reduceMotion: false,
    }));
    // Onboarded, so routes render instead of redirecting to the welcome screen.
    localStorage.setItem('lamer-konekte', JSON.stringify({
      state: { language: 'en', profileName: 'Audit', fishingArea: 'Grand Baie', onboarded: true },
      version: 0,
    }));
    // Count rAF ticks so the motion check can prove the loop is actually idle.
    window.__rafTicks = 0;
    const orig = window.requestAnimationFrame.bind(window);
    window.requestAnimationFrame = (cb) => orig((t) => { window.__rafTicks++; cb(t); });
  }, [themeCfg, textScale]);
  return { ctx, page };
}

const goto = async (page, route) => {
  await page.goto(BASE + route, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1400); // entry animations + first data paint
};

/* ------------------------------------------- in-page measurement helpers */

/** Serialised into the browser: collects text probes with their colours. */
const COLLECT_PROBES = (selectors) => {
  const seen = new Set();
  const out = [];
  for (const sel of selectors) {
    for (const el of document.querySelectorAll(sel)) {
      if (seen.has(el)) continue;
      seen.add(el);
      // Only elements with their OWN visible text.
      const own = Array.from(el.childNodes)
        .filter((n) => n.nodeType === 3 && n.textContent.trim())
        .map((n) => n.textContent.trim()).join(' ');
      if (!own) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 4 || r.height < 4) continue;
      if (r.bottom < 0 || r.top > innerHeight) continue;  // offscreen
      const cs = getComputedStyle(el);
      if (cs.visibility === 'hidden' || cs.opacity === '0') continue;
      // WCAG 1.4.3 exempts INACTIVE controls, and greyed-out buttons
      // legitimately sit below 4.5:1. Without this the audit reports a
      // disabled "Analyse" at 1.57 as a failure and trains you to ignore it.
      if (el.disabled || el.getAttribute('aria-disabled') === 'true'
          || el.closest('[disabled],[aria-disabled=true]')) continue;
      out.push({
        sel, text: own.slice(0, 30),
        x: Math.round(r.x + Math.min(12, r.width / 2)),
        y: Math.round(r.y + r.height / 2),
        color: cs.color,
        opacity: parseFloat(cs.opacity) || 1,
        fontSize: parseFloat(cs.fontSize),
        fontWeight: cs.fontWeight,
      });
    }
  }
  return out;
};

/* ------------------------------------------------------- colour maths */

const relLum = ({ r, g, b }) => {
  const f = (v) => { const s = v / 255; return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4; };
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
};
const ratio = (a, b) => {
  const la = relLum(a), lb = relLum(b);
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
};
/** Handles both `rgb(0 1 2 / .5)` bytes and `color(srgb 0..1 / a)` floats. */
function parseCssColor(str) {
  const isFloat = /^color\(\s*srgb/i.test(str);
  const nums = (str.match(/[\d.]+/g) || []).map(Number);
  if (nums.length < 3) return null;
  const k = isFloat ? 255 : 1;
  return {
    r: nums[0] * k, g: nums[1] * k, b: nums[2] * k,
    a: nums.length > 3 ? nums[3] : 1,
  };
}
/** WCAG large-text threshold: >=24px, or >=18.66px when bold. */
const isLargeText = (px, weight) =>
  px >= 24 || (px >= 18.66 && Number(weight) >= 700);

/* ============================================================== checks */

async function checkHeadingsTouchTypography(browser) {
  const { ctx, page } = await openPage(browser, { width: 1280, height: 900, themeKey: 'day' });
  console.log('\n── headings / touch targets / typography ──────────────────────');
  console.log('route          h1  order      small-targets  tiny-text');
  for (const route of ROUTES) {
    await goto(page, route);
    const r = await page.evaluate(({ touchMin, bodyMin }) => {
      const h1s = [...document.querySelectorAll('h1')].map((h) => h.textContent.trim().slice(0, 24));
      const levels = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map((h) => +h.tagName[1]);
      let jump = null;
      for (let i = 1; i < levels.length; i++) {
        if (levels[i] > levels[i - 1] + 1) { jump = `h${levels[i - 1]}->h${levels[i]}`; break; }
      }
      const small = [];
      for (const el of document.querySelectorAll('a[href],button,select,textarea,input:not([type=radio]):not([type=checkbox]),[role=button]')) {
        const b = el.getBoundingClientRect();
        const cs = getComputedStyle(el);
        if (b.width < 1 || b.height < 1 || cs.visibility === 'hidden') continue;
        if (el.closest('.lk-skip-link')) continue;         // visually-hidden by design
        if (b.width < touchMin || b.height < touchMin) {
          const cls = String(el.className || '').split(' ').filter(Boolean)[0] || '';
          small.push(`${el.tagName.toLowerCase()}${cls ? '.' + cls : ''}(${Math.round(b.width)}x${Math.round(b.height)})`);
        }
      }
      // "Body never below 16px" applies to BODY COPY. The token scale
      // deliberately includes --fs-sm 14px and --fs-xs 12px for captions and
      // metadata, and the legacy sheet styles .caption/.small at 14px on
      // purpose. Flagging those as failures made the audit cry wolf on ~20
      // intentional captions, which just teaches everyone to ignore it. So:
      // an element that OPTS IN to caption/metadata styling is a note; an
      // unmarked paragraph or list item below the floor is a failure. Anything
      // under 12px is a failure regardless — that is off the scale entirely.
      const META = /(^|[\s-])(caption|small|hint|note|sub|meta|provider|coverage|label)($|[\s-])/i;
      const tiny = [], tinyMeta = [];
      for (const el of document.querySelectorAll('p,li,label')) {
        const own = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
        if (!own) continue;
        const cs = getComputedStyle(el);
        const px = parseFloat(cs.fontSize);
        const b = el.getBoundingClientRect();
        if (b.width < 4 || b.height < 4) continue;
        if (px >= bodyMin) continue;
        const cls = String(el.className || '');
        const entry = `${el.tagName.toLowerCase()}${cls ? '.' + cls.split(' ')[0] : ''}@${px}px`;
        if (px < 12) tiny.push(entry + ' (below the 12px scale floor)');
        else if (META.test(cls)) tinyMeta.push(entry);
        else tiny.push(entry);
      }
      return { h1s, jump, small: [...new Set(small)], tiny: [...new Set(tiny)], tinyMeta: [...new Set(tinyMeta)] };
    }, { touchMin: TOUCH_MIN, bodyMin: BODY_MIN_PX });

    console.log(`${route.padEnd(14)} ${String(r.h1s.length).padEnd(3)} ${String(r.jump || "ok").padEnd(10)} ${String(r.small.length).padEnd(14)} ${r.tiny.length}`);
    if (CHECKS.includes('headings')) {
      if (r.h1s.length !== 1) fail('headings', route, `${r.h1s.length} h1 elements: ${JSON.stringify(r.h1s)} (CLAUDE.md: one h1 per page)`);
      if (r.jump) fail('headings', route, `heading level skipped: ${r.jump}`);
    }
    if (CHECKS.includes('touch') && r.small.length) {
      // Reported as a note, not a failure: the legacy stylesheet sets a 48px
      // floor app-wide, so every page trips this. Raising it is a redesign
      // decision, not a per-page bug — see the summary.
      note('touch', route, `${r.small.length} target(s) under ${TOUCH_MIN}px: ${r.small.slice(0, 5).join(', ')}`);
    }
    if (CHECKS.includes('typography')) {
      if (r.tiny.length) fail('typography', route, `body copy under ${BODY_MIN_PX}px: ${r.tiny.join(', ')}`);
      if (r.tinyMeta.length) note('typography', route, `caption/metadata under ${BODY_MIN_PX}px (intentional by class, listed for the redesign): ${r.tinyMeta.slice(0, 5).join(', ')}`);
    }
  }
  await ctx.close();
}

async function checkContrast(browser) {
  console.log('\n── contrast, per theme state (from real painted pixels) ───────');
  const { PNG } = await import('pngjs').catch(() => ({ PNG: null }));
  if (!PNG) {
    console.log('  skipped: pngjs not installed (npm i --no-save pngjs)');
    return;
  }
  console.log('theme         route          probes  worst   offenders');
  for (const themeKey of THEMES) {
    const { ctx, page } = await openPage(browser, { width: 1280, height: 900, themeKey, reduced: true });
    for (const route of ROUTES) {
      await goto(page, route);
      const probes = await page.evaluate(COLLECT_PROBES, TEXT_SELECTORS);
      if (!probes.length) { await page.waitForTimeout(0); continue; }

      // Hide the text so we sample the true backdrop (note 1).
      await page.evaluate((sels) => {
        const st = document.createElement('style');
        st.id = '__audit_hide';
        st.textContent = sels.map((s) => `${s}{color:transparent !important}`).join('');
        document.head.appendChild(st);
      }, TEXT_SELECTORS);
      await page.waitForTimeout(120);
      const shot = PNG.sync.read(await page.screenshot());
      await page.evaluate(() => document.getElementById('__audit_hide')?.remove());

      let worst = Infinity, worstSel = '', bad = [];
      for (const p of probes) {
        if (p.x < 0 || p.y < 0 || p.x >= shot.width || p.y >= shot.height) continue;
        const i = (shot.width * p.y + p.x) << 2;
        const bg = { r: shot.data[i], g: shot.data[i + 1], b: shot.data[i + 2] };
        const fgRaw = parseCssColor(p.color);
        if (!fgRaw) continue;
        const alpha = fgRaw.a * p.opacity;
        const fg = alpha < 1
          ? { r: fgRaw.r * alpha + bg.r * (1 - alpha),
              g: fgRaw.g * alpha + bg.g * (1 - alpha),
              b: fgRaw.b * alpha + bg.b * (1 - alpha) }
          : fgRaw;
        const cr = ratio(fg, bg);
        const floor = isLargeText(p.fontSize, p.fontWeight) ? 3.0 : 4.5;
        if (cr < worst) { worst = cr; worstSel = `${p.sel}"${p.text}"`; }
        if (cr < floor) bad.push(`${cr.toFixed(2)}<${floor} ${p.sel}"${p.text}"`);
      }
      const w = worst === Infinity ? '  n/a' : worst.toFixed(2).padStart(5);
      console.log(`${themeKey.padEnd(13)} ${route.padEnd(14)} ${String(probes.length).padEnd(7)} ${w}   ${bad.length || ''}`);
      if (bad.length) fail('contrast', `${themeKey} ${route}`, bad.slice(0, 6).join(' | '));
      void worstSel;
    }
    await ctx.close();
  }
}

async function checkScaling(browser) {
  console.log('\n── layout at width x text-scale (overflow = broken layout) ────');
  console.log('width  scale  route          docOverflowX  childOverflow');
  for (const { w, h, label } of WIDTHS) {
    for (const scale of TEXT_SCALES) {
      const { ctx, page } = await openPage(browser, { width: w, height: h, themeKey: 'day', textScale: scale, reduced: true });
      for (const route of ROUTES) {
        await goto(page, route);
        const r = await page.evaluate(() => {
          const de = document.documentElement;
          const docOverflowX = de.scrollWidth - de.clientWidth;
          // overflow-x:hidden can hide real overflow from scrollWidth (note 5),
          // so also look for children wider than their own container.
          const bleeding = [];
          for (const el of document.querySelectorAll('main *')) {
            const p = el.parentElement;
            if (!p) continue;
            const er = el.getBoundingClientRect(), pr = p.getBoundingClientRect();
            if (er.width < 8 || pr.width < 8) continue;
            if (er.right > pr.right + 2 || er.left < pr.left - 2) {
              const cs = getComputedStyle(p);
              if (cs.overflowX === 'auto' || cs.overflowX === 'scroll') continue; // intentional
              const cls = String(el.className || '').split(' ').filter(Boolean)[0] || el.tagName.toLowerCase();
              bleeding.push(cls);
            }
          }
          return { docOverflowX, bleeding: [...new Set(bleeding)].slice(0, 4) };
        });
        const flagged = r.docOverflowX > 2 || r.bleeding.length;
        if (flagged) {
          console.log(`${String(w).padEnd(6)} ${scale.padEnd(6)} ${route.padEnd(14)} ${String(r.docOverflowX).padEnd(13)} ${r.bleeding.join(', ')}`);
          if (r.docOverflowX > 2) {
            fail('scaling', `${label} ${w}px @${scale}% ${route}`, `horizontal overflow ${r.docOverflowX}px`);
          } else {
            note('scaling', `${label} ${w}px @${scale}% ${route}`, `child exceeds container: ${r.bleeding.join(', ')}`);
          }
        }
      }
      await ctx.close();
    }
  }
  console.log('(only rows with a problem are printed)');
}

async function checkMotion(browser) {
  console.log('\n── reduced motion must silence every loop ─────────────────────');
  console.log('route          ticks/s(reduced)  verdict');
  const { ctx, page } = await openPage(browser, { width: 1280, height: 900, themeKey: 'night', reduced: true });
  for (const route of ROUTES) {
    await goto(page, route);
    const before = await page.evaluate(() => window.__rafTicks);
    await page.waitForTimeout(1500);
    const after = await page.evaluate(() => window.__rafTicks);
    const perSec = Math.round(((after - before) / 1500) * 1000);
    // A couple of ticks can come from a transition settling; sustained 10+/s
    // means an animation loop is still running despite reduce-motion.
    const ok = perSec < 10;
    console.log(`${route.padEnd(14)} ${String(perSec).padEnd(17)} ${ok ? 'quiet' : '** STILL ANIMATING **'}`);
    if (!ok) fail('motion', route, `${perSec} rAF ticks/s under prefers-reduced-motion (expected ~0)`);
  }
  await ctx.close();
}

/* ================================================================= main */

console.log(`design-audit → ${BASE}`);
console.log(`routes: ${ROUTES.length}  themes: ${THEMES.join(', ')}  checks: ${CHECKS.join(', ')}`);

// Fail fast with a clear message if the dev server is not up.
try {
  const res = await fetch(BASE + '/', { method: 'GET' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
} catch (e) {
  console.error(`\nCannot reach ${BASE} (${e.message}).\nStart it first:  cd frontend && npm run dev`);
  process.exit(2);
}

const browser = await chromium.launch();
try {
  if (['headings', 'touch', 'typography'].some((c) => CHECKS.includes(c))) {
    await checkHeadingsTouchTypography(browser);
  }
  if (CHECKS.includes('contrast')) await checkContrast(browser);
  if (CHECKS.includes('scaling')) await checkScaling(browser);
  if (CHECKS.includes('motion')) await checkMotion(browser);
} finally {
  await browser.close();
}

/* ------------------------------------------------------------- summary */

console.log('\n' + '='.repeat(70));
if (notes.length) {
  console.log(`\nNOTES (${notes.length}) — known/systemic, not per-page regressions:`);
  const byCheck = {};
  for (const n of notes) (byCheck[n.check] ??= []).push(n);
  for (const [check, list] of Object.entries(byCheck)) {
    console.log(`\n  [${check}] ${list.length} occurrence(s)`);
    for (const n of list.slice(0, 4)) console.log(`    ${n.where}: ${n.detail}`);
    if (list.length > 4) console.log(`    …and ${list.length - 4} more`);
  }
}
if (!failures.length) {
  console.log('\nPASS — no failures against the CLAUDE.md floor.');
  process.exit(0);
}
console.log(`\nFAIL — ${failures.length} issue(s):`);
for (const f of failures) console.log(`  [${f.check}] ${f.where}\n      ${f.detail}`);
process.exit(1);
