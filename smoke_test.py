#!/usr/bin/env python
"""Headless check that generation works, without launching the GUI.

Any name already in DEFAULT_MODEL_CONFIG is used as configured -- including
qwen2.5-7b-base, which is the one that returns logprobs on a raw continuation.
An unknown name is assumed to be an OpenRouter slug and registered as one.

Usage: python smoke_test.py [model]
"""
import sys

from dotenv import load_dotenv

load_dotenv()

from gpt import gen
from model import DEFAULT_GENERATION_SETTINGS, DEFAULT_MODEL_CONFIG

model = sys.argv[1] if len(sys.argv) > 1 else 'google/gemma-4-26b-a4b-it:free'
if model not in DEFAULT_MODEL_CONFIG['models']:
    DEFAULT_MODEL_CONFIG['models'][model] = {'model': model,
                                             'type': 'openrouter',
                                             'api_base': 'https://openrouter.ai/api/v1'}

settings = {**DEFAULT_GENERATION_SETTINGS,
            'model': model,
            'num_continuations': 3,
            'response_length': 40,
            'logprobs': 3}

prompt = "The lighthouse keeper wrote in his log: the sea was"
response, error = gen(prompt, settings, DEFAULT_MODEL_CONFIG)

print('error:', error)
if response:
    print('model:', response['model'], '| completions:', len(response['completions']))
    for completion in response['completions']:
        print(' -', repr(completion['text'][:90]), '| tokens:', len(completion['tokens']))
    tokens = response['completions'][0]['tokens']
    if tokens:
        print('sample token:', tokens[0])
