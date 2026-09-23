/* What is drawn along the path, and the panel that chooses it.
 *
 * `docs/SURFACE.md` has an overlay as three separable things, and they are separate here: a
 * MEASURE is a per-position quantity that may be absent, a SCALE maps it into [0,1], and the
 * UNIT is what a value is addressed to. Keeping them apart is what lets a quantity some later
 * analysis computes arrive through this same machinery and be read the same way.
 *
 * The unit here is the segment, because that is what the path read returns and what the
 * column can address -- one node to one segment is the common case and not the definition, so
 * a span holding more than one is marked rather than coloured.
 *
 * A measure declares two things a reader needs and cannot see:
 *
 * - `draw` is whether it reads the row the draw took. A *relative* measure is silent wherever
 *   the draw did not go -- at a token someone authored, or one another source produced. An
 *   *independent* one reads the ranking alone and has a value at both.
 * - `needs` is how much of a ranking it reads. A *top* measure reads the head and is honest at
 *   whatever depth was recorded; a *tail* one reads what accumulated, so one path can hold its
 *   values at several depths and the panel says which.
 *
 * - `looks` is which way it reads. An *up* measure reads the ranking a node stood in, which
 *   never changes again; a *down* one reads the tree below it, which changes with every act
 *   the reader makes. A down measure declares neither of the other two, because both are
 *   about a ranking and it reads none.
 *
 * The first two are the divisions `docs/SURFACE.md` states, and they cross: the gap is
 * draw-independent and robust, the flag is draw-relative and robust. The third cuts deeper
 * than either, and something follows from it that has nothing to do with drawing -- a measure
 * that looks down is a continuation rule, being the same scalar read as an argmax over
 * siblings. So the panel's path chips are this list read that way rather than a second list.
 */

/** Every measure the page can draw, in the order it offers them.
 *
 *  `reads` is the same quantity in two spaces, which is what *linear against log is a choice
 *  on the same measure* means -- not two measures. Each carries its own fixed domain, since
 *  the same position is a different number in each; a domain that descends says so by running
 *  from high to low, and the scale needs nothing else to know the polarity.
 */
/** The two readings every downward measure has, over a count of nodes.
 *
 *  The log one is of one plus the count, because a node with nothing below it parts nowhere
 *  and none is a count rather than a gap. Both are monotone, so the two agree on order and
 *  differ only in the middle -- which is the whole of it, and is what makes a subtree of
 *  thousands legible beside a corridor of a dozen.
 *
 *  Neither carries a fixed domain. Subtree size runs from one to the size of the tree and the
 *  tree grows, so a colour could not mean the same thing twice; `docs/SURFACE.md` has a depth
 *  limit as what supplies a ceiling, and until there is one these are path-relative and the
 *  panel says so.
 */
const counted = key => ({
  log: { unit: "ln nodes", dp: 2, domain: null, of: u => Math.log1p(u[key]) },
  linear: { unit: "nodes", dp: 0, domain: null, of: u => u[key] },
});

