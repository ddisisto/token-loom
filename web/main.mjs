// The instrument: a given goes in at the root, and everything after that is
// navigation.
//
// The two acts are supply and selection, and the reader's agency is entirely
// in the second. So this file is mostly about where the reader is standing and
// what that makes available; generation happens as a consequence of movement
// and is never asked for directly.
//
// **View state keys off positions, never off indices.** Runs renumber the
// moment a branch appears -- `FRONTEND.md` constraint 7 -- so where the slider
// is, and how deep the reader got down each branch, are recorded as
// `(span, offset)` and resolved against the tree each render. An index held
// across a mutation is a bug with a delay on it.

import { Refusal, Writes, api, pollWhile } from './api.mjs';
import {
  activePath, ancestry, endOf, forks, forget as forgetText, nodeState,
  unrenderable,
} from './path.mjs';
import * as flyout from './flyout.mjs';
import {
  banner, cardStrip, follow, place, renderFlow, renderMargin,
} from './surface.mjs';

/** The stops on the chunk slider, in tokens.
 *
 * The one generation parameter the surface exposes, because its effect is
 * pacing rather than behaviour, and pacing is a reader's business. Each value
 * interns as its own parameter set, so a tree records where its reader changed
 * pace -- which is interning working as intended.
 */
const CHUNKS = [8, 16, 32, 64, 96];
const START = 2;

/** How much of the line above the band is kept in view when the page follows
 * the target: one line, because the text a choice follows from is part of the
 * choice. In `rem` so it tracks the type rather than the screen. */
const LEAD = 32;

const dom = {};
const state = {
  tree: null,
  settings: null,
  chunk: CHUNKS[START],
  // The fork the target is on, as a position, and `undefined` for "wherever
  // the tip is". Not `null` for that, which is a real position: the root fork
  // has no pieces and so no address, and `endOf` answers `null` for it. Using
  // one value for both meant up from the first fork silently retargeted the
  // tip instead -- it moved the selection and nothing else, which looks like a
  // stuck key rather than like a bug.
  sliderAt: undefined,
  // Which card is selected, and `null` for "whichever one the path already
  // goes through". A number is the reader having said otherwise. Defaulting to
  // 0 was wrong wherever the target's fork had already been chosen through --
  // it drew card 0 as selected while the prose below it was card 1, which is
  // the surface contradicting itself. Reachable on load, since the last fork
  // has a chosen child in any tree whose tip does not.
  card: null,
  deepest: new Map(),   // first span of a branch -> the deepest tip seen down it
  readOnly: false,
};

const writes = new Writes();

// -- where the reader is ---------------------------------------------------

const key = (pos) => (pos === null ? '.' : `${pos.span}+${pos.offset}`);

/** The forks along the path, which one the target is on, and which card of it.
 *
 * Resolved by position rather than kept as an index, so a branch appearing
 * anywhere earlier does not silently move the target somewhere else. The card
 * is resolved here too, and for the same reason: `state.card` is an override
 * and the default is whatever the path itself goes through, which only the
 * tree can answer.
 */
function slider() {
  const points = forks(state.tree);
  if (!points.length) return { points, index: -1, fork: null, card: 0 };
  let index = points.length - 1;
  if (state.sliderAt !== undefined) {
    const found = points.findIndex((f) => key(f.at) === key(state.sliderAt));
    if (found >= 0) index = found;
  }
  const fork = points[index];
  const want = state.card === null ? Math.max(0, fork.active) : state.card;
  return {
    points,
    index,
    fork,
    card: Math.max(0, Math.min(want, fork.children.length - 1)),
  };
}

// -- the address bar -------------------------------------------------------

/** Where the reader is standing, as a fragment: `#s7+31/1`.
 *
 * The target fork in the grammar `loom.py` parses, and which of its cards is
 * selected. Written on every draw and read on load, so the address bar is a
 * live readout of the reader's location and a link that puts someone else in
 * front of the same thing -- which is mostly what it is for: "look at this"
 * is otherwise a paragraph of directions.
 *
 * **The cursor is deliberately not in it.** It lives in the tree, on disk, so
 * a link opened against the same tree already lands on the same path; putting
 * it in the URL as well would mean a page load quietly rewriting where the
 * reader was. The fragment names where you are *standing*, not which path you
 * are standing on.
 *
 * `replaceState` rather than `pushState`: the browser's back button belongs to
 * the reader, and one history entry per arrow key would take it from them.
 */
