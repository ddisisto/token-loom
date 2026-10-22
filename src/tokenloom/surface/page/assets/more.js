/* Continuing: a draw asked for at the caret, the wake it leaves, and the caret kept in the
 * window while the reader scrolls.
 *
 * The gesture is the scroll: reaching the end of what there is to read asks for more of it,
 * at the caret -- which is where the reader is already looking, because left alone it follows
 * the end of the path. Pointing somewhere moves it, and then the same gesture asks there
 * instead: one anchor for every act at a position, and not a second rule for this one.
 *
 * A downward move *at* the end counts as well as an arrival there. Under about a thousand
 * characters the column sits at its minimum height, so text that lands does not make the
 * page any taller -- the room above it shrinks instead -- and a reader who stayed at the end
 * would have nowhere left to scroll and no way to ask again.
 *
 * An armed caret drops the end of the page from the gesture. Arriving at the end is what
 * makes an ordinary scroll deliberate; a caret armed by `realise` was placed by a click on a
 * row drawn in front of the reader, which is the same deliberateness spent earlier -- so the
 * next scroll down asks wherever the page is standing, and asking once disarms it.
 */

import { buying } from "./arm.js";
import { frontier } from "./column.js";
import { composing } from "./compose.js";
import * as cursor from "./cursor.js";
import { draw } from "./draw.js";
import { parked, shifting, still, stir } from "./edge.js";
import { atEnd, busy, drawn, rebase, scrolled as since, show, working } from "./reading.js";
import { refresh, writable } from "./roots.js";
import { settled } from "./rows.js";
import * as wake from "./wake.js";
import { ask, generated, say } from "./wire.js";

const $ = id => document.getElementById(id);

const SETTLE = 140;  // ms of quiet before a scroll counts, so momentum is not a request
const REST = 450;    // ms after one lands, so a held key is one request and not twenty
const AIR = 1.5;     // lines of context the caret keeps between itself and either edge

export let quiet = 0;
let timer = null;

function pending(...what) {
  const box = document.createElement("div");
  box.className = "pending";
  box.append(...what);
  const had = $("column").querySelector(".pending");
  if (had) had.replaceWith(box); else $("column").append(box);
  return box;
}

/* What a draw leaves behind it, which `wake.js` times. While it is asked for, a row of
 * placeholders stands straight after the caret, one for each token it may bring, and glows;
 * once it lands, what it brought takes them over segment by segment, and the run it makes
 * keeps the glow a while and then lets it go. So the mark answers *what just landed*, and
 * draws in quick succession leave a trail. The row is where the length line's pulse hands
 * over to -- that one stops as the draw is asked, which is when this one starts.
 *
 * A run is one element around its segments, so its glow is one box broken only where the line
 * breaks: a tunnel the text runs through, with no edge between one token and the next. */
let landing = null;  // a draw that has landed and is not drawn yet: { ids, length }
let traces = [];     // { ids, length, born, count, hold }: what each draw brought, while it shows
let revealing = [];  // { trace, segs, sizes, run }: what is still taking its placeholders over,
                     // and the last run of it, where what is left of the row stands

const column = $("column");

/** Give the stylesheet what `wake.js` times a draw's wake by. */
export function mount() {
  column.style.setProperty("--rise", `${wake.RISE}ms`);
  column.style.setProperty("--decay", `${wake.DECAY}ms`);
  column.style.setProperty("--wink-for", `${wake.WINK}ms`);
  column.style.setProperty("--dimmed",
                           `color-mix(in srgb, var(--accent) ${wake.DIM * 100}%, transparent)`);
}

const slots = n => Array.from({ length: n }, () => [
  Object.assign(document.createElement("span"), { className: "slot" }), " ",
]).flat();

/** A run around `els`, which stand next to each other in the flow. */
function enclose(els) {
  const run = document.createElement("span");
  run.className = "run";
  els[0].before(run);
  run.append(...els);
  return run;
}

/** Mark what is drawn with whatever is still under way, resumed where it had got to: the
 *  column is rebuilt by every read, and a rebuild is not the draw landing again. */
