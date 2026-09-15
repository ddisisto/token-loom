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

function drawRoots(tree, current) {
  $("list").replaceChildren(...(tree.roots.length ? tree.roots.map(root => {
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
    if (root.id === current) li.setAttribute("aria-current", "true");
    li.onclick = () => show(root.id);
    return li;
  }) : [Object.assign(document.createElement("li"), {
    className: "none",
    textContent: "Nothing here yet.",
  })]));
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
  const flow = document.createElement("div");
  flow.className = "flow";
  flow.append(...spans(read.segments));
  $("column").replaceChildren(flow);
  // Which root is current is derived from the path rather than held beside the position,
  // so the two cannot disagree about where the reader is.
  const root = read.segments[0].nodes[0].id;
  for (const li of $("list").children)
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
  $("column").replaceChildren(compose(at));
  $("column").querySelector("textarea").focus();
}

// ---- the page -------------------------------------------------------------------------

function say(text, bad) {
  $("status").textContent = text;
  $("status").className = bad ? "fault" : "";
}

$("new").onclick = () => stage(null);
$("fold").onclick = () => {
  const folded = document.body.classList.toggle("folded");
  $("fold").setAttribute("aria-pressed", String(folded));
};

try {
  const tree = await refresh();
  // With nothing yet chosen the first root is what is read; with no roots at all the page
  // is never a bare one, because the only thing to do here is the only thing offered.
  if (tree.roots.length) await show(tree.roots[0].id);
  else stage(null);
} catch (why) {
  say(`${why.kind || "unreachable"}: ${why.message}`, true);
}