const MEASURES = [
  {
    key: "flag",
    looks: "up",
    what: "what the draw paid to go where the model would not have",
    draw: "relative",
    needs: "top",
    missing: a => `the row the draw took is not among the ${a.rows} recorded`,
    /* A draw the rows do not hold is censored and not missing. What was written is a prefix
     * of what the model ranked, so the token taken sits at or below the lowest row -- which
     * bounds the flag from one side. `bound` is that limit in the reading's own space, and
     * `word` is which side of the value it stands on, since inverting the space inverts it. */
    reads: {
      log: {
        unit: "nats", dp: 2, domain: [0, 5],
        of: (a, n) => a.top - n.logprob,
        bound: { word: "at least", of: a => a.top - a.least },
      },
      linear: {
        unit: "ratio", dp: 3, domain: [1, 0],
        of: (a, n) => Math.exp(n.logprob - a.top),
        bound: { word: "at most", of: a => Math.exp(a.least - a.top) },
      },
    },
  },
  {
    key: "gap",
    looks: "up",
    what: "how far the top token stands above the next, drawn where it barely does",
    draw: "independent",
    needs: "top",
    missing: a => `only ${a.rows} row recorded`,
    // A distribution measure marks where work was *available*, so a position the model had
    // nearly settled is the quiet one and a pair of rivals is the loud one. That is the
    // domain's business and not the quantity's: the value stays the gap the record holds.
    reads: {
      log: { unit: "nats", dp: 2, domain: [5, 0], of: a => (a.second === null ? null : a.top - a.second) },
      linear: { unit: "ratio", dp: 3, domain: [0, 1], of: a => (a.second === null ? null : Math.exp(a.second - a.top)) },
    },
  },
  {
    key: "mass",
    looks: "up",
    what: "how much probability the recorded rows hold between them",
    draw: "independent",
    needs: "tail",
    missing: () => "nothing recorded",
    reads: {
      log: { unit: "nats", dp: 3, domain: [0, 0.3], of: a => -Math.log(a.mass) },
      linear: { unit: "p", dp: 3, domain: [1, 0.5], of: a => a.mass },
    },
  },
  /* ---- what lies below ----
   *
   * These read no ranking, so neither of the other declarations arises. What they read is the
   * tree the reader has grown under a node rather than a model's opinion at it, which is a
   * different kind of fact drawn the same way: a reader carrying *dark is interesting* across
   * from the measures above has it wrong half the time, and the panel's own line is where
   * that is said.
   *
   * `under` is what the path read carries when it was asked for one -- every measure at once,
   * since one descent computes them all and a client choosing between them has the rest for
   * nothing.
   *
   * `rule` is the continuation rule the measure generates, under the name the server knows
   * it by. `longest` is older than the measure it turned out to be.
   *
   * Three of the four only fall as a path descends, so unbounded they draw as a gradient from
   * the root and say nothing but where the steps are. Over the 266-node path of
   * `data/continuations` the run to the next fork is the only one that rises, and it rises ten
   * times. `docs/SURFACE.md` has the depth limit as what makes the other three local.
   */
  {
    key: "height",
    rule: "longest",
    looks: "down",
    what: "how far the longest descent from here reaches",
    missing: () => "the descent did not reach this node",
    reads: counted("height"),
  },
  {
    key: "size",
    rule: "size",
    looks: "down",
    what: "how much has been grown at or below here",
    missing: () => "the descent did not reach this node",
    reads: counted("size"),
  },
  {
    key: "forks",
    rule: "forks",
    looks: "down",
    what: "how many places below here the tree parts",
    missing: () => "the descent did not reach this node",
    reads: counted("forks"),
  },
  {
    key: "run",
    rule: "run",
    looks: "down",
    what: "how far there is to go from here before a choice",
    missing: () => "the descent did not reach this node",
    reads: counted("run"),
  },
];

/** What is chosen. Nothing, until a reader asks: the column that opens draws no overlay, and
 *  a read that is not asked for one pays for none of it. */
let chosen = null;
let reading = "log";
let fixed = true;

/* Which continuation rule the read follows, by the server's name for it. It is held here
 * because it is chosen from the same list of scalars the measures are, and it moves
 * independently of them: reading a path laid out by one measure while another is drawn over
 * it is the case `docs/SURFACE.md` says a preset must not take away. */
let taken = "longest";

export const asked = () => chosen !== null;

export const rule = () => taken;

const pick = () => MEASURES.find(m => m.key === chosen) ?? null;

/** What a read has to ask for. A measure that looks up rides on the ranking overlay and one
 *  that looks down wants a second descent, which costs more than the path it decorates -- so
 *  neither is asked for until something is chosen that reads it. */
export const wants = () => {
  const m = pick();
  return { overlays: m?.looks === "up", beneath: m?.looks === "down" };
};

// ---- the measure, at one position -------------------------------------------------------

