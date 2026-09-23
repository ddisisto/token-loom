/* The few DOM calls the page's panels make, and nothing more.
 *
 * Importing this installs `document` and `DocumentFragment` on the global, so it is imported
 * before the asset under test and never after. It is not a test harness for the page: there
 * is no layout, no event dispatch and no reading column here, and a check that wanted any of
 * those would be asking for a browser.
 *
 * Classes are a real set rather than a string, because what a panel says about its own state
 * is read back through `classList` -- which control is on, which row is off -- and a stub that
 * dropped that would make every such check pass.
 */

export class El {
  constructor(tag) {
    this.tag = tag;
    this.textContent = "";
    this.children = [];
    this.parentElement = null;
    this.attrs = {};
    this.style = { props: {}, setProperty: (k, v) => { this.style.props[k] = v; } };
    this._class = new Set();
    this.classList = {
      add: (...names) => { for (const n of names) if (n) this._class.add(n); },
      remove: (...names) => { for (const n of names) this._class.delete(n); },
      contains: name => this._class.has(name),
      toggle: (name, on) => {
        const want = on === undefined ? !this._class.has(name) : Boolean(on);
        if (want) this._class.add(name); else this._class.delete(name);
        return want;
      },
    };
  }

  get className() { return [...this._class].join(" "); }
  set className(value) {
    this._class = new Set(String(value ?? "").split(/\s+/).filter(Boolean));
  }

  adopt(kid) { if (kid instanceof El) kid.parentElement = this; return kid; }
  append(...kids) { for (const kid of kids) this.children.push(this.adopt(kid)); }
  prepend(...kids) { this.children.unshift(...kids.map(kid => this.adopt(kid))); }
  replaceChildren(...kids) { this.children = kids.map(kid => this.adopt(kid)); }
  setAttribute(name, value) { this.attrs[name] = value; }
  getAttribute(name) { return this.attrs[name]; }
}

export class Frag extends El {
  constructor() { super("#fragment"); }
}

/** Every string under an element, in order -- which is what a reader would see. */
export function words(item) {
  if (typeof item === "string") return item;
  if (!(item instanceof El)) return "";
  return [item.textContent, ...item.children.map(words)].filter(Boolean).join(" ");
}

globalThis.document = { createElement: tag => new El(tag) };
globalThis.DocumentFragment = Frag;
