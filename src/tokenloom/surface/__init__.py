"""The reading surface: the reads it needs above the core, and the process that serves them.

`reads.py` holds segmentation, the continuation rule and the three reads `docs/SURFACE.md`
states, each standing on `core/reads.py`. `app.py` is the process -- one tree claimed for as
long as it runs, serving those reads, the five acts and the page. `wire.py` is what crosses
between them.

Nothing is re-exported here, so a call site names the module it means. `app.py` is the only
one of the three that needs Starlette, and a tree is read without it installed.
"""