/* A position with no value is not a position with a low one, and the ways to arrive there are
 * told apart here and marked apart in the column -- because a reader who could not tell them
 * apart would read a gap in the record as a quiet position.
 *
 * One of them is not a no-value at all on a second look. A draw that fell past what was
 * recorded is *censored* rather than missing: the rows that were written bound it, so it
 * carries a value from one side and says so.
 */
function at(mark, m) {
  // A measure that looks down reads nothing a ranking holds, so none of the states below can
  // arise for one. What can is that the descent did not reach the node, which is a hole --
  // and not the same as nothing lying below it, since that is a value and it has one.
  if (m.looks === "down") {
    if (mark.under === undefined) return { mark, state: "none" };
    if (mark.under === null) return { mark, state: "hole" };
    const value = m.reads[reading].of(mark.under);
    if (!Number.isFinite(value)) return { mark, state: "hole" };
    return { mark, state: "value", value };
  }
  const among = mark.among;
  if (!among || !among.length) return { mark, state: "none" };
  // Two sources ranked this position and neither is the answer. Choosing one silently would
  // make the overlay mean different things along one path with nothing saying so.
  if (among.length > 1) return { mark, state: "clash" };
  const a = among[0];
  if (m.draw === "relative") {
    // Nothing this source drew stands here -- the token was authored, or another model put
    // it there. Off the scale rather than at its end, and not a gap in the record.
    if (a.source !== mark.source) return { mark, state: "off", among: a };
    // Drawn from this very ranking and absent from it, which is the recording ceiling
    // cutting the row off. The model had a number the record does not -- but the rows it
    // does hold say how low that number is, so this is a bound wherever the reading can
    // take one, and only a hole where it cannot.
    if (mark.logprob === null) {
      const edge = m.reads[reading].bound;
      const limit = edge ? edge.of(a, mark) : null;
      if (limit === null || !Number.isFinite(limit)) return { mark, state: "hole", among: a };
      return { mark, state: "bound", value: limit, among: a };
    }
  }
  const value = m.reads[reading].of(a, mark);
  if (value === null || !Number.isFinite(value)) return { mark, state: "hole", among: a };
  return { mark, state: "value", value, among: a };
}

// ---- the scale --------------------------------------------------------------------------

/* Fixed before relative: a fixed domain makes a colour mean the same thing in every path and
 * every tree, and a path-relative one makes a single path maximally legible and comparable to
 * nothing. The second is another scale and not another system, so it is the same two numbers.
 */
function domain(m, values) {
  // A reading with no fixed domain is path-relative whether or not the chip says so, because
  // there is no ceiling to place it against. That is not a gap to fill in: a count of what a
  // reader has grown has no domain until a depth limit gives it one.
  const fix = m.reads[reading].domain;
  if (fix && (fixed || !values.length)) return fix;
  if (!values.length) return [0, 1];
  let min = values[0], max = values[0];
  for (const v of values) { if (v < min) min = v; if (v > max) max = v; }
  return fix && fix[1] < fix[0] ? [max, min] : [min, max];
}

/** Whether what was drawn took its range from the path rather than from the measure. */
const relative = m => !(fixed && m.reads[reading].domain);

const place = ([lo, hi], v) =>
  hi === lo ? 0 : Math.min(1, Math.max(0, (v - lo) / (hi - lo)));

// ---- what a span gets ---------------------------------------------------------------------

const named = (sources, id) => sources?.[String(id)] ?? `source ${id}`;

/** What one node's state says, in words. The depth rides along wherever a measure needed a
 *  tail to compute, since two such values are only comparable at one depth. */
