import openai
import os
import numpy as np
import math
import codecs
from util.tokenizer import logit_mask


def normalize(probs):
    return [float(i) / sum(probs) for i in probs]


def logprobs_to_probs(probs):
    if isinstance(probs, list):
        return [math.exp(x) for x in probs]
    else:
        return math.exp(probs)


def dict_logprobs_to_probs(prob_dict):
    return {key: math.exp(prob_dict[key]) for key in prob_dict.keys()}


def total_logprob(response):
    logprobs = response['logprobs']['token_logprobs']
    logprobs = [i for i in logprobs if not math.isnan(i)]
    return sum(logprobs)


def tokenize_ada(prompt):
    response = openai.Completion.create(
        engine='ada',
        prompt=prompt,
        max_tokens=0,
        echo=True,
        n=1,
        logprobs=0
    )
    tokens = response.choices[0]["logprobs"]["tokens"]
    positions = response.choices[0]["logprobs"]["text_offset"]
    return tokens, positions


def prompt_probs(prompt, engine='ada'):
    response = openai.Completion.create(
        engine=engine,
        prompt=prompt,
        max_tokens=0,
        echo=True,
        n=1,
        logprobs=0
    )
    positions = response.choices[0]["logprobs"]["text_offset"]
    tokens = response.choices[0]["logprobs"]["tokens"]
    logprobs = response.choices[0]["logprobs"]["token_logprobs"]
    return logprobs, tokens, positions

# evaluates logL(prompt+target | prompt)
def conditional_logprob(prompt, target, engine='ada'):
    combined = prompt + target
    response = openai.Completion.create(
        engine=engine,
        prompt=combined,
        max_tokens=0,
        echo=True,
        n=1,
        logprobs=0
    )
    positions = response.choices[0]["logprobs"]["text_offset"]
    logprobs = response.choices[0]["logprobs"]["token_logprobs"]
    word_index = positions.index(len(prompt))
    total_conditional_logprob = sum(logprobs[word_index:])
    return total_conditional_logprob



# TODO use threading
# returns the conditional probabilities for each event happening after prompt
def event_probs(prompt, events, engine='ada'):
    probs = []
    for event in events:
        logprob = conditional_logprob(prompt, event, engine)
        probs.append(logprobs_to_probs(logprob))

    normal_probs = normalize(probs)
    return probs, normal_probs


# like event_probs, returns conditional probabilities (normalized & unnormalized) for each token occurring after prompt
def token_probs(prompt, tokens, engine='ada'):
    pass


# returns a list of positions and counterfactual probability of token at position
# if token is not in top_logprobs, probability is treated as 0
# all positions if actual_token=None, else only positions where the actual token in response is actual_token
# TODO next sequence instead of next token
def counterfactual(response, token, actual_token=None, next_token=None, sort=True):
    counterfactual_probs = []
    tokens = response.choices[0]['logprobs']['tokens']
    top_logprobs = response.choices[0]['logprobs']['top_logprobs']
    positions = response.choices[0]['logprobs']['text_offset']
    for i, probs in enumerate(top_logprobs):
        if (actual_token is None and next_token is None) \
                or actual_token == tokens[i] \
                or (i < len(tokens) - 1 and next_token == tokens[i+1]):
            if token in probs:
                counterfactual_probs.append({'position': positions[i+1],
                                             'prob': logprobs_to_probs(probs[token])})
            else:
                counterfactual_probs.append({'position': positions[i+1], 'prob': 0})
    if sort:
        counterfactual_probs = sorted(counterfactual_probs, key=lambda k: k['prob'])
    return counterfactual_probs


# returns a list of substrings of content and
# logL(preprompt+substring+target | preprompt+substring) for each substring
def substring_probs(preprompt, content, target, engine='ada', quiet=0):
    logprobs = []
    substrings = []
    _, positions = tokenize_ada(content)
    for position in positions:
        substring = content[:position]
        prompt = preprompt + substring
        logprob = conditional_logprob(prompt, target, engine)
        logprobs.append(logprob)
        substrings.append(substring)
        if not quiet:
            print(substring)
            print('logprob: ', logprob)

    return substrings, logprobs


# returns a list of substrings of content
# logL(substring+target | substring) for each substring
def token_conditional_logprob(content, target, engine='ada'):
    response = openai.Completion.create(
        engine=engine,
        prompt=content,
        max_tokens=0,
        echo=True,
        n=1,
        logprobs=100
    )
    tokens = response.choices[0]['logprobs']['tokens']
    top_logprobs = response.choices[0]['logprobs']['top_logprobs']
    logprobs = []
    substrings = []
    substring = ''
    for i, probs in enumerate(top_logprobs):
        substrings.append(substring)
        if target in probs:
            logprobs.append(probs[target])
        else:
            logprobs.append(None)
        substring += tokens[i]
    return substrings, logprobs



