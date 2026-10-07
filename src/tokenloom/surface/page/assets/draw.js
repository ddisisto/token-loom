/* What a continuation is asked for, and the panel that sets it.
 *
 * These are llama.cpp's parameters, and the page holds them because nothing else can: a
 * control needs a name, a range and a meaning, and none of the three is derivable from a
 * parameter an adapter merely accepts. So the dependency is named here and kept to this
 * file, which is what a second adapter replaces rather than amends.
 *
 * Two things the contract decides for the panel rather than leaving to taste:
 *
 * - **A sampler is off, or it is in the chain.** The chain holds what a request named, so a
 *   sampler at the end of its line where it would do nothing is left out of the request,
 *   rather than named at a value that does nothing. `temperature` is always named, because a
 *   chain without it draws at 1.0.
 * - **The panel cannot hold a state the adapter would refuse.** The gesture that generates
 *   is a scroll, so there is no submit to disable and no moment to object in; and a refusal
 *   is recorded, so an invalid pair does not fail harmlessly, it writes an act. Hence
 *   `record_rows` and `top_k` move each other rather than disagreeing.
 *
 * Nothing here is remembered between loads. What each act was asked for is in the record.
 */

/** The ceiling `record_rows` and `top_k` share, because one has to cover the other and a
 *  row count is paid at every position of every draw. */
const COVER = 50;

/** How much of a line its idle end takes. */
export const IDLE = 0.06;

/** Every parameter the panel sets, in the order it shows them.
 *
 *  `scale` is how a position along a line becomes a value: `line` evenly on `step`, `log`
 *  evenly in ratio, so the low end is fine-grained, and `tail` evenly in ratio of what is left
 *  below 1, so 0.9, 0.95 and 0.99 each have room. `idle` is the end where the parameter does
 *  nothing, which takes the last `IDLE` of the line: an optional one is left out of the request
 *  there, and a required one is sent `rests`. `edge` is set somewhere other than the panel.
 */
const FIELDS = [
  { key: "length", group: "the draw", scale: "line", min: 8, max: 400, step: 8, value: 64,
    edge: true },

  { key: "temperature", group: "the chain", scale: "line", min: 0, max: 2.5, step: 0.05,
    value: 0, edge: true },
  { key: "top_k", group: "the chain", scale: "log", int: true, min: 1, max: COVER, value: 10,
    idle: "high", on: false },
  { key: "top_p", group: "the chain", scale: "tail", min: 0.1, max: 0.995, value: 0.95,
    idle: "high", on: false },
  { key: "min_p", group: "the chain", scale: "log", min: 0.005, max: 0.5, value: 0.02,
    idle: "low" },

  { key: "record_rows", group: "the record", scale: "log", int: true, min: 2, max: COVER,
    value: 10 },
  { key: "record_mass", group: "the record", scale: "tail", min: 0.1, max: 0.995, value: 0.9,
    idle: "high", rests: 1 },

  { key: "cache_prompt", group: "the backend", kind: "flag", value: true },
];

/* `seed` is not here, and its absence is the design's and not an omission. A surface is
 * where a question worth asking under control might be found and not where it is answered,
 * so an act that has to be replayed is one the command line makes. `docs/SURFACE.md` states
 * it, along with what it costs. */

const state = new Map(FIELDS.map(f => [f.key, { value: f.value, on: f.on ?? true }]));
const field = key => {
  const found = FIELDS.find(f => f.key === key);
  if (found === undefined) throw new RangeError(`no parameter ${key}`);
  return found;
};

/** What a parameter sends: its value, what it rests at, or nothing. */
function sent(f) {
  const held = state.get(f.key);
  if (f.kind === "flag" || held.on) return held.value;
  return f.rests;
}

/** What a `generate` is asked for. A parameter that is off is absent, not zero. */
export function draw() {
  const params = {};
  for (const f of FIELDS) {
    const value = sent(f);
    if (value !== undefined) params[f.key] = value;
  }
  return params;
}

/** What a draw keeps, with nothing of what it draws.
 *
 *  **It is the panel cut along the line `docs/NEXT.md` already draws through it**: what is
 *  drawn is `length` and the chain, what is kept is the record's depth and mass, and
 *  then the backend. A caller that decides the first pair for itself still owes the record
 *  the second, and a rollout is that caller -- it fixes its length and its heat, and takes
 *  how deep to record from wherever the reader set it.
 *
 *  The chain goes with the draw and not with the record. A rollout naming no sampler is
 *  greedy in the act's own `params` rather than greedy by argument, which is what lets *a
 *  stub is any node no act but a greedy one produced* be read off the record later.
 */
export function keep() {
  const params = {};
  for (const f of FIELDS) {
    if (f.group === "the draw" || f.group === "the chain") continue;
    const value = sent(f);
    if (value !== undefined) params[f.key] = value;
  }
  return params;
}

// ---- along a line ---------------------------------------------------------------------------

/** Rounded to what a reader can tell apart: a step, a whole number, or two figures of what
 *  the scale spreads out -- the value on a log, and what is left below 1 on a tail. */
function round(f, v) {
  if (f.scale === "line") {
    // Past the step's own precision, so 0.05 times seven is 0.35 and not 0.35000000000000003.
    return Number((f.min + Math.round((v - f.min) / f.step) * f.step).toFixed(6));
  }
  if (f.int) return Math.round(v);
  if (f.scale === "tail") return Number((1 - Number((1 - v).toPrecision(2))).toFixed(6));
  return Number(v.toPrecision(2));
}