function tell(m, p, sources) {
  const deep = m.needs === "tail" && p.among ? ` over ${p.among.rows} rows` : "";
  switch (p.state) {
    case "value": {
      const r = m.reads[reading];
      return `${p.value.toFixed(r.dp)} ${r.unit}${deep}`;
    }
    case "bound": {
      const r = m.reads[reading];
      return `${r.bound.word} ${p.value.toFixed(r.dp)} ${r.unit}${deep}`
        + ` · the draw fell past the ${p.among.rows} rows recorded here`;
    }
    case "off":
      return `no draw to read: ${named(sources, p.mark.source)} put this token here`;
    case "hole":
      return `no value: ${m.missing(p.among)}`;
    case "clash":
      return "two sources ranked this position, and the surface does not choose between them";
    default:
      return "nothing ranked this position";
  }
}

/** One span's mark: a class, a place on the scale where there is one, and what it says. */
function paint(m, row, span, sources) {
  if (row.every(p => p.state === "none")) return null;
  if (row.length > 1) {
    return {
      cls: "split",
      title: `${m.key} · ${row.length} tokens spell this and no one value covers them · `
        + row.map(p => tell(m, p, sources)).join(" · "),
    };
  }
  const p = row[0];
  const title = `${m.key} · ${tell(m, p, sources)}`;
  if (p.state === "value") return { cls: "val", t: place(span, p.value), title };
  // A bound is placed like a value and marked unlike one: the colour says how far the draw
  // went at minimum, and the mark says the record stops there rather than agreeing.
  if (p.state === "bound") return { cls: "bound", t: place(span, p.value), title };
  return { cls: p.state, title };
}

/** Read the whole path at once: the marks, span by span, and a survey of what was found.
 *
 *  One pass, because a path-relative domain is not known until every value is. Returns null
 *  when nothing is chosen, which is the column that opens.
 */
export function read(segments, sources) {
  const m = pick();
  if (!m) return survey(null);
  const rows = segments.map(cell => cell.nodes.map(mark => at(mark, m)));

  // A bound places on the same scale as a value and is counted apart from one, because what
  // a reader may conclude from the two is not the same.
  const values = [];
  let bounded = 0;
  let deep = null;
  let total = 0;
  for (const row of rows) {
    for (const p of row) {
      total += 1;
      if (p.state !== "value" && p.state !== "bound") continue;
      if (p.state === "bound") bounded += 1;
      values.push(p.value);
      // Which depth a value came from is only ever asked of a measure that read a tail, and
      // a measure that looks down read no ranking to have a depth in.
      if (m.needs !== "tail") continue;
      const rank = p.among.rows;
      deep = deep === null ? [rank, rank] : [Math.min(deep[0], rank), Math.max(deep[1], rank)];
    }
  }
  const span = domain(m, values);
  survey(m, values, bounded, deep, total);
  return rows.map(row => paint(m, row, span, sources));
}

// ---- the panel ----------------------------------------------------------------------------

const el = (tag, className, text) =>
  Object.assign(document.createElement(tag), { className, textContent: text ?? "" });

const sync = [];
const settle = () => { for (const again of sync) again(); };

let note = null;

/** What the path held, once it was read. The count is how much of the path the measure
 *  reached, and the depths are what `docs/SURFACE.md` has a depth-bound overlay carry: values
 *  gathered at different depths are not comparable, and a uniform wash would not say so. */
function survey(m, values, bounded, deep, total) {
  if (!note) return null;
  if (!m) { note.replaceChildren(); return null; }
  if (!values.length) {
    note.replaceChildren(el("div", "", `nothing on this path carries a ${m.key}`));
    return null;
  }
  const r = m.reads[reading];
  let min = values[0], max = values[0];
  for (const v of values) { if (v < min) min = v; if (v > max) max = v; }
  const lines = [
    `${values.length} of ${total} positions`,
    `${min.toFixed(r.dp)} – ${max.toFixed(r.dp)} ${r.unit}`
      + (relative(m) ? " · the path's own range" : ""),
  ];
  // Which rule laid the path out, because a downward measure is drawn over a path some
  // downward measure chose -- and when they are the same one, what is drawn is the choice
  // rather than anything about it.
  if (m.looks === "down") {
    lines.push(m.rule === taken
      ? "this measure chose the path as well as drawing it"
      : `the path follows ${taken}`);
  }
  // How much of that range is a bound and not a reading, which is the difference between
  // *the draw paid this* and *the draw paid at least this*.
  if (bounded) lines.push(`${bounded} of them are bounds · ${r.bound.word} and no nearer`);
  if (m.needs === "tail") {
    lines.push(deep[0] === deep[1]
      ? `${deep[0]} rows throughout`
      : `${deep[0]}–${deep[1]} rows · these are values from different depths`);
  }
  note.replaceChildren(...lines.map(text => el("div", "", text)));
  return null;
}

