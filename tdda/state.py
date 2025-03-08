import os

from tdda.config import Config
from tdda.utils import handle_tilde


class StateParams:
    """
    Container for shared GLOBAL parameters.

    These are initialized from file and ordinarily the custom set
    held in this object are returned.

    If, however, p.testing is set to True, the default parameters
    are used instead, to avoid tests being confused by custom settings.

    So for testing, the pattern is:

        from tdda.state import params
        params.testing = True
        try:
            [Do testing]
        finally:
            params.testing = False
    """
    custom = Config()
    custom.referencetest.right_colour = 'blue'
    custom._testing = True

    default = Config()
    default._testing = False

    testing = False

    def __getattr__(self, a):
        if a == 'testing':
            return StateParams.testing
        elif StateParams.__dict__['testing']:
            return StateParams.default.__dict__[a]
        else:
            return StateParams.custom.__dict__[a]

    def __setattr__(self, a, v):
        if a == 'testing':
            StateParams.testing = v
        elif StateParams.__dict__['testing']:
            StateParams.default.__dict__[a] = v
        elif StateParams.__dict__['testing']:
            StateParams.cutom.__dict__[a] = v


#params = StateParams()
config = None

def get_config(force_no_global=False):
    global config
    if force_no_global:
        os.environ['TDDA_NO_CONFIG'] = '1'
        config = Config()
    elif config is None:
        config = Config()
    return config