function locate(fork, card) {
  if (!fork) return;
  const at = fork.at === null ? '.' : `${fork.at.span}+${fork.at.offset}`;
  const hash = `#${at}/${card}`;
  if (hash !== window.location.hash) history.replaceState(null, '', hash);
}

/** The same, read back. `null` when there is no fragment or it is not one of
 * ours -- a hand-typed address is a reasonable thing to be wrong, and falling
 * back to the tip is the same thing that happens when a target has been
 * deleted out from under the reader. */
function located() {
  const raw = decodeURIComponent(window.location.hash.slice(1));
  if (!raw) return null;
  const [where, card] = raw.split('/');
  let at;
  if (where === '.') at = null;
  else {
    const parsed = /^([A-Za-z0-9_-]+)\+(\d+)$/.exec(where);
    if (!parsed) return null;
    at = { span: parsed[1], offset: Number(parsed[2]) };
  }
  const n = Number(card);
  return { at, card: Number.isInteger(n) && n >= 0 ? n : null };
}

/** Remember how far the reader got down every branch on the current path.
 *
 * Keyed by the first span of each branch, which is durable, and consulted when
 * a re-route lands on that branch again. A session that has forgotten lands at
 * the fork, which is the honest fallback rather than a degraded one -- and a
 * reload forgets all of it, because none of it is written down.
 */
function remember() {
  const tip = state.tree.selected;
  if (!tip) return;
  for (const step of ancestry(state.tree, tip)) {
    state.deepest.set(step.span, tip);
  }
}

/** Where to stand after routing onto `node`: as deep as this reader has been. */
function resumeInto(node) {
  const first = node.pieces.length ? node.pieces[0].span : null;
  const held = first === null ? null : state.deepest.get(first);
  if (held && state.tree.spans[held.span]
    && Object.hasOwn(state.tree.live, held.span)) return held;
  return endOf(node);
}

// -- talking to the server -------------------------------------------------

function refused(e) {
  if (!(e instanceof Refusal)) throw e;
  banner(dom.banners, e.detail);
}

/** Apply a whole-tree response. The response *is* the new state.
 *
 * `chase` is whether this draw should bring the target back into view. True
 * for everything the reader did and false for everything that merely arrived:
 * a poll filling a card must not move the page under them. See `follow`.
 */
function apply(tree, chase = true) {
  state.tree = tree;
  draw(chase);
  route();
}

/** The selection is the path: if the tree does not run through the selected
 * card, make it.
 *
 * **This is the whole of what dissolving "selected" and "confirmed" means.**
 * The surface used to hold the two apart at exactly one fork -- the last one,
 * where alternatives were on offer rather than chosen -- and behind it
 * selecting already re-routed. One gesture with two rules, and the seam showed:
 * stepping up from the tip left the lower half of the page blank, because the
 * card being read was not on the path and so nothing followed it.
 *
 * Called from `apply` rather than from the acts, because the default selection
 * has to hold the invariant too. A batch of two arrives with card 0 selected
 * and nobody having pressed anything; a permalink names a card; a tree written
 * by `loom.py` opens with its cursor wherever the command line left it. All
 * three are the same case and none of them is a keystroke.
 *
 * Three things keep it from running away:
 *
 * - **A card still in flight is not routed onto.** Its run has no bytes yet, so
 *   its end is byte 0, and recording that would say the path leaves the span
 *   where it starts -- which stops being true the moment the bytes land, and
 *   `loom.py gen` from that cursor would branch at the wrong end of it.
 * - **The stop condition is the position, not the index.** Once the cursor
 *   equals the card's end there is nothing to write, so the response this write
 *   provokes cannot provoke another.
 * - **Never while something is queued.** `Writes.submit` replaces what is
 *   waiting, and what is waiting is usually the reader's next keypress. The
 *   write that is running will apply, and this runs again then.
 */
function route() {
  if (writes.queued) return;
  const { fork, card } = slider();
  if (!fork || fork.active === card) return;
  const node = fork.children[card];
  if (!node || nodeState(state.tree, node) !== 'ready') return;
  const to = endOf(node);
  const at = state.tree.selected;
  if (!to || (at && at.span === to.span && at.offset === to.offset)) return;
  writes.submit(async () => {
    apply(await api.cursor(to));
    remember();
  }, refused);
}

