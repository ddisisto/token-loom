/* What else was live at a position, and what became of each of them.
 *
 * `docs/SURFACE.md` has the three kinds a row can be -- the one taken here, one realised
 * elsewhere, and one nothing ever took -- and they are told apart by what the record already
 * says: a row carries the node that realised it or nothing, and the path says which of those
 * nodes is the one in front of the reader. So no row is marked by anything the page decided.
 *
 * The rows are drawn where a band would go. A ranking answers *what else was here* at a
 * position, which is the question a band answers at higher density, and giving them one place
 * is what keeps there from being two answers to it.
 */

/** Sources in the order they first appear, each with its own rows in descending logprob.
 *
 *  Within a source the order is a model's and the store does not enforce it -- a ranking
 *  deepened by a later act appends, and a near-tie at the join can leave two rows out of
 *  order -- so it is sorted here. Across sources it is not: a node several models ranked
 *  holds several rankings, and one order over their union would stand rows side by side that
 *  were never alternatives to each other.
 */
export function sorted(rows) {
  const by = new Map();
  for (const row of rows) {
    if (!by.has(row.source)) by.set(row.source, []);
    by.get(row.source).push(row);
  }
  for (const group of by.values()) group.sort((a, b) => b.logprob - a.logprob);
  return [...by.entries()];
}

/** Which of the three a row is, given the node the path takes next.
 *
 *  `took` costs nothing, being where the reader already is. `elsewhere` costs a selection and
 *  no act: the node exists and is off the path. `unrealised` is the only one that writes, and
 *  what it takes is a `realise` and then something to continue it.
 *
 *  A child carrying `deleted` is still a child, so a row whose node was set aside is
 *  `elsewhere` and not `unrealised` -- the merge key forbids realising it again, and what
 *  brings it back is `undelete`.
 */
export const kind = (row, next) =>
  row.child === null ? "unrealised" : row.child === next ? "took" : "elsewhere";

/** How much of the distribution the rows hold between them.
 *
 *  They sum to less than one because the rest of the vocabulary was never recorded, not
 *  because anything was truncated, so this is labelled as being over what was recorded. It
 *  belongs to the node and not to any act: a ranking extends across acts and is never
 *  rewritten, so the rows are the union of what everything passing through wrote down.
 */
export const recorded = rows => rows.reduce((sum, row) => sum + Math.exp(row.logprob), 0);

/* A newline is shown and not obeyed here. The column is where a newline is a newline; a row
 * is one line by its own construction, and obeying one would carry the rest of the list out
 * of alignment. */
const oneLine = text => text.replace(/\n/g, "\\n");

const el = (tag, className, text) =>
  Object.assign(document.createElement(tag), { className, textContent: text ?? "" });

/** Whether the reader wants rows at all. Nothing is asked for until they do, and a position
 *  can run to dozens of them -- `docs/SURFACE.md`'s *density stays behind intent*. */
let on = false;

export const asked = () => on;
export const want = yes => { on = yes; };

/* What has been read, by node. A ranking only grows -- `_extend_ranking` appends and never
 * rewrites -- so the rows themselves would keep for the life of the page. What does not keep
 * is `child`: an act realises a row, and the same response then says something different
 * about what became of it. So this is dropped whenever the record changes, which is the one
 * thing hovering makes load-bearing rather than an optimisation. */
const held = new Map();

export const remember = (node, payload) => { held.set(node, payload); };
export const recall = node => held.get(node);
export const forget = () => { held.clear(); };

/* ---- the second axis ----
 *
 * The order of a list of rows is the model's, and the bar behind each one is how far below
 * the top of that ranking it stands -- both of them the same opinion, stated twice because a
 * rank does not say by how much. What neither says is what the reader made of any of it.
 *
 * That is the downward family, read across the siblings at one position instead of down the
 * path -- `docs/SURFACE.md` has an overlay and a ranking as one quantity on two axes, and
 * this is the axis the rows were missing. It is drawn as the size of the token itself, since
 * what it reports is how much is there.
 *
 * It is not a second opinion about the model. A row's rank is fixed the moment it is
 * recorded; its weight moves with every act, and the two disagreeing is the whole of what
 * there is to see -- where the heaviest row is not the top one is where the reader steered.
 */

