"""What models exist, how to reach them, and what they can do.

Two halves of one concept, previously split between `model.py` (the registry) and
`util/gpt_util.py` (the capability table) for historical reasons only. The registry
names instances; the table describes their types.
"""

import os

# How each model type differs. These properties used to be scattered across
# generate(), openAI_generate() and get_correct_key() as `model_type in (...)`
# tests, which meant adding a provider involved editing several tuples in
# several functions and getting every one of them right.
#
#   api             which generate() branch handles it
#   endpoint        'completions' continues the prompt; 'chat' sends it as a message
#   logprobs_format shape of the returned logprobs. 'legacy' is the parallel
#                   tokens/token_logprobs/top_logprobs arrays the completions
#                   endpoint has always used; 'chat' is the newer list of
#                   per-token dicts. Not implied by the endpoint -- llama-server
#                   answers a completions request with the chat shape.
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
    'logprobs_format': 'legacy',
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
        'logprobs_format': 'chat',
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
    'llama-server': {
        # llama.cpp's own server binary, as opposed to the llama-cpp-python one
        # the entry above was written for. It will not echo the prompt back, but
        # it does return logprobs on /completions -- raw continuation and
        # logprobs at once, which no hosted provider offers.
        'sends_echo': False,
        'echoes_prompt': False,
        # a completions request answered with the chat-shaped logprobs payload,
        # which is why the two are separate properties
        'logprobs_format': 'chat',
        'batch': 'sequential',
    },
    'openrouter': {
        # the chat endpoint, so the prompt is templated as a message and comes
        # back as a reply rather than a continuation. It is the only way to get
        # logprobs out of OpenRouter.
        'endpoint': 'chat',
        'logprobs_format': 'chat',
        'echoes_prompt': False,
        # OpenRouter accepts n, but most of its providers ignore it and return a
        # single choice
        'batch': 'sequential',
        'drop_params': ('logit_bias', 'n'),
        'key': 'OPENROUTER_API_KEY',
    },
    'openrouter-completion': {
        # the completions endpoint, so no chat template is applied and the model
        # continues the text rather than replying to it. No OpenRouter provider
        # returns logprobs here, so counterfactuals are unavailable -- and
        # sending the parameter to one that cannot honour it corrupts the
        # forwarded request, hence dropping it rather than passing 0.
        'sends_echo': False,
        'echoes_prompt': False,
        'batch': 'sequential',
        'drop_params': ('logit_bias', 'n', 'logprobs'),
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


DEFAULT_MODEL_CONFIG = {
    'models': {
        'davinci-002': {
            'model': 'davinci-002',
            'type': 'openai',
            'api_base': 'https://api.openai.com/v1'
            },
        'babbage-002': {
            'model': 'babbage-002',
            'type': 'openai',
            'api_base': 'https://api.openai.com/v1'
            },
        'gpt-3.5-turbo-instruct': {
            'model': 'gpt-3.5-turbo-instruct',
            'type': 'openai',
            'api_base': 'https://api.openai.com/v1'
            },
        'gpt-3.5-turbo': {
            'model': 'gpt-3.5-turbo',
            'type': 'openai-chat',
            'api_base': 'https://api.openai.com/v1'
            },
        'gpt-4': {
            'model': 'gpt-4',
            'type': 'openai-chat',
            'api_base': 'https://api.openai.com/v1'
            },
        'llama-cpp-port-8009': {
            'model': 'Meta-Llama-3-8B-Q4_5_M',
            'type': 'llama-cpp',
            'api_base': 'http://localhost:8009/v1',
            },
        # a genuine base model, served locally by llama.cpp's own server -- see
        # scripts/llama-server.sh. 'model' must match the -a alias the server was
        # started with. The only setup that returns raw continuation and logprobs
        # together; every hosted provider forces a choice between them.
        'qwen2.5-7b-base': {
            'model': 'qwen2.5-7b-base',
            'type': 'llama-server',
            'api_base': 'http://localhost:8081/v1',
            },
        # any model slug from https://openrouter.ai/models works here; the ':free' ones cost nothing.
        # note that not every provider supports logprobs or continuing an assistant message
        'google/gemma-4-26b-a4b-it:free': {
            'model': 'google/gemma-4-26b-a4b-it:free',
            'type': 'openrouter',
            'api_base': 'https://openrouter.ai/api/v1',
            },
        'openai/gpt-oss-20b:free': {
            'model': 'openai/gpt-oss-20b:free',
            'type': 'openrouter',
            'api_base': 'https://openrouter.ai/api/v1',
            },
        # type 'openrouter-completion' posts the prompt to /completions, so no chat template is
        # applied and the model continues the text rather than replying to it. No provider
        # returns logprobs on that endpoint, so counterfactuals are unavailable there.
        # Providers differ in whether they chat-template a completion request, hence the pin.
        'mistralai/mistral-nemo': {
            'model': 'mistralai/mistral-nemo',
            'type': 'openrouter-completion',
            'api_base': 'https://openrouter.ai/api/v1',
            'extra_body': {'provider': {'order': ['DeepInfra'], 'allow_fallbacks': False}},
            },
        'mistralai/Mistral-7B-v0.1':{
            'model': 'mistralai/Mistral-7B-v0.1',
            'type': 'together',
            'api_base': 'https://api.together.xyz/v1'
         },
        'j1-large': {
            'model': 'j1-large',
            'type': 'ai21',
            'api_base': None,
            },
        'j1-jumbo': {
            'model': 'j1-jumbo',
            'type': 'ai21',
            'api_base': None,
            },
        'gpt-neo-1-3b': {
            'model': 'gpt-neo-1.3B',
            'type': 'gooseai',
            'api_base': None,
            },
        'gpt-neo-2-7b': {
            'model': 'gpt-neo-2.7B',
            'type': 'gooseai',
            'api_base': None,
            },
        'gpt-j-6b': {
            'model': 'gpt-j-6B',
            'type': 'gooseai',
            'api_base': None,
            },
        'gpt-neo-20b': {
            'model': 'gpt-neo-20B',
            'type': 'gooseai',
            'api_base': None,
            },
    },
}
