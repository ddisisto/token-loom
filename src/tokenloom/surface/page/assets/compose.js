/* The composer: a root's, in place of the column, and one in the text at the caret.
 *
 * One component. What changes between starting something and continuing or branching from
 * a position is `at`, which is the node the text hangs under and is null for a root.
 *
 * Staging it writes nothing. The act is the submit, which is what keeps the gesture that
 * offers a place to write separate from the write.
 */

import * as cursor from "./cursor.js";
import * as ranking from "./ranking.js";
import { blank, busy, drawn, rebase, show, working } from "./reading.js";
import { refresh, writable } from "./roots.js";
import { unshown } from "./rows.js";
import { ask, say, wrong } from "./wire.js";

const $ = id => document.getElementById(id);

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

export function stage(at) {
  blank();
  unshown();
  if (!writable) return $("column").replaceChildren();
  $("column").replaceChildren(compose(at));
  $("column").querySelector("textarea").focus();
}

/* **A token the model never ranked is one the surface cannot reach, and nothing past it is
 * reachable either.** The rows are what the record ranked, so a word the model did not
 * consider is a branch no gesture arrives at -- and the reader who wants to steer through one
 * has no way to say so. The act for it is already here: `create` takes the position it hangs
 * under, `/create` forwards it, and `compose` has been written for both cases from the start.
 * What was missing is a place to type that is not the whole column.
 *
 * So this is that component's other half rather than a second composer. A root replaces the
 * column because there is nothing to read yet; this one stands *in* the text at the caret, and
 * what is below it stays. **A draw at the caret takes that text down and this does not**, which
 * looks like the same gesture wanting two answers and is not: a draw replaces what is below with
 * something the reader has not seen, and the old text standing under it would be read as part of
 * the new one. Here the reader is writing the replacement themselves, and what they are replacing
 * is the thing they want in front of them while they do.
 */

/** Whether a composer is open in the column. It holds the gestures that write, because they
 *  all land at the caret and the caret is where the typing is going. */
export const composing = () => $("column").querySelector(".author") !== null;

/** Take an open composer away, from wherever the reader is when they ask.
 *
 *  **The key that leaves it is the page's and not the box's.** A reader who clicked somewhere
 *  else has a composer that is still open and no longer has the focus, and the way out of it
 *  cannot be a key only the thing they just left would hear.
 */
export function unauthor() {
  $("column").querySelector(".author")?.remove();
  say("");
}

/** Open a composer at the caret, carrying the token it would stand instead of.
 *
 *  **Pre-filled and selected, so the first keystroke is the replacement.** The token after the
 *  caret is the one being reconsidered -- the one the rows are alternatives to and the one the
 *  column outlines -- so it is read with the same derivation that marks it, and the box starts
 *  on exactly what is marked. At the tip there is no such token and the box starts empty, which
 *  is the same gesture with nothing to say about it.
 *
 *  **What it writes is a sibling and never a change.** The text hangs under the caret, so the
 *  token that stood there still stands, on its own branch, with everything below it: authoring
 *  takes nothing away and the act is as reversible as any other. What is drawn afterwards is
 *  the path through what was made, which is `show` doing what it does for every act.
 */
export function author() {
  if (working || composing() || !writable) return;
  const flow = $("column").querySelector(".flow");
  const at = cursor.node();
  if (flow === null || at === null) return;
  const standing = ranking.subject(drawn, at);

  const box = document.createElement("span");
  box.className = "author";
  box.spellcheck = false;
  // `plaintext-only` is what keeps a paste from bringing markup in with it, and setting it
  // where it is not understood throws rather than being ignored. Falling back leaves the box
  // editable and loses nothing that matters: what is sent is `textContent` either way.
  const editable = yes => {
    const want = yes ? "plaintext-only" : "false";
    try { box.contentEditable = want; } catch { box.contentEditable = yes ? "true" : "false"; }
  };
  editable(true);
  box.textContent = standing === null ? "" : drawn[standing.cell].text;

  let sending = false;

  const send = async () => {
    const text = box.textContent;
    if (sending || !text) return;
    sending = true;
    busy(true);
    editable(false);
    try {
      const act = await ask("/create", { at, text });
      await refresh();
      // Which replaces the column, and the composer with it.
      await show(act.tip);
      say(`${act.nodes.length} token${act.nodes.length === 1 ? "" : "s"} authored`);
    } catch (why) {
      // A rejection left no trace in the record, so what it offers is an edit and not a
      // dismissal -- the same answer the root composer gives, in the one place there is.
      wrong(why);
      editable(true);
      box.focus();
      sending = false;
    } finally {
      busy(false);
      rebase();
    }
  };

  box.onkeydown = event => {
    if (event.key === "Escape") { event.preventDefault(); unauthor(); return; }
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      send().catch(() => {});
    }
  };

  // In the text at the caret, and not instead of it. **What stands below is what the reader is
  // writing an alternative to**, so it is theirs to look at while they do -- taking it down
  // would hide the one thing the new text is being measured against. It moves along and down to
  // make room, which is what text does for text.
  const mark = flow.querySelector(".seg.at");
  if (mark === null) flow.append(box); else mark.insertAdjacentElement("afterend", box);
  box.focus();
  // The whole of it, so typing replaces rather than appends. A caret left at one end would
  // make the pre-fill something to delete, which is the opposite of what putting it there
  // was for.
  const all = document.createRange();
  all.selectNodeContents(box);
  const where = window.getSelection();
  where.removeAllRanges();
  where.addRange(all);
  say("typing replaces it \u00b7 ctrl\u23ce writes it, esc leaves");
}