/** What one row weighs, or why it weighs nothing that can be read.
 *
 *  Two rows weigh nothing for different reasons and the difference matters: a row nothing
 *  realised has no node to measure, and a row whose node the descent did not reach has one
 *  the toggle is hiding. Both draw at the floor and they say different things, because a
 *  reader who read the second as the first would take an arm they pruned for one they never
 *  made.
 */
export function weight(row, weigh) {
  if (row.child === null) return { state: "none" };
  if (row.under === undefined) return { state: "unasked" };
  if (row.under === null) return { state: "hidden" };
  const value = weigh.of(row.under);
  if (!Number.isFinite(value)) return { state: "hole" };
  return { state: "value", value, count: row.under[weigh.key] };
}

/** Where each row sits on that axis, over the rows of its own source.
 *
 *  Against the heaviest of them, the way the bar is against the top row, because a count of
 *  what has been grown has no domain -- the same reason the downward measures carry no fixed
 *  one in `overlay.js`. So a list shows the shape of this position's exploration and not its
 *  share of the tree, and a position nothing was grown at is a list of even rows rather than
 *  a list of empty ones.
 */
export function spread(weights) {
  let max = 0;
  for (const w of weights) if (w.state === "value" && w.value > max) max = w.value;
  return weights.map(w => (w.state === "value" && max > 0 ? w.value / max : 0));
}

/** What a row's weight says, in words. The count and not the reading, because what a reader
 *  checks a size against is a number of nodes and the reading is how it was drawn. */
const says = (w, weigh) => {
  switch (w.state) {
    case "value":
      return `${w.count} below this`;
    case "none":
      return "nothing has realised this row, so nothing has been grown from it";
    case "hidden":
      return "what was grown here is set aside, and the toggle is hiding it";
    case "hole":
      return "no value here";
    default:
      return null;
  }
};

/** The rows at one node, as they stand beside the column.
 *
 *  `next` is the node the path takes from here, which is what makes one row the one taken.
 *  `pick` is handed a row and does whatever taking it means; nothing here decides that,
 *  because two of the three kinds cost nothing and the third is an act. `weigh` is the
 *  downward measure the rows are sized by, which arrives rather than being chosen here for
 *  the same reason the rule does -- the panel is where a way of looking is chosen.
 */
export function list(payload, next, pick, weigh) {
  const box = el("aside", "rows");
  const groups = sorted(payload.rows);
  if (!groups.length) {
    box.append(el("div", "none", "nothing was ranked at this position"));
    return box;
  }
  for (const [source, rows] of groups) {
    const name = payload.sources?.[String(source)] ?? `source ${source}`;
    const top = Math.exp(rows[0].logprob);
    const head = el("div", "who", name);
    head.append(el("span", "much",
      `${rows.length} rows · ${recorded(rows).toFixed(3)} of the mass recorded`));
    box.append(head);
    const weights = weigh ? rows.map(row => weight(row, weigh)) : [];
    const sizes = spread(weights);
    const out = el("ol", "list");
    for (const [i, row] of rows.entries()) {
      const p = Math.exp(row.logprob);
      const li = el("li", kind(row, next));
      const bar = el("span", "bar");
      // The bar is against the top row of this source and not against one, so a position the
      // model was unsure of does not read as a page of empty bars. What a logprob should look
      // like is open in `docs/SURFACE.md`; this is one answer and not the settled one.
      bar.style.setProperty("--p", (p / top).toFixed(4));
      li.append(bar, el("span", `spell${row.decodes ? "" : " raw"}`, oneLine(row.text)),
                el("span", "p", p.toFixed(3)));
      if (weigh) {
        // The place goes to the stylesheet and the count to the title: how much room a row
        // takes is the glance, and what it is a count of is the thing a reader checks.
        li.style.setProperty("--w", sizes[i].toFixed(4));
        const told = says(weights[i], weigh);
        if (told) li.title = `${weigh.key} · ${told}`;
        if (weights[i].state !== "value") li.classList.add("bare");
      }
      li.onclick = () => pick(row);
      out.append(li);
    }
    box.append(out);
  }
  return box;
}
