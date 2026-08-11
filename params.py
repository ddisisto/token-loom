"""Generation parameters — the conditions a span was produced under.

Currently a bag of defaults. Phase 1 of the roadmap makes a parameter set a
first-class object: hashed, interned once in a table, and referenced by every span
it produced, so a span stays self-describing without replaying ancestry. It gains
slice start, stop tokens, seed and n_ctx at that point. Named for what it becomes
rather than what it starts as.

Keys the tkinter app carried and nothing reads any more -- preset, template,
global_context, start, restart, logit_bias -- are gone. logit_bias in particular
was a GPT-2 token mask, meaningless for any model in use, listed in drop_params
for every OpenRouter type, and unreachable behind a default of ''.
"""

import codecs

DEFAULT_GENERATION_SETTINGS = {
    'num_continuations': 4,
    'temperature': 0.9,
    'top_p': 1,
    'response_length': 100,
    'prompt_length': 6000,
    'logprobs': 1,
    'model': 'google/gemma-4-26b-a4b-it:free',
    'stop': '',  # separated by '|'
}


def parse_stop(stop_string):
    return codecs.decode(stop_string, "unicode-escape").split('|')