function settingsNow() {
  return { ...state.settings, length: state.chunk };
}

// -- the acts --------------------------------------------------------------

/** Carry on from the selected card: generate from its end.
 *
 * The cursor is normally already there -- `route` put it there when the card
 * was selected -- so the write is a no-op and what down does is the
 * generation. It is still written rather than assumed, because there is one
 * case where it is not a no-op: a card selected while it was still in flight
 * was not routed onto, and pressing down once it lands is the reader saying
 * they meant it.
 */
function confirm() {
  const { fork, card } = slider();
  if (!fork) return;
  const node = fork.children[card];
  if (!node || nodeState(state.tree, node) !== 'ready') return;

  // the cursor is written before the generation rather than after, so a reload
  // during a long call lands where the reader is and not a step behind it
  const at = endOf(node);
  state.sliderAt = undefined;
  state.card = null;
  writes.clearPending();
  writes.submit(async () => {
    apply(await api.cursor(at));
    remember();
    apply(await api.generate(at, 2, settingsNow()));
  }, refused);
}

/** Move the selection, which *is* moving the path. Everywhere, now.
 *
 * `resumeInto` rather than the card's end, which is the one thing this does
 * that `route` does not: a reader who went a long way down a branch and came
 * back to compare should land where they were, not at the top of it again.
 * `route` is the floor and this is the memory.
 *
 * The target is pinned to this fork before the write. Without that the cursor
 * moving could take the target with it -- if the branch selected has been
 * generated from before, the last fork on the path is suddenly deeper than the
 * one the reader is standing at.
 */
function select(index) {
  const { fork } = slider();
  if (!fork || index < 0 || index >= fork.children.length) return;
  state.card = index;
  if (index === fork.active) return draw();            // already on the path
  const node = fork.children[index];
  // a card still generating is selected but not walked onto; see `route`
  if (nodeState(state.tree, node) !== 'ready') return draw();

  const to = resumeInto(node);
  state.sliderAt = fork.at;
  writes.submit(async () => {
    apply(await api.cursor(to));
    remember();
  }, refused);
}

/** Move the selection onto a card that has just arrived.
 *
 * **By the span it holds, never by its index.** A generation attaches at a
 * position; which card that becomes is the layout's business, and `wire.py`
 * sends runs as composition and promises no order -- the same reason
 * `path.mjs:continues` decides by bytes rather than by position.
 *
 * Assuming the newest card is the last one was wrong at exactly one kind of
 * fork, which is how it was found: at a fork made by a counterfactual branch,
 * `outline` emitted the branches first and the span carrying on past the cut
 * last, so a fresh continuation landed second from the right and the selection
 * stayed on the card to its right. `outline` now orders that list oldest
 * first, so the two agree -- and this reads the span rather than trusting that
 * they will keep agreeing.
 */
function landed(made) {
  if (!made) return;
  const { fork } = slider();
  const i = fork ? fork.children.findIndex(
    (c) => c.pieces.length && c.pieces[0].span === made) : -1;
  if (i < 0) return;
  state.card = i;
  draw();
}

/** Ask for one more continuation at this fork.
 *
 * A fresh draw rather than a repeat: seeds derive from the tree's base seed
 * plus a call index, so every continuation ever made at a position has its
 * own. A reader who finds two cards holding the same text and wants a third is
 * asking a reasonable question of the model.
 */
function grow() {
  const { fork } = slider();
  if (!fork || writes.busy) return;
  if (state.readOnly) {
    banner(dom.banners, 'no model server is attached, so nothing can be '
      + 'generated; the tree still reads');
    return;
  }
  // only a continuation still running blocks another. One that finished with
  // no bytes is finished, and asking for one more is the *only* thing left to
  // do there -- an end-of-text at a tip stops the path, and refusing to grow
  // as well leaves the reader with no move at all. Any child in flight, rather
  // than the last one: with a resuming branch at the end of the strip, the
  // last card is the oldest text at that fork and says nothing about what is
  // still running.
  if (fork.children.some((c) => nodeState(state.tree, c) === 'flight')) return;
  const at = fork.at;
  writes.submit(async () => {
    const tree = await api.generate(at, 1, settingsNow());
    apply(tree);
    landed(tree.created && tree.created[0]);
  }, refused);
}

