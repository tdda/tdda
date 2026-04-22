import os

from tdda.config import Config

config = None
load = True
testing = False


def get_config(c, /, force_no_global=False):
    if c is not None:
        return c
    global config, load, testing
    if force_no_global:
        return Config(load=False, testing=testing)
    if config is None:
        return Config(load=load, testing=testing)
    return config


def set_load(v):
    global load, config
    old_val = load
    load = v
    return old_val


def set_testing(v=True):
    global testing, config
    old_val = testing
    testing = v
    config = Config(load=load, testing=testing)
    return old_val


def get_testing():
    global testing
    return testing


def reset_config():
    global config
    config = None
