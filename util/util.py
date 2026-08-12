"""The four helpers anything still imports.

This was 579 lines of general-purpose Python — csv and json wrappers, ngram and diff
helpers, an FString class, list and array utilities — accumulated by the tkinter app.
With that gone, reachability from the surviving imports (`inference.py`, `web/tree.py`)
covers four functions. The other 34 went, and numpy and pandas went with them; git
holds them if any turn out to be wanted.
"""

import datetime
import functools
import json
import logging
import time
from functools import partial


def timestamp():
    ts = time.time()
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d-%H.%M.%S')


def json_open(filename):
    with open(filename) as f:
        return json.load(f)


def json_create(filename, data=None):
    data = data if data else []
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)


def retry(func=None, exception=Exception, n_tries=5, delay=0.1,
          backoff=2, logger=True, on_failure=None):
    """Retry decorator with exponential backoff.

    https://stackoverflow.com/questions/42521549/retry-function-in-python

    `inference.gen` applies it as `@retry(n_tries=3, delay=1, backoff=2,
    on_failure=...)`, so both the bare and the parameterised forms are live.
    """
    # Called with keyword arguments rather than bare: return a decorator.
    if func is None:
        return partial(
            retry,
            exception=exception,
            n_tries=n_tries,
            delay=delay,
            backoff=backoff,
            logger=logger,
            on_failure=on_failure,
        )

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        ntries, ndelay = n_tries, delay
        exe = None
        while ntries > 0:
            try:
                return func(*args, **kwargs)
            except exception as e:
                exe = e
                msg = f"Failed with exception: {str(e)}, Retrying in {ndelay} seconds..."
                if logger:
                    logging.warning(msg)
                else:
                    print(msg)
                time.sleep(ndelay)
                ntries -= 1
                ndelay *= backoff

        if on_failure is not None:
            return on_failure(*args, **kwargs)
        else:
            raise exe

    return wrapper
