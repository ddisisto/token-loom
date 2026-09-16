/* The surface: a list of roots, a reading column, and the one composer both of them use.
 *
 * The reader's position is a single node and everything else is derived from it -- which
 * root is current, what path is drawn, where a write will land. Holding a root as well
 * would be two pieces of state that can disagree, and `/path/{node}` already answers from
 * a node what the surface needs.
 *
 * Nothing here is remembered between loads. Reader state lives in the session, and what is
 * live, what parts and what a ranking holds are read from the store every time.
 */

const $ = id => document.getElementById(id);

/** The reader's position: a node, or nothing at all before there is a tree. */
let position = null;

/* Where a continuation hangs: the last node whose path has a string form, which is the leaf
 * unless the path ends mid-character. A segment cannot be split and nothing is addressed
 * inside one, so trailing bytes waiting for the rest of their character are not a position
 * the surface acts at -- and a draw that repeats them merges onto the same nodes. */
let addressable = null;

// ---- the wire -------------------------------------------------------------------------

class Fault extends Error {
  constructor(kind, message) { super(message); this.kind = kind; }
}

async function ask(path, body) {
  const answer = await fetch(path, body === undefined ? {} : {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const shape = await answer.json();
  // A fault says which kind it was because the record does: a refusal and a rejection are
  // answers about the request, and only a failure is worth repeating unchanged.
  if (!answer.ok) throw new Fault(shape.error || "error", shape.message || answer.statusText);
  return shape;
}

// ---- the list of roots ----------------------------------------------------------------

/** A label is one line and the column cuts it, so a newline is shown rather than obeyed. */
const oneLine = text => text.replace(/\n/g, "\\n");

function rootRow(root, current) {
  const li = document.createElement("li");
  li.append(oneLine(root.label));
  if (root.forked) {
    // It stopped where the tree parts rather than for room, and the two read the same in
    // the text. Part of the line, so it is clipped with it.
    const mark = document.createElement("span");
    mark.className = "fork";
    mark.textContent = " ⑂";
    mark.title = "the tree parts here";
    li.append(mark);
  }
  li.dataset.node = root.id;
  li.setAttribute("aria-current", String(root.id === current));
  li.onclick = () => show(root.id);
  return li;
}

/** Last in the list, which is the row the root it makes will occupy. */
function newRow() {
  const li = document.createElement("li");
  li.className = "new";
  const go = document.createElement("button");
  go.textContent = "+";
  go.title = "start something new";
  go.onclick = () => stage(null);
  li.append(go);
  return li;
}

function drawRoots(tree, current) {
  const rows = tree.roots.map(root => rootRow(root, current));
  if (!rows.length) rows.push(Object.assign(document.createElement("li"), {
    className: "none",
    textContent: "Nothing here yet.",
  }));
  $("roots").replaceChildren(...rows, newRow());
}

async function refresh(current) {
  const tree = await ask("/tree");
  drawRoots(tree, current);
  say(`${tree.path}  ${tree.vocabulary}  ` +
      `${tree.counts.nodes} nodes  ${tree.counts.edges} edges  ${tree.counts.acts} acts`);
  return tree;
}

// ---- the reading column ---------------------------------------------------------------

function spans(segments) {
  return segments.map(cell => {
    const el = document.createElement("span");
    el.className = cell.decodes ? "seg" : "seg raw";
    el.textContent = cell.text;
    el.dataset.node = cell.nodes[cell.nodes.length - 1].id;
    return el;
  });
}

/** Draw the path through a node and make it the position. */
async function show(node) {
  const read = await ask(`/path/${node}`);
  position = node;
  const closed = read.segments.filter(cell => cell.decodes);
  addressable = closed.length ? closed[closed.length - 1].nodes.at(-1).id : null;
  const flow = document.createElement("div");
  flow.className = "flow";
  flow.append(...spans(read.segments));
  $("column").replaceChildren(flow);
  // Which root is current is derived from the path rather than held beside the position,
  // so the two cannot disagree about where the reader is.
  const root = read.segments[0].nodes[0].id;
  for (const li of $("roots").querySelectorAll("li[data-node]"))
    li.setAttribute("aria-current", String(Number(li.dataset.node) === root));
}

// ---- the composer ---------------------------------------------------------------------

/* One component. What changes between starting something and continuing or branching from
 * a position is `at`, which is the node the text hangs under and is null for a root.
 *
 * Staging it writes nothing. The act is the submit, which is what keeps the gesture that
 * offers a place to write separate from the write.
 */
function compose(at) {
  const box = document.createElement("div");
  box.className = "compose";
  const area = document.createElement("textarea");
  area.placeholder = at === null
    ? "Something to start from. It is tokenised as written."
    : "Text to hang under this position.";
  const fault = document.createElement("span");
  fault.className = "fault";
  const go = document.createElement("button");
  go.textContent = "create";

  const submit = async () => {
    const text = area.value;
    if (!text) return;
    fault.textContent = "";
    go.disabled = area.disabled = true;
    try {
      const act = await ask("/create", { at, text });
      await refresh();
      await show(act.tip);
    } catch (why) {
      // A rejection left no trace in the record, so what it offers is an edit.
      fault.textContent = `${why.kind}: ${why.message}`;
      go.disabled = area.disabled = false;
      area.focus();
    }
  };

  go.onclick = submit;
  area.onkeydown = event => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) submit();
  };

  const foot = document.createElement("div");
  foot.className = "foot";
  foot.append(Object.assign(document.createElement("span"), {
    className: "grow", textContent: "⌘⏎ / ctrl⏎",
  }), fault, go);
  box.append(area, foot);
  return box;
}