export function wakes() {
  const now = performance.now();
  const brought = (ids, cell) => cell.nodes.some(n => ids.has(n.id));
  if (landing !== null) {
    const { ids, length } = landing;
    const count = drawn.filter(cell => brought(ids, cell)).length;
    traces.push({ ids, length, born: now, count, hold: wake.hold(count, still.matches) });
    landing = null;
  }
  traces = wake.trail(traces, now);
  revealing = [];
  const segs = [...column.querySelectorAll(".flow .seg")];
  if (segs.length !== drawn.length) return;
  for (const trace of traces) {
    // The newest claims a segment first, since a variation that merged brings nodes an older
    // draw did.
    const at = drawn.flatMap((cell, i) =>
      traces.findLast(t => brought(t.ids, cell)) === trace ? [i] : []);
    if (!at.length) continue;
    const mine = at.map(i => segs[i]);
    // One run for each stretch that stands together, so wrapping never reorders the text.
    const stretches = at.reduce((out, i, k) => {
      if (k > 0 && i === at[k - 1] + 1) out.at(-1).push(segs[i]); else out.push([segs[i]]);
      return out;
    }, []);
    let run = null;
    for (const stretch of stretches) {
      run = enclose(stretch);
      run.style.setProperty("--hold", `${wake.delay(trace, now)}ms`);
      run.style.setProperty("--wink", `${wake.delay(trace, now) + wake.DECAY}ms`);
      const done = run;
      done.onanimationend = event => {
        if (event.target !== done || event.animationName !== "wink") return;
        // Moved, a segment still marked as arriving would arrive again.
        for (const el of done.querySelectorAll(".arrives")) el.classList.remove("arrives");
        done.replaceWith(...done.childNodes);
      };
    }
    // Under reduced motion it is simply there.
    if (!still.matches && now - trace.born < wake.arrived(trace.count)) {
      for (const el of mine) el.classList.add("due");
      revealing.push({ trace, segs: mine, sizes: at.map(i => drawn[i].nodes.length), run });
    }
  }
  if (revealing.length) requestAnimationFrame(unveil);
}

/** One frame of the runs taking their placeholders over: each segment due by now comes in,
 *  and what is left of the row stands after it, until the last is in and the row goes. */
function unveil(now) {
  for (const r of revealing) {
    const n = wake.shown(now - r.trace.born, r.trace.count);
    let tokens = 0;
    for (const [k, el] of r.segs.entries()) {
      if (k >= n) break;
      tokens += r.sizes[k];
      if (el.classList.contains("due")) el.classList.replace("due", "arrives");
    }
    const want = n >= r.trace.count ? 0 : wake.tail(r.trace.length, tokens);
    const have = r.run.querySelectorAll(".slot");
    if (have.length > want) {
      for (const slot of [...have].slice(want)) { slot.nextSibling?.remove(); slot.remove(); }
    } else if (have.length < want) {
      r.run.append(...slots(want - have.length));
    }
  }
  revealing = revealing.filter(r =>
    r.segs.some(el => el.classList.contains("due")) || r.run.querySelector(".slot") !== null);
  if (revealing.length) requestAnimationFrame(unveil);
}

/** The row of placeholders, straight after the caret, which is where what is asked for will
 *  start. A caret that ends a run still glowing stands the row after the run; one inside a run
 *  takes the run apart, since what follows it there is about to be replaced. */
function waiting(length = draw().length) {
  const at = column.querySelector(".flow .seg.at");
  const row = Object.assign(document.createElement("span"), { className: "run waiting" });
  row.append(...slots(length));
  if (at === null) return pending(row);
  const run = at.closest(".run");
  if (run === null) at.after(row);
  else if ([...run.querySelectorAll(".seg")].at(-1) === at) run.after(row);
  else {
    run.replaceWith(...run.childNodes);
    at.after(row);
  }
}

/** Take the text below the caret down while a variation is drawn at it, and put it back.
 *
 *  What stands below is what the draw is about to replace, and leaving it there shows the
 *  reader one continuation and then exchanges it for another. Hidden and not re-read: the
 *  segments below are part of what the text above is measured against, so a column rebuilt
 *  short would move the wash on lines this act is not about. The caret's own mark is what the
 *  stylesheet finds them by, every one of them being a sibling after it or after its run.
 */
