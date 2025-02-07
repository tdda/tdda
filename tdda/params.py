from tdda.referencetest.params import ReferenceTestParams
#from tdda.constraints.params import ConstraintsParams

class ConstraintsParams:
    def __init__(self):
        pass


class TDDAParams:
    def __init__(self):
        self.referencetest = ReferenceTestParams()
        self.constraints = ConstraintsParams()

