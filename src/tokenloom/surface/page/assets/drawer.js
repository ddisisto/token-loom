/* The footer, and the drawer in it. Hovering it lifts the drawer over the text after a beat,
 * and leaving lets it fall after another, so passing over it does neither; the heat rides its
 * top edge, and a pointer on it keeps the drawer up without lifting it. Dragged up by the heat,
 * the drawer is held at whatever height it was let go and takes that room from the text, which
 * is `--foot`; how high the footer reaches either way is `--lid`. `room.js` has where it rests.
 */

import { along, draw, place, set, share } from "./draw.js";
import * as room from "./room.js";

export const foot = document.querySelector("footer");
const drawer = document.getElementById("drawer");
const LIFT = 120, FALL = 300;  // ms
const NEAR = 32;  // px either side of the drawer's panel a pointer on the footer lifts it from
let over = 0;   // how many of the footer and the heat the pointer is on
let lifting = null;
let rising = null;  // a lift waiting on the pointer staying near the drawer
let held = 0;   // px the drawer is held open at; 0 is shut

/** How tall the drawer is with everything in it showing, held to most of the screen. */
const full = () => Math.min(drawer.scrollHeight, window.innerHeight * 0.6);

function measure() {
  const root = document.documentElement.style;
  root.setProperty("--foot", `${foot.offsetHeight}px`);
  const floating = foot.classList.contains("peek") && held === 0;
  root.setProperty("--lid", `${foot.offsetHeight + (floating ? drawer.offsetHeight : 0)}px`);
}

function hold(px) {
  held = Math.round(px);
  foot.classList.toggle("held", held > 0);
  if (held > 0) foot.classList.remove("peek");
  foot.style.setProperty("--held", `${held}px`);
  measure();
}

function lift(up) {
  clearTimeout(lifting);
  // A line in the hand keeps it up, wherever the pointer has wandered while holding it.
  if (!up && drawer.querySelector(".moving")) {
    lifting = setTimeout(() => lift(false), FALL);
    return;
  }
  foot.classList.toggle("peek", up && held === 0);
  measure();
}

/** The pointer arrived on something that keeps the drawer up. */
function arrive() {
  over++;
  clearTimeout(lifting);
}
function depart() {
  over = Math.max(0, over - 1);
  clearTimeout(lifting);
  if (over === 0 && foot.classList.contains("peek")) lifting = setTimeout(() => lift(false), FALL);
}
/** Lift the drawer after a beat while the pointer on the footer is across from its panel, and
 *  not while it is anywhere else along the footer. */
function aim(event) {
  const panel = drawer.querySelector(".panel")?.getBoundingClientRect();
  const near = panel && event.clientX >= panel.left - NEAR && event.clientX <= panel.right + NEAR;
  if (!near || held > 0 || foot.classList.contains("peek")) {
    clearTimeout(rising);
    rising = null;
    return;
  }
  if (rising === null) rising = setTimeout(() => { rising = null; lift(true); }, LIFT);
}

/* The heat of a draw, set along a line across the column at the footer's top. Its range and
 * steps are the draw panel's, read through `along` and `share`. */
const heat = Object.assign(document.createElement("div"), { id: "heat" });
const track = Object.assign(document.createElement("div"), { className: "track" });
const warmth = Object.assign(document.createElement("div"), { className: "point" });
const heatSays = Object.assign(document.createElement("span"), { className: "says" });
const gripper = Object.assign(document.createElement("div"), {
  className: "grip", title: "drag up for the rest of the draw, or click" });

/** Where along the heat each of the stylesheet's colours stands. */
const GLOW = [[0, "--heat-0"], [1, "--heat-1"], [2, "--heat-2"], [along("temperature", 1), "--heat-3"]];

/** The colour a heat is drawn in: mixed between the two stops either side of it. */
function glow(t) {
  const i = Math.max(0, GLOW.findLastIndex(([at]) => at <= t));
  const [a, from] = GLOW[Math.min(i, GLOW.length - 2)];
  const [b, to] = GLOW[Math.min(i + 1, GLOW.length - 1)];
  const p = Math.min(1, Math.max(0, (t - a) / (b - a)));
  return `color-mix(in oklab, var(${from}), var(${to}) ${(p * 100).toFixed(1)}%)`;
}

function heated() {
  heat.style.setProperty("--x", String(share("temperature")));
  const { temperature } = draw();
  heat.style.setProperty("--glow", glow(temperature));
  heatSays.textContent = temperature === 0 ? "greedy" : `heat ${temperature.toFixed(2)}`;
}

/* A drag on the heat sets the heat, until it has gone far enough up or down to be the
 * drawer's -- and then the heat goes back to where the drag found it, since a hand reaching
 * for the drawer was not setting it. A drag from the grip is only ever the drawer's, and a
 * grip let go without moving it opens the drawer, or shuts one that is open. */
let grip = null;  // { y, from, heat, drawer, bare }
const toward = event => {
  const box = track.getBoundingClientRect();
  place("temperature", (event.clientX - box.left) / box.width);
  heated();
};

/** Watch the footer, and put the heat on the page. */
export function mount() {
  new ResizeObserver(measure).observe(foot);
  new ResizeObserver(measure).observe(drawer);
  foot.addEventListener("pointerenter", event => { arrive(); aim(event); });
  foot.addEventListener("pointermove", aim);
  foot.addEventListener("pointerleave", () => {
    clearTimeout(rising);
    rising = null;
    depart();
  });

  track.append(warmth, heatSays);
  heat.append(track, gripper);
  document.querySelector("main").append(heat);
  heat.style.setProperty("--scale", `linear-gradient(to right, ${GLOW.map(([t, c]) =>
    `var(${c}) ${(t / GLOW.at(-1)[0] * 100).toFixed(1)}%`).join(", ")})`);

  heat.addEventListener("pointerdown", event => {
    if (event.button !== 0) return;
    event.preventDefault();
    heat.setPointerCapture(event.pointerId);
    // A drawer lifted by hovering is the height it shows, so a drag starts from there.
    const from = held > 0 ? held : foot.classList.contains("peek") ? drawer.offsetHeight : 0;
    const bare = event.target === gripper;
    grip = { y: event.clientY, from, heat: draw().temperature, drawer: false, bare };
    heat.classList.add(bare ? "lifting" : "moving");
    if (!bare) toward(event);
  });
  heat.addEventListener("pointermove", event => {
    if (grip === null) return;
    const to = room.pulled(grip.from, grip.y - event.clientY, full());
    if (to === null && !grip.drawer) return grip.bare ? undefined : toward(event);
    if (!grip.drawer) {
      grip.drawer = true;
      set("temperature", grip.heat);
      heated();
    }
    hold(to ?? grip.from);
  });
  heat.addEventListener("pointerenter", () => arrive());
  heat.addEventListener("pointerleave", depart);
  for (const end of ["pointerup", "pointercancel"]) {
    heat.addEventListener(end, () => {
      if (grip?.drawer) hold(room.rests(held, full()));
      else if (grip?.bare) hold(held > 0 ? 0 : full());
      grip = null;
      heat.classList.remove("moving", "lifting");
    });
  }
  heated();
}
