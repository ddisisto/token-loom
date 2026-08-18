// The wire, and the one rule about who may be talking on it.
//
// Every mutation answers with the whole tree, so nothing here merges or
// patches: a response replaces what the client held. `FRONTEND.md` constraint 8
// is the reason that is affordable -- the client issues every mutation, so it
// already knows what changed, and the response is the new source of truth
// rather than a description of the change.

/** A refusal the server made, carrying its own message.
 *
 * `FRONTEND.md` constraint 12: these reach the reader as themselves. Nothing
 * here retries, and nothing translates a message into a friendlier one --
 * "1025 prompt tokens do not fit a context of 512" is the sentence that tells
 * a reader what to do, and any paraphrase of it says less.
 */
export class Refusal extends Error {
  constructor(status, detail) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

async function send(method, path, body) {
  let response;
  try {
    response = await fetch(path, {
      method,
      headers: body === undefined ? {} : { 'content-type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (cause) {
    // the server went away mid-session; the reader is owed the plain fact
    throw new Refusal(0, 'the server is not answering');
  }
  const text = await response.text();
  let parsed = null;
  try {
    parsed = text ? JSON.parse(text) : null;
  } catch {
    parsed = null;
  }
  if (!response.ok) {
    throw new Refusal(response.status,
      (parsed && parsed.detail) || `${response.status} from ${path}`);
  }
  return parsed;
}

export const api = {
  tree: () => send('GET', '/api/tree'),
  settings: () => send('GET', '/api/settings'),
  tokens: (span) => send('GET', `/api/span/${encodeURIComponent(span)}/tokens`),
  author: (at, text) => send('POST', '/api/author', { at, text }),
  generate: (at, n, settings) => send('POST', '/api/generate', { at, n, settings }),
  branch: (span, index, rank) => send('POST', '/api/branch', { span, index, rank }),
  cursor: (at) => send('PUT', '/api/cursor', { at }),
};

/** One writer, one pending slot, and reads that never queue.
 *
 * The server serialises every mutation behind one lock, including the model
 * call, so a second write sent while a generation is running would sit in a
 * socket until it finished. That is the position `FRONTEND.md` constraint 9
 * exists to keep the reader out of: a request they are waiting on must never
 * land behind one they are not.
 *
 * So writes go through here and reads do not. `GET /api/tree` runs underneath a
 * generation on purpose -- it is what fills the placeholders while a batch is
 * still arriving.
 *
 * **The pending slot holds one call and the newest wins.** Its whole job is
 * that a speculative call decided on but not yet sent is dropped when the
 * reader confirms instead: right-then-immediately-down should cost a wait only
 * where the speculative call had already started, which is the one case nothing
 * can be done about.
 */
export class Writes {
  constructor() {
    this.running = null;
    this.pending = null;
    this.watchers = new Set();
    // bumped whenever a write finishes, so a read that started earlier can
    // tell that its answer is now the older one
    this.completed = 0;
  }

  get busy() {
    return this.running !== null;
  }

  /** Called whenever the queue starts or stops running something. */
  watch(fn) {
    this.watchers.add(fn);
    return () => this.watchers.delete(fn);
  }

  announce() {
    for (const fn of this.watchers) fn(this.busy);
  }

  /** Run `fn` when the writer is free, replacing anything already waiting.
   *
   * Returns nothing. A caller that wants the result asks the tree, which is
   * what the response is anyway -- and a queued call may never run at all, so
   * a promise for its result would be a promise that can be quietly abandoned.
   */
  submit(fn, onError) {
    if (this.running) {
      this.pending = { fn, onError };
      return;
    }
    this.start(fn, onError);
  }

  start(fn, onError) {
    this.running = (async () => {
      try {
        await fn();
      } catch (e) {
        if (onError) onError(e);
      } finally {
        this.running = null;
        this.completed++;
        const next = this.pending;
        this.pending = null;
        if (next) this.start(next.fn, next.onError);
        else this.announce();
      }
    })();
    this.announce();
  }

  /** Forget anything waiting. A confirm calls this before enqueuing its own. */
  clearPending() {
    this.pending = null;
  }
}

/** Poll the tree while a write is running, so placeholders fill as they land.
 *
 * A batch saves per continuation and reads do not take the writer lock, so the
 * first card is readable while the second is still being generated. Polling is
 * how a client that cannot stream finds that out; streaming would replace this
 * and nothing else. Stops itself when the write finishes.
 */
export function pollWhile(writes, apply, ms = 400) {
  let timer = null;
  return writes.watch((busy) => {
    if (busy && timer === null) {
      timer = setInterval(async () => {
        // A poll and the write it is watching race, and the poll can lose:
        // its request may have left before the write finished and its answer
        // arrive after. Applying it then would put a stale tree on the screen
        // and leave it there, since nothing else is coming. So the answer is
        // dropped unless the same write is still running that was running when
        // it was asked for.
        const mark = writes.completed;
        try {
          const tree = await api.tree();
          if (writes.busy && writes.completed === mark) apply(tree);
        } catch {
          // a read that fails during a generation is not the reader's problem;
          // the write's own refusal is the one that gets reported
        }
      }, ms);
    } else if (!busy && timer !== null) {
      clearInterval(timer);
      timer = null;
    }
  });
}