function parting() {
  const flow = column.querySelector(".flow");
  if (flow === null) return waiting();
  flow.classList.add("parting");
  waiting();
}

function rejoin() {
  const flow = column.querySelector(".flow");
  if (flow === null) return;
  flow.classList.remove("parting");
}

/** What a variation left, said once it has landed.
 *
 *  **A draw that samples what was already below the caret merges onto it and moves nothing.**
 *  The tokens reach existing nodes through `(parent, token_id, source)` and the act records
 *  them like any others, so nothing in the response distinguishes the case -- and at
 *  temperature zero it is the ordinary one, the path below a node being a greedy descent
 *  already. It is the one outcome the reader cannot see, so it is the one that is said.
 *
 *  Whether the text moved is a node that is on the screen and was not, which is the question
 *  asked rather than a count of what the act wrote: an act writes the same nodes whether they
 *  were there before or not.
 */
function parted(act, was) {
  const moved = drawn.flatMap(cell => cell.nodes).some(n => !was.has(n.id));
  const drew = `${act.nodes.length} token${act.nodes.length === 1 ? "" : "s"} drawn`;
  say(moved
    ? `${drew} \u00b7 enter again for another variation`
    : `${drew} onto what was already here \u00b7 the text has not moved`);
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

/** Ask for more of the path, at a node. The scroll gesture passes the end of what is being
 *  read; the caret passes wherever the reader put it, and a draw there is what makes a fork
 *  -- the tokens either merge onto what already follows or part from it.
 *
 *  **`pin` keeps the caret where it is, which makes the act repeatable without aiming it
 *  again.** The ordinary draw carries the caret to the tip, which is the batch discipline
 *  `docs/SURFACE.md` names: asking for the next batch carries acceptance of the last. A
 *  variation at a fixed position is the other thing a draw can be -- several continuations
 *  from one node, read against each other -- and there the caret is the position being asked
 *  about rather than the frontier of what has been read. The path drawn is the one that
 *  landed and not the one the rule would pick, because the read is through the act's own tip.
 */
export async function more(where = cursor.node(), { pin = false } = {}) {
  // A roll in flight is the other writer there is, and it holds a warm prompt cache a draw
  // from somewhere else would truncate -- `docs/SPINE.md` measures that at 28 ms against
  // 7.4 s. A scroll during one is dropped rather than queued, the same as during a draw.
  //
  // An open composer holds it too. The reader is writing the continuation at this position by
  // hand, and a draw landing under them would answer the question they are in the middle of.
  if (working || composing() || buying !== null || !writable) return;
  if (where === null || where === undefined) return;
  busy(true);
  // Taken before the act, because what is drawn is replaced by it and the comparison is what
  // says whether the draw parted from anything.
  const was = pin ? new Set(drawn.flatMap(cell => cell.nodes).map(n => n.id)) : null;
  if (pin) parting(); else waiting();
  try {
    // Ending mid-character is not the only reason a backend may decline a path, so the
    // predicate is asked at the position the act would use. Asking writes nothing, and the
    // answer is advisory -- what it saves is a refusal nobody needed to see.
    if (!(await ask(`/evaluable?node=${where}`)).evaluable) {
      pending(Object.assign(document.createElement("span"), {
        textContent: "The model will not continue from this position.",
      }));
      return;
    }
    // Asked for at the moment of the act, so what the panel holds now is what is sent and
    // what the record keeps. Nothing here caches it.
    const params = draw();
    const act = await generated({ at: where, params });
    landing = { ids: new Set(act.nodes.map(n => n.id)), length: params.length };
    await refresh();
    // An `eos` before anything was drawn names no tip, and the path is where it was.
    await show(act.tip ?? where, pin ? where : undefined);
    if (pin) parted(act, was);
  } catch (why) {
    failed(why);
  } finally {
    // Every way out of here, including the refusal that returns without drawing. A path that
    // landed has replaced the flow this was set on, so there is nothing left to put back.
    if (pin) rejoin();
    // A draw that failed leaves the flow it was asked in, placeholders and all.
    column.querySelector(".flow .waiting")?.remove();
    landing = null;
    busy(false);
    quiet = Date.now() + REST;
    // What landed moved the end and may have moved the window: an arrival at the end is a
    // fresh one, and where the page now stands is not somewhere the reader scrolled to.
    rebase();
    stir();  // a draw disarms the caret and moves the end
  }
}

/** Whether a downward move counts as a request: at the end of the page, or anywhere at all
 *  once the caret has been armed -- and never while the room is parked, which is what parking
 *  is for. */
export const ready = () => !parked && (cursor.armed() || atEnd());

/** Put the caret back in the window, if scrolling has carried it out.
 *
 *  The gesture that asks for a draw is the scroll and the draw lands at the caret, so a caret
 *  off the screen aims an act at a position nobody is looking at. Following the window is
 *  what keeps *the draw lands where you are looking* true rather than usually true -- and it
 *  is what makes the end of the page and the caret agree again, since a reader who pointed
 *  somewhere and then scrolled to the foot was drawing thousands of tokens above it.
 *
 *  **An armed caret does not move.** It is the one the reader chose, on a row drawn in front
 *  of them, and the next downward scroll is the draw -- so there is no reading to keep up
 *  with, and drifting off it would both aim the act elsewhere and disarm it on the way.
 *
 *  It costs no read, and `point` has why it may not take one: this is a mark that moves over
 *  text that does not.
 */
function dodge() {
  if (working || cursor.armed() || cursor.node() === null) return;
  const segs = $("column").querySelectorAll(".flow .seg");
  if (segs.length !== drawn.length) return;  // the composer, or a read in flight
  // A caret hard against an edge is one the reader has to hunt for, and the line it marks is
  // half a line of context in either direction. The band is reckoned in lines and not in
  // pixels, so it holds whatever the column is set in.
  const line = parseFloat(getComputedStyle($("column")).lineHeight) || 24;
  const air = line * AIR;
  const room = window.innerHeight;
  const to = cursor.seated(drawn, cursor.node(), i => {
    const box = segs[i].getBoundingClientRect();
    if (box.top < air) return -1;
    if (box.bottom > room - air) return 1;
    return 0;
  });
  if (to === null || to === cursor.node()) return;
  cursor.place(to);
  frontier();
  settled();
}

/* One settle for both, because they are one gesture read twice and the order between them
 * matters: the caret goes back in the window first, and what is asked for is asked at where
 * it ended up. Two timers would race, and the losing order draws at a position that was about
 * to move. */
let wanted = false;

export function moved(counts) {
  wanted = wanted || counts;
  clearTimeout(timer);
  timer = setTimeout(() => {
    const ask = wanted;
    wanted = false;
    dodge();
    if (ask && !working && Date.now() >= quiet && ready()) more();
  }, SETTLE);
}

/** A scroll the reader made, with `end` whether it stood at the end of the page before anything
 *  it set off moved it. Every scroll settles, because the caret follows the window whichever
 *  way it went. Only some of them ask for anything. */
export function scrolled(end) {
  // Downward and not merely different. At the end of the page there is nowhere below to go,
  // so an arrival there is the gesture; an armed caret has no such place, so the direction is
  // all there is -- and what lands after an act can shorten the page and move the window on
  // its own, which would otherwise read as a reader asking for the next one.
  const went = since(end);
  // A room being moved shifts the end of the page under a reader who has not scrolled.
  moved(!shifting && ((cursor.armed() && went.down) || went.arrived));
}

/** An act with no terminator is a generation in flight, so a reload draws it rather than
 *  losing it. One writer means there is at most one.
 *
 *  On a server that only reads, the act is another writer's, and it is said rather than waited
 *  on or called abandoned. */
export async function resume() {
  const { acts } = await ask("/acts?in_flight=1");
  if (!acts.length) return false;
  if (!writable) {
    say(`act ${acts[0].id} is a draw in flight: the writer holding this tree is drawing it, `
        + "or is gone and the next writer will record it aborted \u00b7 reload to see it land");
    return false;
  }
  busy(true);
  // As long as the act asked for, which the record holds and the page's setting may not.
  waiting(acts[0].params?.length);
  while ((await ask("/acts?in_flight=1")).acts.length)
    await new Promise(again => setTimeout(again, 700));
  busy(false);
  return true;
}
