from tdda.referencetest import ReferenceTestCase, tag

class TestC(ReferenceTestCase):
    def testCpass(self):
        self.assertTrue(True)

    def testCfail(self):
        self.assertTrue(False)

    def testCerror(self):
        self.assertTrue(0/0)

if __name__ == '__main__':
    ReferenceTestCase.main()
