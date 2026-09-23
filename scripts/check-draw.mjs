/* Drive the draw panel against a stub DOM.  `node scripts/check-draw.mjs`
 *
 * What it is here for is the pair `record_rows` and `top_k`, which must not be able to
 * disagree. Nothing on the page objects if they do: the gesture that generates is a scroll,
 * so an invalid pair is not caught on the way out, and the adapter's refusal is *recorded* --
 * which means the browser reports this bug by writing an act into the store. It found one
 * the first time it ran, in the direction a toggle moves.
 *
 * The stub is `stub-dom.mjs`, which the overlay's check drives too. It is not a test harness
 * for the page, and the reading column is not driven from here.
 */

import { El } from "./stub-dom.mjs";

const { draw, panel } = await import(
  new URL("../src/tokenloom/surface/page/assets/draw.js", import.meta.url));

const frag = panel();
const body = frag.children[1];
const rows = new Map();
for (const row of body.children) {
  if (!row.className.startsWith("row")) continue;
  const [top, control] = row.children;
  const name = top.children[0];
  const key = name.children.find(c => typeof c === "string");
  rows.set(key, {
    toggle: name.children.find(c => c instanceof El && c.type === "checkbox"),
    control,
  });
}

let bad = 0;
const is = (what, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) bad++;
  console.log(`${ok ? "ok  " : "FAIL"} ${what}: ${JSON.stringify(got)}` +
              (ok ? "" : ` != ${JSON.stringify(want)}`));
};

const check = (key, on) => { const t = rows.get(key).toggle; t.checked = on; t.onchange(); };
const move = (key, value) => { const c = rows.get(key).control; c.value = String(value); c.oninput(); };
const covered = () => !("top_k" in draw()) || draw().record_rows >= draw().top_k;

is("the defaults are the required five and nothing else", draw(),
   { length: 80, temperature: 0, record_rows: 10, record_mass: 0.9, cache_prompt: true });

check("top_k", true);
is("naming top_k at the rows already kept moves neither", [draw().top_k, draw().record_rows], [10, 10]);

move("top_k", 40);
is("a wider draw carries the record with it", [draw().top_k, draw().record_rows], [40, 40]);
is("  and the rows control shows what it was moved to", rows.get("record_rows").control.value, "40");

move("record_rows", 12);
is("keeping fewer rows narrows the draw to what they cover", [draw().top_k, draw().record_rows], [12, 12]);

move("top_k", 3);
is("a narrower draw leaves the record where it is", [draw().top_k, draw().record_rows], [3, 12]);

check("top_k", false);
is("a sampler left out is absent and not zero", "top_k" in draw(), false);
move("record_rows", 2);
is("  and an unnamed top_k constrains nothing", draw().record_rows, 2);

check("top_k", true);
is("naming it again lands inside what is kept", [draw().top_k, draw().record_rows], [2, 2]);

check("cache_prompt", false);
is("a required flag is sent false rather than dropped", draw().cache_prompt, false);

is("no reader asks for a seed, so no control offers one", rows.has("seed"), false);

move("temperature", 1.2);
is("temperature is real and not rounded", draw().temperature, 1.2);

// Every reachable pair, driven from both sides.
for (const k of [1, 5, 10, 25, 50]) {
  for (const r of [2, 10, 50]) {
    move("top_k", k); move("record_rows", r);
    if (!covered()) { bad++; console.log(`FAIL uncovered after top_k ${k} then rows ${r}`, draw()); }
    move("record_rows", r); move("top_k", k);
    if (!covered()) { bad++; console.log(`FAIL uncovered after rows ${r} then top_k ${k}`, draw()); }
  }
}
console.log(bad ? `\n${bad} failed` : "\nall covered, nothing failed");
process.exit(bad ? 1 : 0);
