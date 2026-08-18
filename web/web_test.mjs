// The client's derivations, checked without a browser.
//
//     node web/web_test.mjs
//
// The fourth executable check beside `core_test.py`, `api_test.py` and
// `llama_test.py`, and the same shape: a script that prints what it asserted
// and why. No runner, no dependencies, no build step -- node has run ES modules
// natively for years and `web/path.mjs` is the same file the browser loads.
//
// It exists because `path.mjs` is entirely derived values, and `CLAUDE.md`'s
// rule for those is that ordinary use will not reach them: a byte/string
// mismatch shows up as one character of drift in a flyout, and picking the
// wrong child at a counterfactual fork shows up as text that is subtly not
// what the reader chose. Neither announces itself.
//
// Fixtures come from `web/fixtures.py`, so they are what `wire.tree_json`
// actually produces rather than what this file's author believed it produces.
// The expectations come from the core as well -- `expect.path` is
// `Tree.path_bytes` -- which is what keeps the arithmetic here from being the
// thing under test.

import { execFileSync } from 'node:child_process';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  activePath, ancestry, byteOffset, continues, forks, forget, indexed,
  leaving, nodeState, nodeText, pieceText, stringIndex, textOf, unrenderable,
} from './path.mjs';

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));

let passed = 0;
let failed = 0;

function check(what, ok, detail) {
  if (ok) {
    passed++;
    console.log(`  ok    ${what}`);
  } else {
    failed++;
    console.log(`  FAIL  ${what}${detail === undefined ? '' : `  -- ${detail}`}`);
  }
}

function load() {
  const raw = execFileSync('uv', ['run', 'python', 'web/fixtures.py'],
    { cwd: ROOT, encoding: 'utf8', maxBuffer: 32 * 1024 * 1024 });
  return JSON.parse(raw);
}

/** The whole active path as the client assembles it, piece by piece. */
function assembled(tree) {
  return activePath(tree).flatMap((n) => n.pieces)
    .map((p) => pieceText(tree, p)).join('');
}

// -- the conversion --------------------------------------------------------

function conversion(cases) {
  console.log('\nbytes and string indices, which are not the same number');
  forget();
  const tree = cases.wide.tree;

  const seed = textOf(tree, 's0');
  const enc = new TextEncoder();
  check('a span counts its own bytes the way the encoder does',
    seed.bytes === enc.encode(seed.text).length,
    `${seed.bytes} vs ${enc.encode(seed.text).length}`);
  check('and that is not the number of units the string is long',
    seed.bytes > seed.text.length,
    `${seed.bytes} bytes, ${seed.text.length} units`);

  // 'Le phare — gardien du détroit 🜁': the em dash is 3 bytes and 1 unit, the
  // accented e is 2 and 1, the astral glyph 4 and 2. Computed, not eyeballed:
  // the encoder is the authority on its own lengths.
  const drift = [...seed.text].map((ch, i) => [i, ch]).filter(
    ([, ch]) => enc.encode(ch).length !== ch.length);
  check('and they part company on every character that is not one byte',
    drift.length === 3 && drift.map(([, c]) => c).join('') === '—é🜁',
    JSON.stringify(drift));

  let roundTrips = true;
  let interior = 0;
  for (let b = 0; b <= seed.bytes; b++) {
    const s = seed.strAt[b];
    if (seed.byteAt[s] === b) continue;
    interior++;
    // an interior byte answers with the start of its own character, which is
    // the only answer that keeps a click inside an emoji from landing outside
    if (seed.byteAt[s] > b || seed.strAt[seed.byteAt[s]] !== s) roundTrips = false;
  }
  check('every character boundary survives the trip both ways',
    roundTrips, 'an interior byte mapped outside its own character');
  // every character contributes one boundary byte and the rest are interior,
  // so this is the byte count less the code point count -- derived rather than
  // counted by eye, which is how the first two attempts at this line were wrong
  check('and interior bytes are the only ones that do not, one per extra byte',
    interior === seed.bytes - [...seed.text].length,
    `${interior} vs ${seed.bytes - [...seed.text].length}`);

  const empty = indexed('');
  check('an empty string is still addressable at its one offset',
    empty.bytes === 0 && empty.strAt[0] === 0 && empty.byteAt[0] === 0);

  // the round trip through the tree's own accessors, which is what the flyout
  // and the click handler each use one half of
  const at = seed.text.indexOf('🜁');
  check('a click resolves to a byte offset and back to where it was',
    stringIndex(tree, 's0', byteOffset(tree, 's0', at)) === at,
    `${at} -> ${byteOffset(tree, 's0', at)}`);
}

// -- the path --------------------------------------------------------------

function paths(cases) {
  console.log('\nthe active path, against what the core says it is');
  for (const [name, { tree, expect }] of Object.entries(cases)) {
    forget();
    if (expect.path === null) {
      check(`${name}: the core cannot spell this path, so nothing is asserted`,
        unrenderable(tree).length > 0, JSON.stringify(unrenderable(tree)));
      continue;
    }
    const built = assembled(tree);
    check(`${name}: the pieces assemble into exactly the path`,
      built === expect.path, `${JSON.stringify(built)} vs ${JSON.stringify(expect.path)}`);
    check(`${name}: and into the byte count the core recorded`,
      new TextEncoder().encode(built).length === expect.bytes,
      `${new TextEncoder().encode(built).length} vs ${expect.bytes}`);
  }

  forget();
  const tree = cases.plain.tree;
  const chain = ancestry(tree, tree.selected);
  check('the ancestry is one entry per span, root first',
    chain.map((p) => p.span).join(',') === 's0,s1', JSON.stringify(chain));
  check('and each entry says where the path leaves that span',
    chain[0].offset === tree.spans.s0.length
    && chain[1].offset === tree.spans.s1.length, JSON.stringify(chain));
}

