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
 *   control has three states and not two, and one left unchecked is left out of the chain
 *   rather than applied at some default of the server's. `temperature` is the exception and
 *   is always named, because a chain without it draws at 1.0.
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

/** Every parameter the panel sets, in the order it shows them.
 *
 *  `off` marks the ones a request may leave out. The rest are the adapter's required set:
 *  what something other than the caller would otherwise decide.
 */
const FIELDS = [
  { key: "length", group: "the draw", kind: "int", min: 8, max: 400, step: 8, value: 80 },

  { key: "temperature", group: "the chain", kind: "real", min: 0, max: 2, step: 0.05, value: 0 },
  { key: "top_k", group: "the chain", kind: "int", min: 1, max: COVER, step: 1, value: 10, off: true },
  { key: "top_p", group: "the chain", kind: "real", min: 0.05, max: 1, step: 0.05, value: 0.95, off: true },
  { key: "min_p", group: "the chain", kind: "real", min: 0, max: 0.5, step: 0.01, value: 0.05, off: true },

  { key: "record_rows", group: "the record", kind: "int", min: 2, max: COVER, step: 1, value: 10 },
  { key: "record_mass", group: "the record", kind: "real", min: 0.1, max: 1, step: 0.05, value: 0.9 },

  { key: "cache_prompt", group: "the backend", kind: "flag", value: true },
];

/* `seed` is not here, and its absence is the design's and not an omission. A surface is
 * where a question worth asking under control might be found and not where it is answered,
 * so an act that has to be replayed is one the command line makes. `docs/SURFACE.md` states
 * it, along with what it costs. */

const state = new Map(FIELDS.map(f => [f.key, { value: f.value, on: !f.off }]));

/** What a `generate` is asked for. A parameter that is off is absent, not zero. */
export function draw() {
  const params = {};
  for (const field of FIELDS) {
    const held = state.get(field.key);
    if (held.on) params[field.key] = held.value;
  }
  return params;
}

/* `record_rows` must cover a `top_k` the request names, so one of the two gives way. The
 * value just moved is the one that was meant, and the other follows it -- both are on
 * screen, so neither moves out of sight.
 *
 * Naming `top_k` is not a move: the width it carries is left over from the last time it was
 * on, while the row count was chosen since. So a toggle passes the record as what was meant
 * and narrows the draw to fit, rather than growing the record to a number nobody picked.
 */
function cover(meant) {
  const wide = state.get("top_k"), rows = state.get("record_rows");
  if (!wide.on || rows.value >= wide.value) return;
  if (meant === "top_k") rows.value = wide.value;
  else wide.value = rows.value;
}

// ---- the panel --------------------------------------------------------------------------

const el = (tag, className, text) =>
  Object.assign(document.createElement(tag), { className, textContent: text ?? "" });

const shown = (field, value) => (field.kind === "real" ? value.toFixed(2) : String(value));

/** Called after any change, because a change to one control can move another. */
const sync = [];
const settle = () => { for (const again of sync) again(); };

function row(field) {
  const held = state.get(field.key);
  const box = el("div", field.off ? "row opt" : "row");
  const top = el("div", "top");
  const name = el("label", "name");
  const read = el("span", "val");

  if (field.off) {
    const on = Object.assign(document.createElement("input"), { type: "checkbox" });
    on.checked = held.on;
    on.onchange = () => { held.on = on.checked; cover("record_rows"); settle(); };
    name.append(on);
  }
  name.append(field.key);
  top.append(name, read);
  box.append(top);

  if (field.kind === "flag") {
    // The label's own box is the control: a flag has a value and no range to put it on.
    const on = Object.assign(document.createElement("input"), { type: "checkbox" });
    on.checked = held.value;
    on.onchange = () => { held.value = on.checked; settle(); };
    name.prepend(on);
    sync.push(() => { on.checked = held.value; read.textContent = held.value ? "on" : "off"; });
    return box;
  }

  const set = Object.assign(document.createElement("input"), {
    type: "range", min: field.min, max: field.max, step: field.step, value: String(held.value),
  });
  set.oninput = () => {
    const asked = field.kind === "real" ? Number(set.value) : Math.round(Number(set.value));
    if (Number.isFinite(asked)) held.value = Math.min(field.max, Math.max(field.min, asked));
    cover(field.key);
    settle();
  };
  box.append(set);

  sync.push(() => {
    box.classList.toggle("off", !held.on);
    set.disabled = !held.on;
    // Only written back when it disagrees, so a number being typed into is not reformatted
    // under the cursor and a range the other control moved still follows.
    if (Number(set.value) !== held.value) set.value = String(held.value);
    read.textContent = held.on ? shown(field, held.value) : "—";
  });
  return box;
}

/** The whole panel, ready to be put somewhere. */
export function panel() {
  const out = new DocumentFragment();
  const head = el("button", "head");
  const summary = el("span", "sum");
  head.append(el("span", "name", "draw"), summary);

  const body = el("div", "body");
  let group = null;
  for (const field of FIELDS) {
    if (field.group !== group) body.append(el("div", "group", (group = field.group)));
    body.append(row(field));
  }

  sync.push(() => {
    const { length, temperature, record_rows } = draw();
    summary.textContent = `${length} tok · ${temperature.toFixed(2)}° · ${record_rows} rows`;
  });

  head.onclick = () => {
    const open = head.parentElement.classList.toggle("open");
    head.setAttribute("aria-expanded", String(open));
  };
  head.setAttribute("aria-expanded", "false");

  out.append(head, body);
  settle();
  return out;
}
