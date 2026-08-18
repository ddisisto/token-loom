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
import { banner, cardStrip, place, renderFlow, renderMargin } from './surface.mjs';

/** The stops on the chunk slider, in tokens.
 *
 * The one generation parameter the surface exposes, because its effect is
 * pacing rather than behaviour, and pacing is a reader's business. Each value
 * interns as its own parameter set, so a tree records where its reader changed
 * pace -- which is interning working as intended.
 */
const CHUNKS = [8, 16, 32, 64, 96];
const START = 2;

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
  growing: false,
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
  if (!points.length) {
    return { points, index: -1, fork: null, card: 0, chosen: false };
  }
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
    // whether the path continues past this fork. Normally false at the last
    // fork, because generation attaches its alternatives at the tip -- but an
    // authored tree, or one whose tip was deleted, ends past its last fork,
    // and then there is nothing here to confirm.
    chosen: fork.active >= 0,
  };
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

/** Apply a whole-tree response. The response *is* the new state. */
function apply(tree) {
  state.tree = tree;
  draw();
}

function settingsNow() {
  return { ...state.settings, length: state.chunk };
}

function generate(at, n) {
  if (state.readOnly) {
    banner(dom.banners, 'no model server is attached, so nothing can be '
      + 'generated; the tree still reads');
    return;
  }
  writes.submit(async () => {
    apply(await api.generate(at, n, settingsNow()));
  }, refused);
}

// -- the acts --------------------------------------------------------------

/** Confirm the selected card: it joins the path, and the tip moves onto it. */
function confirm() {
  const { fork, card, chosen } = slider();
  if (!fork || chosen) return;
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

/** Move the selection. Behind the tip, moving *is* re-routing. */
function select(index) {
  const { fork, chosen } = slider();
  if (!fork || index < 0 || index >= fork.children.length) return;
  state.card = index;
  // nothing has been chosen at this fork yet, so selecting is only a pick
  if (!chosen) return draw();
  if (index === fork.active) return draw();            // already on the path

  const to = resumeInto(fork.children[index]);
  state.sliderAt = fork.at;
  writes.submit(async () => {
    apply(await api.cursor(to));
    remember();
  }, refused);
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
  if (!fork || writes.busy || state.readOnly) return;
  const last = fork.children[fork.children.length - 1];
  if (nodeState(state.tree, last) !== 'ready') return;
  state.growing = true;
  generate(fork.at, 1);
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

function draw() {
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

  let { points, index, fork, card, chosen } = slider();
  const atTip = index === points.length - 1;

  if (fork && state.growing) {
    // the card asked for has arrived, so move onto it as the reader intended
    const arrived = fork.children.length - 1;
    if (arrived > card) {
      state.card = arrived;
      card = arrived;
      state.growing = false;
    }
  }

  const strip = cardStrip(state.tree, fork, card, {
    growable: Boolean(fork) && atTip && !chosen && !state.readOnly
      && card === fork.children.length - 1
      && nodeState(state.tree, fork.children[card]) === 'ready',
  });

  // one flow, laid out once and drawn twice: the clone is a copy of the
  // finished layout rather than a second render, which is what guarantees the
  // two halves tile rather than merely agree
  renderFlow(dom.above, state.tree);
  dom.below.replaceChildren(
    ...[...dom.above.childNodes].map((n) => n.cloneNode(true)));
  dom.band.replaceChildren(...(strip ? [strip] : []));

  // the cross-section is behind the tip when the reader has come back to an
  // earlier fork, and what lies past it is dimmed rather than removed
  const shift = place(dom, index, { muted: !atTip });
  renderMargin(dom.margin, dom.above, points, index, shift);
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
  const { fork, index, points, card, chosen } = slider();
  if (!fork) return;
  if (event.key === 'ArrowLeft') { select(card - 1); }
  else if (event.key === 'ArrowRight') {
    if (card + 1 < fork.children.length) select(card + 1);
    else if (index === points.length - 1) grow();
  } else if (event.key === 'ArrowUp') { back(); }
  else if (event.key === 'ArrowDown' || event.key === 'Enter') {
    // down is always towards the tip. At the last fork that means confirming
    // what is selected -- unless the path already runs past it, where there is
    // nothing to confirm and nowhere further forward to go.
    if (index === points.length - 1) { if (!chosen) confirm(); }
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
    const { index, points, card: at, chosen } = slider();
    // a mouse reader does in two clicks what arrow-then-down does from the
    // keyboard: select what is not selected, confirm what is
    if (i === at && index === points.length - 1 && !chosen) confirm();
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
  document.addEventListener('click', clicks);
  // a resize re-wraps the flow, so the clips and the band are stale in a way
  // that re-measuring fixes and re-rendering is not needed for. This is the one
  // reflow the surface allows, and the reader asked for it.
  window.addEventListener('resize', () => {
    if (state.tree) draw();
  });
  pollWhile(writes, apply);

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
  try {
    forgetText();
    apply(await api.tree());
    remember();
  } catch (e) {
    refused(e);
  }
}

start();