/** The value at `u` along the live part of a line, from 0 to 1. */
function at(f, u) {
  const t = Math.min(1, Math.max(0, u));
  if (f.scale === "log") return round(f, f.min * (f.max / f.min) ** t);
  if (f.scale === "tail") return round(f, 1 - (1 - f.min) * ((1 - f.max) / (1 - f.min)) ** t);
  return round(f, f.min + t * (f.max - f.min));
}

/** Where along the live part of a line `v` stands, from 0 to 1. */
function where(f, v) {
  if (f.scale === "log") return Math.log(v / f.min) / Math.log(f.max / f.min);
  if (f.scale === "tail") return Math.log((1 - v) / (1 - f.min)) / Math.log((1 - f.max) / (1 - f.min));
  return (v - f.min) / (f.max - f.min);
}

/** The value `s` of the way along a parameter's line, or null at its idle end. A line that is
 *  not the panel's own takes its range from here, so the two cannot disagree about it. */
export function along(key, s) {
  const f = field(key);
  const x = Math.min(1, Math.max(0, s));
  if (f.idle === "low") return x < IDLE ? null : at(f, (x - IDLE) / (1 - IDLE));
  if (f.idle === "high") return x > 1 - IDLE ? null : at(f, x / (1 - IDLE));
  return at(f, x);
}

/** How far along its line a parameter stands, from 0 to 1, with an idle one at its end. */
export function share(key) {
  const f = field(key);
  const held = state.get(key);
  if (!held.on) return f.idle === "low" ? 0 : 1;
  const u = Math.min(1, Math.max(0, where(f, held.value)));
  if (f.idle === "low") return IDLE + u * (1 - IDLE);
  if (f.idle === "high") return u * (1 - IDLE);
  return u;
}

/** Set a parameter from a position along its line. */
export function place(key, s) {
  const value = along(key, s);
  const held = state.get(key);
  held.on = value !== null;
  if (value !== null) held.value = value;
  cover(key);
  settle();
}

/** Set a parameter to a value, within its range. */
export function set(key, value) {
  const f = field(key);
  const held = state.get(key);
  held.value = Math.min(f.max, Math.max(f.min, value));
  held.on = true;
  cover(key);
  settle();
}

/** What a parameter reads as: its value, or what its idle end means. */
export function said(key) {
  const f = field(key);
  const held = state.get(key);
  if (f.kind === "flag") return held.value ? "on" : "off";
  if (!held.on) return f.rests === undefined ? "off" : "all";
  return String(held.value);
}

/* `record_rows` must cover a `top_k` the request names, so one of the two gives way. The
 * value just moved is the one that was meant, and the other follows it -- both are on
 * screen, so neither moves out of sight. */
function cover(meant) {
  const wide = state.get("top_k"), rows = state.get("record_rows");
  if (!wide.on || rows.value >= wide.value) return;
  if (meant === "top_k") rows.value = wide.value;
  else wide.value = rows.value;
}

// ---- the panel --------------------------------------------------------------------------

const el = (tag, className, text) =>
  Object.assign(document.createElement(tag), { className, textContent: text ?? "" });

/** Called after any change, because a change to one control can move another. */
const sync = [];
const settle = () => { for (const again of sync) again(); };

/** One parameter as a line with a point on it, the same as the page's two rules. Where the
 *  pointer is along the line is read here and nowhere else, and `along` says what it means. */
function row(f) {
  const box = el("div", "row");
  const name = el("span", "name", f.key);
  const read = el("span", "val");

  if (f.kind === "flag") {
    // A flag has a value and no line to put it on, so the row is the control.
    box.classList.add("flag");
    box.onclick = () => { state.get(f.key).value = !state.get(f.key).value; settle(); };
    box.append(name, el("span", "line"), read);
    sync.push(() => {
      read.textContent = said(f.key);
      box.classList.toggle("off", !state.get(f.key).value);
    });
    return box;
  }

  const line = el("span", "line");
  line.append(el("span", "point"));
  let held = false;
  const toward = event => {
    const box = line.getBoundingClientRect();
    place(f.key, (event.clientX - box.left) / box.width);
  };
  line.onpointerdown = event => {
    if (event.button !== 0) return;
    event.preventDefault();
    line.setPointerCapture(event.pointerId);
    held = true;
    line.classList.add("moving");
    toward(event);
  };
  line.onpointermove = event => { if (held) toward(event); };
  line.onpointerup = line.onpointercancel = () => { held = false; line.classList.remove("moving"); };
  box.append(name, line, read);

  sync.push(() => {
    line.style.setProperty("--x", String(share(f.key)));
    box.classList.toggle("off", !state.get(f.key).on);
    read.textContent = said(f.key);
  });
  return box;
}

/** The panel, ready to be put somewhere: one column per group, and nothing set elsewhere. */
export function panel() {
  const out = el("div", "panel");
  let named = null, group = null;
  for (const f of FIELDS) {
    if (f.edge) continue;
    if (f.group !== named) {
      named = f.group;
      group = el("div", "group");
      group.append(el("div", "head", f.group));
      out.append(group);
    }
    group.append(row(f));
  }
  settle();
  return out;
}
