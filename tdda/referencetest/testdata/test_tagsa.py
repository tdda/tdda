from tdda.referencetest import ReferenceTestCase, tag

class TestA(ReferenceTestCase):
    def testAfail(self):
        self.assertTrue(False)

if __name__ == '__main__':
    ReferenceTestCase.main()
