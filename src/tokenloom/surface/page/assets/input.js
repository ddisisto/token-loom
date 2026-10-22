/* Input: the page-wide keys, the wheel, the scroll and the column's own ground, each sent to
 * the module whose gesture it is. Nothing here decides more than whose it is. */

import * as chart from "./chart.js";
import { release, step } from "./column.js";
import { author, composing, unauthor } from "./compose.js";
import * as cursor from "./cursor.js";
import { stir } from "./edge.js";
import { more, moved, quiet, ready, scrolled } from "./more.js";
import { atEnd, carrying, rebase } from "./reading.js";
import { known, waymark } from "./roots.js";
import { wrong } from "./wire.js";

const $ = id => document.getElementById(id);

/** Listen, for the rest of the page's life. */
export function listen() {
  addEventListener("scroll", () => {
    // Read before the column lets go of a height it was holding, which moves the page.
    const end = atEnd();
    // The page's own scroll is not the reader reading on.
    if (carrying()) rebase();
    else {
      chart.unheld();
      stir(true);
      scrolled(end);
    }
    chart.followed();
  }, { passive: true });

  // Already somewhere that counts, and still going down. Every way of moving the page is one
  // of these.
  addEventListener("wheel", event => {
    if (event.shiftKey && chart.look.on) return;  // the map's zoom
    // The drawer scrolls itself, and a wheel there is not the page being read further.
    if (event.target instanceof Element && event.target.closest("footer")) return;
    stir(true);
    moved(event.deltaY > 0 && ready());
  }, { passive: true });

  addEventListener("keydown", event => {
    // A composer is an editable that is not a form control, so this is wider than the two tags.
    if (event.target.closest("textarea, input, [contenteditable]")) return;
    // Typing at the caret. **A modifier on the draw key and not a key of its own**: both write
    // at the caret, and the pair reads as *draw here* and *write here* rather than as two
    // unrelated keys. It is also what the composer sends with, so the gesture that opens one is
    // the gesture that finishes it.
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)
        && !event.altKey && !event.shiftKey) {
      if (event.repeat) return;
      event.preventDefault();
      author();
      return;
    }
    // A variation at the caret, which is the draw that does not move the reader. **It is a key
    // and not a scroll because it has no place to be arrived at.** What makes the scroll
    // deliberate is the end of the page, and what makes an armed caret deliberate is the click
    // that armed it; a draw at a position in the middle of the text has neither, so the gesture
    // itself is what has to be unmistakable. A modifier on it is some other gesture rather than
    // a quieter version of this one, and a held key is one request because `quiet` says so.
    if (event.key === "Enter") {
      if (event.repeat || event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) return;
      if (event.target.closest("button, a")) return;  // Enter there is that control's own
      event.preventDefault();
      if (Date.now() < quiet) return;
      more(cursor.node(), { pin: true }).catch(() => {});
      return;
    }
    // The way back to the tip, which is what makes the scroll gesture reachable again. It writes
    // nothing and arms nothing: a reader standing at the tip has the foot of the page for that.
    //
    // An open composer takes it first, and this is where that has to be heard: a reader who
    // clicked away from the box still has one open, and the key that leaves it cannot be one
    // only the box hears. The caret has not moved while it was open, so the release that would
    // have happened here is still there on the next press.
    if (event.key === "Escape") {
      if (composing()) unauthor(); else release();
      stir();
      return;
    }
    // A waypoint at the caret, or the one there cleared.
    if (event.key === "w" && !event.ctrlKey && !event.metaKey && !event.altKey) {
      if (event.repeat || cursor.node() === null || known === null) return;
      event.preventDefault();
      waymark(cursor.node()).catch(wrong);
      return;
    }
    // The caret a segment along, which reaches a token that spells nothing as well as any other.
    if ((event.key === "ArrowLeft" || event.key === "ArrowRight")
        && !event.ctrlKey && !event.metaKey && !event.altKey && !event.shiftKey) {
      event.preventDefault();
      step(event.key === "ArrowLeft" ? -1 : 1);
      return;
    }
    // Across the map to the next branch over: left and right where it runs down the page, up
    // and down where it runs across.
    if (event.ctrlKey && !event.metaKey && !event.altKey && !event.shiftKey && chart.look.on) {
      const by = (chart.look.down ? { ArrowLeft: -1, ArrowRight: 1 }
        : { ArrowUp: -1, ArrowDown: 1 })[event.key];
      if (by !== undefined) {
        event.preventDefault();
        chart.scanBy(by);
        return;
      }
    }
    if (!["ArrowDown", "PageDown", "End", " ", "ArrowUp", "PageUp", "Home"].includes(event.key))
      return;
    moved(["ArrowDown", "PageDown", "End", " "].includes(event.key) && ready());
  });

  addEventListener("resize", () => chart.sketch());

  // Shift and the wheel zoom the map, wherever the pointer is, and do nothing else: not the
  // draw a wheel at the end of the column asks for, nor the sideways scroll some browsers make
  // of it, nor the browser's own zoom with Ctrl, which scans across instead.
  addEventListener("wheel", event => {
    if (!event.shiftKey || !chart.live()) return;
    event.preventDefault();
    chart.wheel(event);
  }, { passive: false });

  // The column's own ground is the map's: the scale, the thumb, and the strands under it.
  const column = $("column");
  column.addEventListener("pointerdown", chart.pressed);
  column.addEventListener("pointerup", event => {
    // The caret follows the window, as it does after any scroll, and nothing is asked for.
    if (chart.lifted(event)) moved(false);
  });
  column.addEventListener("pointerleave", () => chart.hover(null));
  column.addEventListener("pointermove", chart.pointed);

  /* A click there is an arrival on the map where it points at one, and otherwise the same
   * release as Escape, spelled where the reader's hand already is. **Two boxes and not a rule
   * about what to ignore**: the column's own and the text's, which are where there is nothing.
   * Everything else in here -- a segment, a row, a boundary's control, the composer -- is a
   * click that already means something, and naming those instead would be a list that goes
   * stale as they are added. */
  column.onclick = event => {
    const on = event.target;
    if (on === column && chart.charting(event)) return;
    if (on === column || on.classList?.contains("flow")) release();
  };
}
