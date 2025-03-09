import os

from tdda.config import Config

config = None
load = True
testing = False


def get_config(force_no_global=False):
    global config, load, testing
    if force_no_global:
        config = Config(load=False, testing=testing)
    elif config is None:
        config = Config(load=load, testing=testing)
    return config


def set_load(v):
    global load, config
    old_val = load
    load = v
    return old_val


def set_testing(v):
    global testing, config
    old_val = testing
    testing = v
    config = Config(load=load, testing=testing)
    return old_val


def get_testing():
    global testing
    return testing

