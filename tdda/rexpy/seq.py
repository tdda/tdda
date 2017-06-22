import unittest

def common_string_sequence(s, t):
    """
    Find a sequence of characters that occurs, in order, in both s and t.
    The sequence need not be contiguous in either.

    Doesn't necessarily return the "best" (or longest) such sequence.
    """
    common = []
    p = 0         # position in string t
    for c in s:
        pos = t[p:].find(c)
        if pos > -1:
            common.append(c)
            p += pos + 1
    return ''.join(common)


def common_list_sequence(s, t):
    """
    Find a sequence of elements that occurs, in order, in both lists s and t.
    The sequence need not be contiguous in either.
    """
    common = []
    p = 0         # position in list t
    for c in s:
        pos = find(t[p:], c)
        if pos > -1:
            common.append(c)
            p += pos + 1
    return common


def find(L, c):
    return L.index(c) if c in L else -1


class TestCommonSequences(unittest.TestCase):
    def test_strings(self):
        self.assertEqual(common_string_sequence('', ''), '')
        self.assertEqual(common_string_sequence('abc', 'abc'), 'abc')
        self.assertEqual(common_string_sequence('abcde', 'ace'), 'ace')
        self.assertEqual(common_string_sequence('ace', 'abcde'), 'ace')
        self.assertEqual(common_string_sequence('abcde', 'aced'), 'acd')
        self.assertEqual(common_string_sequence('aced', 'abcde'), 'ace')
        self.assertEqual(common_string_sequence('aced', 'xyz'), '')
        self.assertEqual(common_string_sequence('aaaa', 'a'), 'a')
        self.assertEqual(common_string_sequence('a', 'aaaa'), 'a')
        self.assertEqual(common_string_sequence('aaaa', 'aa'), 'aa')
        self.assertEqual(common_string_sequence('aa', 'aaaa'), 'aa')
        self.assertEqual(common_string_sequence('abc', ''), '')
        self.assertEqual(common_string_sequence('', 'abc'), '')

    def test_sequences(self):
        a = 1
        b = 2
        c = 3
        d = 4
        e = 5
        x = 6
        y = 7
        z = 8
        self.assertEqual(common_list_sequence([], []), [])
        self.assertEqual(common_list_sequence([a, b, c], [a, b, c]), [a, b, c])
        self.assertEqual(common_list_sequence([a, b, c, d, e], [a, c, e]),
                                              [a, c, e])
        self.assertEqual(common_list_sequence([a, c, e], [a, b, c, d, e]),
                                              [a, c, e])
        self.assertEqual(common_list_sequence([a, b, c, d, e], [a, c, e, d]),
                                              [a, c, d])
        self.assertEqual(common_list_sequence([a, c, e, d], [a, b, c, d, e]),
                                              [a, c, e])
        self.assertEqual(common_list_sequence([a, c, e, d], [x, y, z]), [])
        self.assertEqual(common_list_sequence([a, a, a, a], [a]), [a])
        self.assertEqual(common_list_sequence([a], [a, a, a, a]), [a])
        self.assertEqual(common_list_sequence([a, a, a, a], [a, a]), [a, a])
        self.assertEqual(common_list_sequence([a, a], [a, a, a, a]), [a, a])
        self.assertEqual(common_list_sequence([a, b, c], []), [])
        self.assertEqual(common_list_sequence([], [a, b, c]), [])

if __name__ == '__main__':
     unittest.main()
