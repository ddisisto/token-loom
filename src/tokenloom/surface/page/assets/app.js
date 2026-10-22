/* The surface: a list of roots, a reading column, and the one composer both of them use. This
 * is its startup: what goes on the page in what order, the ways of looking in the panel, and
 * the first read.
 *
 * Nothing here is remembered between loads but the reader's waypoints, which `waypoint.js`
 * keeps. Reader state lives in the session, and what is live, what parts and what a ranking
 * holds are read from the store every time.
 */

import * as chart from "./chart.js";
import * as cursor from "./cursor.js";
import { panel } from "./draw.js";
import * as drawer from "./drawer.js";
import * as edge from "./edge.js";
import { listen } from "./input.js";
import * as mark from "./mark.js";
import * as more from "./more.js";
import { panel as overlayPanel } from "./overlay.js";
import * as ranking from "./ranking.js";
import { ended, pathEnd, relaid, seeHidden, show } from "./reading.js";
import { live, refresh } from "./roots.js";
import { margin } from "./rows.js";
import { stage } from "./compose.js";
import { wrong } from "./wire.js";

const $ = id => document.getElementById(id);

more.mount();
listen();
$("drawer").append(panel());
edge.mount();
drawer.mount();

$("read").append(overlayPanel(relaid));

/* One state for the whole page, so the roots and the column always say the same thing about
 * what has been set aside. Flipping it re-reads rather than filtering what is already drawn:
 * the column's hidden tail is not in the response until it is asked for. */
$("hidden").onchange = async () => {
  seeHidden($("hidden").checked);
  try {
    await refresh();
    if (pathEnd() !== null) await show(pathEnd());
  } catch (why) {
    wrong(why);
  }
};

/* Whether who took each token is marked. Default on, and a way of looking like the two
 * above: it records nothing and changes no text. Flipping it re-reads, because the sampler's
 * half of the mark needs the ranking and a read made without it did not carry one. */
$("taker").onchange = async () => {
  mark.want($("taker").checked);
  const here = cursor.node();
  try {
    if (here !== null) await show(pathEnd(), here);
  } catch (why) {
    wrong(why);
  }
};

/* Whether what else was live is shown. A way of looking, like what is set aside: it records
 * nothing, and it asks for nothing until it is on -- a position can run to dozens of rows,
 * and `docs/SURFACE.md` has density staying behind intent. */
$("rows").onchange = () => margin();

$("charted").onchange = () => {
  chart.mapped($("charted").checked);
  margin();
  chart.charter();
};

$("fold").onclick = () => {
  const folded = document.body.classList.toggle("folded");
  $("fold").setAttribute("aria-pressed", String(folded));
};

try {
  // A reload restores a checkbox in some browsers, and nothing here is remembered between
  // loads -- so what the box says is what the page believes, rather than the other way.
  seeHidden($("hidden").checked);
  chart.mapped($("charted").checked);
  ranking.want($("rows").checked);
  const tree = await refresh();
  // With nothing yet chosen the first root is what is read; with no roots at all the page
  // is never a bare one, because the only thing to do here is the only thing offered.
  const rows = live(tree);
  if (!rows.length) stage(null);
  else {
    await show(rows[0].id);
    // Something another page started, or this one was reloaded out from under.
    if (await more.resume()) {
      await refresh();
      await show(cursor.node());
    }
  }
  ended();
} catch (why) {
  wrong(why);
}
