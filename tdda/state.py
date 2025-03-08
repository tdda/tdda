import os

from tdda.config import Config

config = None

def get_config(force_no_global=False):
    global config
    if force_no_global:
        os.environ['TDDA_NO_CONFIG'] = '1'
        config = Config()
    elif config is None:
        config = Config()
    return config
