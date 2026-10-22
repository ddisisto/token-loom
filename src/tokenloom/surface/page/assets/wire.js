/* The wire: what the page asks the server, and the status line it answers on. */

const $ = id => document.getElementById(id);

export class Fault extends Error {
  constructor(kind, message) { super(message); this.kind = kind; }
}

export async function ask(path, body) {
  const answer = await fetch(path, body === undefined ? {} : {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  // A server that fell over before it could phrase an answer sends no JSON at all, and
  // reading it as JSON would report the parse rather than the fault.
  const shape = await answer.json().catch(() => null);
  // A fault says which kind it was because the record does: a refusal and a rejection are
  // answers about the request, and only a failure is worth repeating unchanged.
  if (!answer.ok) {
    throw new Fault(shape?.error || "error", shape?.message || answer.statusText);
  }
  if (shape === null) throw new Fault("error", "the server sent something that is not JSON");
  return shape;
}

/** Ask for a draw, and treat one that broke as the fault it is.
 *
 *  **A `generate` that failed is an act, and it comes back as one.** The record keeps it with
 *  terminator `failed` and no nodes, so the route answers it as made -- and a caller reading
 *  only that something was made would ask again, at the same place, for the same thing. Only
 *  a refusal is turned into a fault on the server, being an answer about the request; the rest
 *  of the ways a draw writes nothing are turned into one here. An `eos` with nothing before it
 *  is an answer and not a fault, and comes back as made.
 */
export async function generated(body) {
  const act = await ask("/generate", body);
  if (["failed", "cancelled", "aborted"].includes(act.terminator)) {
    throw new Fault(act.terminator, `act ${act.id} wrote nothing: the draw ${act.terminator}`);
  }
  return act;
}

export function say(text, bad) {
  $("status").textContent = text;
  $("status").className = bad ? "fault" : "";
}

/** Say what went wrong, in the status line, as a fault. */
export const wrong = why => say(`${why.kind || "unreachable"}: ${why.message}`, true);