/** Take the slider back one fork, which is what up does from anywhere. */
function back() {
  const { points, index } = slider();
  if (index <= 0) return;
  state.sliderAt = points[index - 1].at;
  state.card = null;
  draw();
}

/** And forward again, the inverse of the above.
 *
 * `INTERACTION.md` names up and not down for this, because down at the tip is
 * confirm. At an earlier fork there is nothing to confirm -- selecting is what
 * re-routes there, and it has already happened -- so down means the only other
 * movement available, which is towards the tip.
 */
function forward() {
  const { points, index } = slider();
  if (index < 0 || index >= points.length - 1) return;
  state.sliderAt = index + 1 === points.length - 1
    ? undefined : points[index + 1].at;
  state.card = null;
  draw();
}

// -- the finer grain -------------------------------------------------------

async function interrogate(event) {
  const at = flyout.addressOf(state.tree, event);
  if (!at) return;
  try {
    const token = await flyout.tokenAt(at.span, at.offset);
    if (!token) return;
    flyout.render(dom.flyout, token, event.pageX + 8, event.pageY + 12, {
      onTake: (rank) => take(at.span, token.idx, rank),
    });
  } catch (e) {
    refused(e);
  }
}

/** Branch onto an alternative the model ranked and did not sample.
 *
 * Instant and calls no model. What comes back is a span one token long,
 * anchored at that token's offset; the remainder of the span being read becomes
 * its sibling, so prose that had no choice point in it acquires one.
 */
function take(spanId, index, rank) {
  dom.flyout.hidden = true;
  writes.clearPending();
  writes.submit(async () => {
    const tree = await api.branch(spanId, index, rank);
    apply(tree);
    const made = tree.created && tree.created[0];
    if (!made) return;
    const at = { span: made, offset: tree.spans[made].length };
    state.sliderAt = undefined;
    state.card = null;
    apply(await api.cursor(at));
    remember();
    apply(await api.generate(at, 2, settingsNow()));
  }, refused);
}

// -- drawing ---------------------------------------------------------------

function draw(chase = true) {
  if (!state.tree) return;
  const spans = Object.keys(state.tree.spans);
  dom.seed.hidden = spans.length > 0;
  dom.reading.hidden = spans.length === 0;
  if (!spans.length) return;

  const cannot = unrenderable(state.tree);
  if (cannot.length) {
    dom.reading.hidden = true;
    dom.refuse.hidden = false;
    dom.refuse.textContent = `This tree holds bytes with no string form in `
      + `${cannot.join(', ')} — a branch onto a fragment of a character. `
      + `loom.py can read it; this surface cannot show it without guessing.`;
    return;
  }
  dom.refuse.hidden = true;

  const { points, index, fork, card } = slider();
  const atTip = index === points.length - 1;

  // asking for one more belongs to the last fork and to its right-hand end.
  // It used to be gated on nothing having been chosen there as well, which
  // stopped meaning anything once selecting became choosing.
  const strip = cardStrip(state.tree, fork, card, {
    growable: Boolean(fork) && atTip && !state.readOnly
      && card === fork.children.length - 1
      && nodeState(state.tree, fork.children[card]) !== 'flight',
  });

  // one flow, laid out once and drawn twice: the clone is a copy of the
  // finished layout rather than a second render, which is what guarantees the
  // two halves agree about where every glyph is
  const { nodeOf } = renderFlow(dom.above, state.tree);
  dom.below.replaceChildren(
    ...[...dom.above.childNodes].map((n) => n.cloneNode(true)));
  dom.band.replaceChildren(...(strip ? [strip] : []));

  // the cross-section is behind the tip when the reader has come back to an
  // earlier fork, and what lies past it is dimmed rather than removed
  // the fork's address, so the strip slides between cards of one fork and is
  // placed outright when the reader steps to a different one
  const shift = place(dom, index < 0 ? -1 : nodeOf[index],
    { muted: !atTip, at: fork ? key(fork.at) : null });
  renderMargin(dom.margin, dom.above, points, index, shift);
  locate(fork, card);
  if (chase) follow(dom.band, LEAD);
}

// -- the seed --------------------------------------------------------------

