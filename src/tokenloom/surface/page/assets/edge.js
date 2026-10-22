/* The length of a draw is set at the page's edge, as the room below the last line, and
 * `room.js` has what each position means. Room is a share of the height above the footer, so
 * a drawer held up shortens the edge and keeps every position where it was learned. Parked, a
 * scroll draws nothing and the length is left where it was, so the key that draws at the caret
 * still has one. */

import * as cursor from "./cursor.js";
import { draw, set } from "./draw.js";
import { foot } from "./drawer.js";
import { rebase, working } from "./reading.js";
import * as room from "./room.js";

export let parked = false;
export let shifting = false;  // the point in the hand

const edge = Object.assign(document.createElement("div"), { id: "edge" });
const says = Object.assign(document.createElement("span"), { className: "says" });
const handle = Object.assign(document.createElement("div"), { className: "point" });
const counter = Object.assign(document.createElement("div"), { className: "counter" });

function stand(asked) {
  const at = room.place(asked);
  parked = at.length === null;
  if (!parked) set("length", at.length);
  document.getElementById("column").style.setProperty(
    "--space", `calc((100vh - var(--foot)) * ${at.room / 100})`);
  edge.style.setProperty("--room", `${at.room}%`);
  edge.classList.toggle("parked", parked);
  says.textContent = parked ? "parked" : `${at.length} tokens`;
  stir();
}

/* The cue: how near the next scroll is to drawing, drawn as a counter-point at the last
 * line's height that pulses against the point and meets it at the mark. `room.cue` decides what
 * is shown; this only paints it, and runs a frame loop only while something is moving. */

let stirred = -Infinity;  // when the page last moved
let hovering = false;
let phase = 0;
let frame = null;
let then = 0;
export const still = matchMedia("(prefers-reduced-motion: reduce)");

/** How far below the mark the last line stands, in the room's units: what is left to scroll. */
const gap = () => Math.max(0,
  (document.documentElement.scrollHeight - window.scrollY - window.innerHeight)
  / Math.max(1, window.innerHeight - foot.offsetHeight) * 100);

function beat(now) {
  const c = room.cue({ gap: gap(), since: now - stirred, hover: hovering,
                       armed: cursor.armed(), parked });
  edge.classList.toggle("cued", c !== null && (c.near || hovering));
  edge.classList.toggle("close", c !== null && c.close);
  if (c === null) {
    counter.style.opacity = "0";
    handle.style.opacity = "";
    return false;
  }
  phase = (phase + c.rate * (now - then) / 1000) % 1;
  // Solid while a draw is in flight: the gesture has been made and there is nothing to warn of.
  const depth = still.matches || working ? 0 : c.pulse;
  // The two in opposite phase, so one is brightest where the other is faintest.
  const wave = 0.5 - 0.5 * Math.cos(2 * Math.PI * phase);
  edge.style.setProperty("--gap", `${c.gap}%`);
  handle.style.opacity = String(1 - 0.65 * depth * wave);
  counter.style.opacity = String(1 - 0.65 * depth * (1 - wave));
  // A frame is wanted while there is a pulse to run or a fade still under way.
  return depth > 0 || hovering || now - stirred < room.FADE;
}

function tick(now) {
  const going = beat(now);
  then = now;
  frame = going ? requestAnimationFrame(tick) : null;
}

/** Something moved: start the loop if it is not running. */
export function stir(moving = false) {
  if (moving) stirred = performance.now();
  if (frame === null) {
    then = performance.now();
    frame = requestAnimationFrame(tick);
  }
}

// A share of the edge's own height, above its foot, which is the footer's top.
const asked = event => {
  const box = edge.getBoundingClientRect();
  return (box.bottom - event.clientY) / box.height * 100;
};

function letGo() {
  if (!shifting) return;
  shifting = false;
  edge.classList.remove("moving");
  // Where the page's end went is not somewhere the reader scrolled to, so it is taken as the
  // place to start from once the scroll the move caused has been heard.
  requestAnimationFrame(rebase);
}

/** Put the edge on the page, standing at the room the draw's length asks for. */
export function mount() {
  edge.append(counter, handle,
              Object.assign(document.createElement("div"), { className: "across" }), says);
  // In `main`, so the measure it is placed by is read against what the column is.
  document.querySelector("main").append(edge);
  edge.addEventListener("pointerenter", () => { hovering = true; stir(); });
  edge.addEventListener("pointerleave", () => { hovering = false; stir(); });
  edge.addEventListener("pointerdown", event => {
    if (event.button !== 0) return;
    event.preventDefault();
    edge.setPointerCapture(event.pointerId);
    shifting = true;
    edge.classList.add("moving");
    stand(asked(event));
  });
  edge.addEventListener("pointermove", event => { if (shifting) stand(asked(event)); });
  edge.addEventListener("pointerup", letGo);
  edge.addEventListener("pointercancel", letGo);
  stand(room.roomFor(draw().length));
}