// -- the case span identity cannot decide ----------------------------------

function ambiguous(cases) {
  console.log('\nwhich child of a fork the path took');
  forget();
  const { tree, expect } = cases.counterfactual;

  const onPath = new Set(ancestry(tree, tree.selected).map((p) => p.span));
  const fork = forks(tree)[0];
  const named = fork.children.map((c) => c.pieces[0].span);

  // the trap, stated before the assertion that avoids it: both children of
  // this fork name a span the path passes through, so a client that decides by
  // span identity has nothing to decide with
  check('both children of the fork name spans that are on the path',
    named.every((s) => onPath.has(s)) && new Set(named).size === 2,
    `${JSON.stringify(named)} against ${JSON.stringify([...onPath])}`);
  check('and they are told apart by bytes: the remainder starts where the '
    + 'path left',
    fork.children[fork.active].pieces[0].begin === 0
    && fork.children[1 - fork.active].pieces[0].begin
      === ancestry(tree, tree.selected).find((p) => p.span === 's1').offset,
    JSON.stringify(fork.children.map((c) => c.pieces[0])));

  // Uniqueness rather than position, and the difference is the whole check.
  // `outline` appends the resuming branch last, so "the first child whose span
  // is on the path" gets the right answer on every tree it builds -- and
  // passed every other assertion in this file when it was tried. Nothing on
  // the wire promises that order, so what has to hold is that one child
  // qualifies and the other does not.
  const where = leaving(tree);
  const matching = fork.children.filter((c) => continues(c, where));
  check('exactly one child qualifies, so the choice does not rest on order',
    matching.length === 1 && matching[0] === fork.children[fork.active],
    `${matching.length} of ${fork.children.length} qualified`);
  check('and it still qualifies alone when the children arrive reversed',
    [...fork.children].reverse().filter((c) => continues(c, where)).length === 1);
  check('so the path ends on the counterfactual, not on the span it left',
    assembled(tree) === expect.path && expect.path.endsWith(' bright'),
    JSON.stringify(assembled(tree)));
}

// -- forks and cards -------------------------------------------------------

function slider(cases) {
  console.log('\nwhat the margin and the card slider are handed');
  forget();
  const tree = cases.plain.tree;
  const found = forks(tree);

  check('a fork behind the reader knows which way was taken, of how many',
    found[0].active === 0 && found[0].children.length === 2,
    JSON.stringify(found.map((f) => [f.active, f.children.length])));
  check('and the chip reads as the position it is, one-based',
    `⑂${found[0].active + 1}/${found[0].children.length}` === '⑂1/2');
  check('the tip is the same structure with nothing chosen yet',
    found[found.length - 1].active === -1
    && found[found.length - 1].children.length === 2,
    JSON.stringify(found[found.length - 1].active));
  check('a fork names the position a generation from it would attach at',
    found[found.length - 1].at.span === 's1'
    && found[found.length - 1].at.offset === tree.spans.s1.length,
    JSON.stringify(found[found.length - 1].at));
  check('and the cards read as the continuations they are',
    found[found.length - 1].children.map((c) => nodeText(tree, c)).join('|')
    === ' was calm| was rough',
    JSON.stringify(found[found.length - 1].children.map((c) => nodeText(tree, c))));

  console.log('\nthe two ways a card can have no text');
  forget();
  const flight = cases.flight.tree;
  const tip = forks(flight)[0];
  check('a batch of three is three cards, however far along it is',
    tip.children.length === 3, JSON.stringify(tip.children.length));
  check('and they are told apart: landed, still running, produced nothing',
    tip.children.map((c) => nodeState(flight, c)).join(',')
    === 'ready,flight,empty',
    JSON.stringify(tip.children.map((c) => nodeState(flight, c))));
  check('the one still running is the one the core says is in flight',
    tip.children.filter((c) => nodeState(flight, c) === 'flight')
      .map((c) => c.pieces[0].span).join(',') === cases.flight.expect.flight.join(','),
    JSON.stringify(cases.flight.expect.flight));
}

// -- the refusal -----------------------------------------------------------

function refusal(cases) {
  console.log('\nbytes with no string form, which are refused rather than drawn');
  forget();
  check('a tree holding one is named, span by span',
    unrenderable(cases.fragment.tree).length === 1
    && unrenderable(cases.fragment.tree)[0] === 's2',
    JSON.stringify(unrenderable(cases.fragment.tree)));
  check('and every tree that does not hold one says so',
    ['plain', 'flight', 'counterfactual', 'wide']
      .every((n) => unrenderable(cases[n].tree).length === 0));
  check('a span in flight is not one of these, having no bytes rather than '
    + 'unspellable ones',
    unrenderable(cases.flight.tree).length === 0
    && cases.flight.tree.spans.s2.text === null);
}

// -- main ------------------------------------------------------------------

const cases = load();
conversion(cases);
paths(cases);
ambiguous(cases);
slider(cases);
refusal(cases);

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