function submitSeed() {
  const text = dom.input.innerText.replace(/ /g, ' ');
  if (!text.trim()) return;
  writes.submit(async () => {
    const tree = await api.author(null, text);
    apply(tree);
    const made = tree.created[0];
    const at = { span: made, offset: tree.spans[made].length };
    apply(await api.cursor(at));
    remember();
    apply(await api.generate(at, 2, settingsNow()));
  }, refused);
}

// -- wiring ----------------------------------------------------------------

function chunkChanged(index) {
  state.chunk = CHUNKS[index];
  dom.chunkValue.textContent = String(state.chunk);
  dom.chunkValue.classList.add('showing');
  clearTimeout(chunkChanged.timer);
  chunkChanged.timer = setTimeout(
    () => dom.chunkValue.classList.remove('showing'), 1500);
}

function keys(event) {
  if (dom.seed.hidden === false) return;
  const { fork, index, points, card } = slider();
  if (!fork) return;
  if (event.key === 'ArrowLeft') { select(card - 1); }
  else if (event.key === 'ArrowRight') {
    if (card + 1 < fork.children.length) select(card + 1);
    else if (index === points.length - 1) grow();
  } else if (event.key === 'ArrowUp') { back(); }
  else if (event.key === 'ArrowDown' || event.key === 'Enter') {
    // down is always towards the tip; at the last fork that means confirming
    if (index === points.length - 1) confirm();
    else forward();
  } else return;
  event.preventDefault();
}

function clicks(event) {
  const chip = event.target.closest('.chip');
  if (chip) {
    const { points } = slider();
    const at = points[Number(chip.dataset.fork)];
    state.sliderAt = at.at;
    state.card = null;
    return draw();
  }
  const card = event.target.closest('.card');
  if (card) {
    if (card.dataset.grow) return grow();
    const i = Number(card.dataset.card);
    const { index, points, card: at } = slider();
    // a mouse reader does in two clicks what arrow-then-down does from the
    // keyboard: select what is not selected, confirm what is
    if (i === at && index === points.length - 1) confirm();
    else select(i);
    return undefined;
  }
  if (event.target.closest('#flyout')) return undefined;
  dom.flyout.hidden = true;
  if (event.target.closest('.piece')) return interrogate(event);
  return undefined;
}

async function start() {
  for (const id of ['banners', 'seed', 'input', 'submit', 'reading', 'stack',
    'above', 'below', 'band', 'margin', 'flyout', 'refuse', 'chunk',
    'chunkValue']) {
    dom[id] = document.getElementById(id);
  }

  dom.chunk.value = String(START);
  dom.chunk.addEventListener('input', (e) => chunkChanged(Number(e.target.value)));
  dom.chunkValue.textContent = String(state.chunk);
  dom.submit.addEventListener('click', submitSeed);
  document.addEventListener('keydown', keys);
  // our own writes are `replaceState` and do not fire this; a pasted or edited
  // address does, and moving there is what the reader asked for
  window.addEventListener('hashchange', () => {
    const to = located();
    if (!to || !state.tree) return;
    state.sliderAt = to.at;
    state.card = to.card;
    draw();
  });
  document.addEventListener('click', clicks);
  // a resize re-wraps the flow, so the clips and the band are stale in a way
  // that re-measuring fixes and re-rendering is not needed for. This is the one
  // reflow the surface allows, and the reader asked for it.
  window.addEventListener('resize', () => {
    if (state.tree) draw(false);
  });
  // a poll is text arriving rather than the reader moving, so it draws
  // without touching the viewport
  pollWhile(writes, (tree) => apply(tree, false));

  try {
    state.settings = await api.settings();
  } catch (e) {
    // every route but this one answers without a model server, so this is a
    // mode rather than a failure: the tree reads through, and nothing generates
    state.readOnly = true;
    banner(dom.banners, e instanceof Refusal && e.status === 503
      ? 'no model server is attached; reading works, generation does not'
      : String(e.message));
  }
  // the fragment is read before the first draw, so a link lands where it says
  // rather than at the tip and then jumping
  const here = located();
  if (here) {
    state.sliderAt = here.at;
    state.card = here.card;
  }
  try {
    forgetText();
    apply(await api.tree());
    remember();
  } catch (e) {
    refused(e);
  }
}

start();