def sort_logprobs(substrings, logprobs, n_top=None):
    sorted_indices = np.argsort(logprobs)
    top = []
    if n_top is None:
        n_top = len(sorted_indices)
    for i in range(n_top):
        top.append({'substring': substrings[sorted_indices[-(i + 1)]],
                    'logprob': logprobs[sorted_indices[-(i + 1)]]})
    return top


def top_logprobs(preprompt, content, target, n_top=None, engine='ada', quiet=0):
    substrings, logprobs = substring_probs(preprompt, content, target, engine, quiet)
    return sort_logprobs(substrings, logprobs, n_top)


def decibels(prior, evidence, target, engine='ada'):
    prior_target_logprob = conditional_logprob(prompt=prior, target=target, engine=engine)
    evidence_target_logprob = conditional_logprob(prompt=evidence, target=target, engine=engine)
    return (evidence_target_logprob - prior_target_logprob), prior_target_logprob, evidence_target_logprob


def parse_stop(stop_string):
    return codecs.decode(stop_string, "unicode-escape").split('|')

def parse_logit_bias(logit_string):
    biases = codecs.decode(logit_string, "unicode-escape").split('|')
    bias_dict = {}
    for b in biases:
        bias_parts = b.split(':')
        token = bias_parts[0]
        bias = int(bias_parts[1])
        bias_dict[token] = bias
    return logit_mask(bias_dict)

# How each model type differs. These properties used to be scattered across
# generate(), openAI_generate() and get_correct_key() as `model_type in (...)`
# tests, which meant adding a provider involved editing several tuples in
# several functions and getting every one of them right.
#
#   api             which generate() branch handles it
#   endpoint        'completions' continues the prompt; 'chat' sends it as a message
#   sends_echo      whether the request asks the API to include the prompt
#   echoes_prompt   whether the response actually contains it, which is what the
#                   formatter needs. Not the same thing: Together AI accepts the
#                   echo parameter and ignores it.
#   batch           'native' passes n to the API; 'sequential' issues n calls
#   requires_logprobs  the API rejects logprobs=0
#   drop_params     request parameters the provider rejects outright. Omitting
#                   these is not cosmetic: sending one a provider cannot honour
#                   can corrupt the whole forwarded request.
#   key/organization   environment variables holding the credentials
MODEL_TYPE_DEFAULTS = {
    'api': 'openai',
    'endpoint': 'completions',
    'sends_echo': True,
    'echoes_prompt': True,
    'batch': 'native',
    'requires_logprobs': False,
    'drop_params': (),
    'key': None,
    'organization': None,
}

MODEL_TYPES = {
    'openai': {
        'key': 'OPENAI_API_KEY',
        'organization': 'OPENAI_ORGANIZATION',
    },
    'openai-custom': {
        'key': 'OPENAI_API_KEY',
        'organization': 'OPENAI_ORGANIZATION',
    },
    'openai-chat': {
        'endpoint': 'chat',
        'echoes_prompt': False,
        'key': 'OPENAI_API_KEY',
        'organization': 'OPENAI_ORGANIZATION',
    },
    'gooseai': {
        'key': 'GOOSEAI_API_KEY',
    },
    'together': {
        # Together AI ignores the echo parameter, so the prompt never comes back
        'echoes_prompt': False,
        # chat inference and Together both break if logprobs is 0
        'requires_logprobs': True,
        'key': 'TOGETHERAI_API_KEY',
    },
    'llama-cpp': {
        # llama-cpp-python doesn't support batched inference yet:
        # https://github.com/abetlen/llama-cpp-python/issues/771
        'batch': 'sequential',
    },
    'openrouter': {
        # the chat endpoint, so the prompt is templated as a message and comes
        # back as a reply rather than a continuation. It is the only way to get
        # logprobs out of OpenRouter.
        'endpoint': 'chat',
        'echoes_prompt': False,
        # OpenRouter accepts n, but most of its providers ignore it and return a
        # single choice
        'batch': 'sequential',
        'drop_params': ('logit_bias', 'n'),
        'key': 'OPENROUTER_API_KEY',
    },
    'ai21': {
        'api': 'ai21',
    },
}


def model_type_info(model_type):
    """Capabilities of a model type, with defaults filled in.

    Unknown types get the defaults rather than raising, so that credential
    lookup stays total. generate() rejects them explicitly instead.
    """
    return {**MODEL_TYPE_DEFAULTS, **MODEL_TYPES.get(model_type, {})}


def _credential(name, kwargs):
    """Explicitly passed value first, environment second, as it has always been."""
    if not name:
        return None
    value = kwargs.get(name, None)
    return value if value else os.environ.get(name, None)


def get_correct_key(model_type, kwargs={}):
    info = model_type_info(model_type)
    return _credential(info['key'], kwargs), _credential(info['organization'], kwargs)