function stage(at) {
  position = addressable = null;
  $("column").replaceChildren(compose(at));
  $("column").querySelector("textarea").focus();
}

// ---- continuing ------------------------------------------------------------------------

/* The gesture is the scroll: reaching the end of what there is to read asks for more of it,
 * at the end of the path, where the reader is already looking.
 *
 * A downward move *at* the end counts as well as an arrival there. Under about a thousand
 * characters the column sits at its minimum height, so text that lands does not make the
 * page any taller -- the room above it shrinks instead -- and a reader who stayed at the end
 * would have nowhere left to scroll and no way to ask again.
 */

/* A first pass, and sent rather than left out: what the surface defaults to lands in the
 * act's `params`, where a value the sampler chain picked would not. `top_k` is here because
 * the adapter requires `record_rows >= top_k > 0`, and `cache_prompt` because this backend
 * declares it required -- which is the page knowing a backend, and wants a better answer. */
const DRAW = {
  length: 80,
  temperature: 0,
  top_k: 10,
  record_rows: 10,
  record_mass: 0.9,
  cache_prompt: true,
};

const SETTLE = 140;  // ms of quiet before a scroll counts, so momentum is not a request
const REST = 450;    // ms after one lands, so a held key is one request and not twenty

let working = false;
let quiet = 0;
let timer = null;

const atEnd = () =>
  window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2;

function pending(...what) {
  const box = document.createElement("div");
  box.className = "pending";
  box.append(...what);
  const had = $("column").querySelector(".pending");
  if (had) had.replaceWith(box); else $("column").append(box);
  return box;
}

function waiting() {
  pending(Object.assign(document.createElement("span"), {
    className: "wait", textContent: "\u2026",
  }));
}

/** A failure is dismissable and says which kind it was, because the record does. */
function failed(why) {
  const box = pending(Object.assign(document.createElement("span"), {
    className: "grow", textContent: `${why.kind}: ${why.message}`,
  }));
  box.classList.add("fault");
  const go = document.createElement("button");
  go.textContent = "dismiss";
  go.onclick = () => box.remove();
  box.append(go);
}

/** Ask for more of the path. One at a time: there is no queue, and the server says so too. */
async function more() {
  if (working || addressable === null) return;
  working = true;
  waiting();
  try {
    // Ending mid-character is not the only reason a backend may decline a path, so the
    // predicate is asked at the position the act would use. Asking writes nothing, and the
    // answer is advisory -- what it saves is a refusal nobody needed to see.
    if (!(await ask(`/evaluable?node=${addressable}`)).evaluable) {
      pending(Object.assign(document.createElement("span"), {
        textContent: "The model will not continue from this position.",
      }));
      return;
    }
    const act = await ask("/generate", { at: addressable, params: DRAW });
    await refresh();
    await show(act.tip);
  } catch (why) {
    failed(why);
  } finally {
    working = false;
    quiet = Date.now() + REST;
    wasAtEnd = atEnd();  // what landed moved the end; an arrival at it is a fresh one
  }
}

/** Reached the end, and stayed there long enough to have meant it. */
function asked() {
  if (working || Date.now() < quiet) return;
  clearTimeout(timer);
  timer = setTimeout(() => { if (atEnd()) more(); }, SETTLE);
}

let wasAtEnd = false;
addEventListener("scroll", () => {
  const now = atEnd();
  if (now && !wasAtEnd) asked();
  wasAtEnd = now;
}, { passive: true });

// Already at the end, and still going down. Every way of moving the page is one of these.
addEventListener("wheel", event => { if (event.deltaY > 0 && atEnd()) asked(); },
                { passive: true });
addEventListener("keydown", event => {
  if (event.target.closest("textarea, input")) return;
  if (["ArrowDown", "PageDown", "End", " "].includes(event.key) && atEnd()) asked();
});

/** An act with no terminator is a generation in flight, so a reload draws it rather than
 *  losing it. One writer means there is at most one. */
async function resume() {
  const { acts } = await ask("/acts?in_flight=1");
  if (!acts.length) return false;
  working = true;
  waiting();
  while ((await ask("/acts?in_flight=1")).acts.length)
    await new Promise(again => setTimeout(again, 700));
  working = false;
  return true;
}

// ---- the page -------------------------------------------------------------------------

function say(text, bad) {
  $("status").textContent = text;
  $("status").className = bad ? "fault" : "";
}

$("fold").onclick = () => {
  const folded = document.body.classList.toggle("folded");
  $("fold").setAttribute("aria-pressed", String(folded));
};

try {
  const tree = await refresh();
  // With nothing yet chosen the first root is what is read; with no roots at all the page
  // is never a bare one, because the only thing to do here is the only thing offered.
  if (!tree.roots.length) stage(null);
  else {
    await show(tree.roots[0].id);
    // Something another page started, or this one was reloaded out from under.
    if (await resume()) {
      await refresh();
      await show(position);
    }
  }
  wasAtEnd = atEnd();
} catch (why) {
  say(`${why.kind || "unreachable"}: ${why.message}`, true);
}