function chips(name, items, get, set, changed) {
  const box = el("div", "pick");
  box.append(el("div", "what", name));
  const row = el("div", "row");
  for (const item of items) {
    const go = el("button", "chip");
    go.onclick = () => { set(item.value); settle(); changed(); };
    if (item.title) go.title = item.title;
    sync.push(() => {
      go.textContent = typeof item.label === "function" ? item.label() : item.label;
      const on = get() === item.value;
      go.classList.toggle("on", on);
      go.setAttribute("aria-pressed", String(on));
      go.disabled = item.live ? !item.live() : false;
    });
    row.append(go);
  }
  box.append(row);
  return box;
}

/** The whole panel. `changed` is called after anything here moves, and the page re-reads
 *  rather than repainting what it has: turning a measure on is the read asking for what it
 *  did not ask for before, and one path costs milliseconds. */
export function panel(changed) {
  const out = new DocumentFragment();

  const head = el("button", "head");
  head.setAttribute("aria-expanded", "false");
  head.onclick = () => {
    const open = head.parentElement.classList.toggle("open");
    head.setAttribute("aria-expanded", String(open));
  };

  const body = el("div", "body");
  const says = el("div", "says");
  note = el("div", "note");

  const reads = which => () => {
    const m = pick();
    return m ? m.reads[which].unit : which;
  };
  const anchored = () => {
    const m = pick();
    return m !== null && m.reads[reading].domain !== null;
  };

  /* Which path is read comes before what is drawn over it, and it is chosen from the same
   * list: every downward measure is a rule, taking the child with the most of it. The two
   * are set apart because reading a path one measure chose while another is drawn over it is
   * the case that pays, and that is what a preset must leave reachable. */
  const rules = MEASURES.filter(m => m.looks === "down").map(m => ({
    label: m.key,
    value: m.rule,
    title: `continue into the child with the most ${m.key} below it`,
  }));

  body.append(
    chips("path", rules, () => taken, value => { taken = value; }, changed),
    chips("measure",
      [{ label: "none", value: null },
       ...MEASURES.map(m => ({ label: m.key, value: m.key }))],
      () => chosen, value => { chosen = value; }, changed),
    says,
    chips("reading",
      [{ label: reads("log"), value: "log", live: () => chosen !== null },
       { label: reads("linear"), value: "linear", live: () => chosen !== null }],
      () => reading, value => { reading = value; }, changed),
    // `fixed` is not offered where there is nothing to fix it to, and what is lit is what the
    // scale did rather than what was last asked for -- so a measure with no ceiling reads as
    // path-relative instead of claiming a domain it has not got.
    chips("domain",
      [{ label: "fixed", value: true, live: anchored },
       { label: "path", value: false, live: () => chosen !== null }],
      () => { const m = pick(); return m === null ? fixed : !relative(m); },
      value => { fixed = value; }, changed),
    note,
  );

  sync.push(() => {
    const m = pick();
    head.textContent = m ? m.key : "overlay";
    says.textContent = m ? m.what : "";
    // The survey is of a reading of a path, so the moment either moves it is about something
    // that is no longer on screen. Cleared here and filled again by the read that follows,
    // rather than left standing for however long that takes.
    note.replaceChildren();
  });

  out.append(head, body);
  settle();
  return out;
}
