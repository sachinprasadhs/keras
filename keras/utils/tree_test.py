import collections

import numpy as np

from keras import ops
from keras import testing
from keras.utils import tree

STRUCTURE1 = (((1, 2), 3), 4, (5, 6))
STRUCTURE2 = ((("foo1", "foo2"), "foo3"), "foo4", ("foo5", "foo6"))
STRUCTURE_DIFFERENT_NUM_ELEMENTS = ("spam", "eggs")
STRUCTURE_DIFFERENT_NESTING = (((1, 2), 3), 4, 5, (6,))


class TreeTest(testing.TestCase):
    def test_is_nested(self):
        self.assertFalse(tree.is_nested("1234"))
        self.assertFalse(tree.is_nested(b"1234"))
        self.assertFalse(tree.is_nested(bytearray("1234", "ascii")))
        self.assertTrue(tree.is_nested([1, 3, [4, 5]]))
        self.assertTrue(tree.is_nested(((7, 8), (5, 6))))
        self.assertTrue(tree.is_nested([]))
        self.assertTrue(tree.is_nested({"a": 1, "b": 2}))
        self.assertFalse(tree.is_nested(set([1, 2])))
        ones = np.ones([2, 3])
        self.assertFalse(tree.is_nested(ones))
        self.assertFalse(tree.is_nested(np.tanh(ones)))
        self.assertFalse(tree.is_nested(np.ones((4, 5))))

    def test_flatten_and_unflatten(self):
        structure = ((3, 4), 5, (6, 7, (9, 10), 8))
        flat = ["a", "b", "c", "d", "e", "f", "g", "h"]

        self.assertEqual(tree.flatten(structure), [3, 4, 5, 6, 7, 9, 10, 8])
        self.assertEqual(
            tree.unflatten_as(structure, flat),
            (("a", "b"), "c", ("d", "e", ("f", "g"), "h")),
        )
        point = collections.namedtuple("Point", ["x", "y"])
        structure = (point(x=4, y=2), ((point(x=1, y=0),),))
        flat = [4, 2, 1, 0]
        self.assertEqual(tree.flatten(structure), flat)
        restructured_from_flat = tree.unflatten_as(structure, flat)
        self.assertEqual(restructured_from_flat, structure)
        self.assertEqual(restructured_from_flat[0].x, 4)
        self.assertEqual(restructured_from_flat[0].y, 2)
        self.assertEqual(restructured_from_flat[1][0][0].x, 1)
        self.assertEqual(restructured_from_flat[1][0][0].y, 0)

        self.assertEqual([5], tree.flatten(5))
        self.assertEqual([np.array([5])], tree.flatten(np.array([5])))

        self.assertEqual("a", tree.unflatten_as(5, ["a"]))
        self.assertEqual(np.array([5]), tree.unflatten_as("scalar", [np.array([5])]))

        with self.assertRaisesRegex(ValueError, "Structure is a scalar"):
            tree.unflatten_as("scalar", [4, 5])
        with self.assertRaisesRegex(TypeError, "flat_sequence"):
            tree.unflatten_as([4, 5], "bad_sequence")
        with self.assertRaises(ValueError):
            tree.unflatten_as([5, 6, [7, 8]], ["a", "b", "c"])

        self.assertEqual(
            tree.unflatten_as({1: None, 2: None}, ["Hello", "world!"]),
            {1: "Hello", 2: "world!"},
        )

    def test_flatten_dict_order(self):
        ordered = collections.OrderedDict([("d", 3), ("b", 1), ("a", 0), ("c", 2)])
        plain = {"d": 3, "b": 1, "a": 0, "c": 2}
        ordered_flat = tree.flatten(ordered)
        plain_flat = tree.flatten(plain)
        self.assertEqual([3, 1, 0, 2], ordered_flat)
        self.assertEqual([0, 1, 2, 3], plain_flat)

    def test_unflatten_dict_order(self):
        ordered = collections.OrderedDict([("d", 0), ("b", 0), ("a", 0), ("c", 0)])
        plain = {"d": 0, "b": 0, "a": 0, "c": 0}
        seq = [0, 1, 2, 3]
        ordered_reconstruction = tree.unflatten_as(ordered, seq)
        plain_reconstruction = tree.unflatten_as(plain, seq)
        self.assertEqual(
            collections.OrderedDict([("d", 0), ("b", 1), ("a", 2), ("c", 3)]),
            ordered_reconstruction,
        )
        self.assertEqual({"d": 3, "b": 1, "a": 0, "c": 2}, plain_reconstruction)

    def test_map_structure(self):
        structure2 = (((7, 8), 9), 10, (11, 12))
        structure1_plus1 = tree.map_structure(lambda x: x + 1, STRUCTURE1)
        tree.assert_same_structure(STRUCTURE1, structure1_plus1)
        self.assertAllEqual([2, 3, 4, 5, 6, 7], tree.flatten(structure1_plus1))
        structure1_plus_structure2 = tree.map_structure(
            lambda x, y: x + y, STRUCTURE1, structure2
        )
        self.assertEqual(
            (((1 + 7, 2 + 8), 3 + 9), 4 + 10, (5 + 11, 6 + 12)),
            structure1_plus_structure2,
        )

        self.assertEqual(3, tree.map_structure(lambda x: x - 1, 4))

        self.assertEqual(7, tree.map_structure(lambda x, y: x + y, 3, 4))

        # Empty structures
        self.assertEqual((), tree.map_structure(lambda x: x + 1, ()))
        self.assertEqual([], tree.map_structure(lambda x: x + 1, []))
        self.assertEqual({}, tree.map_structure(lambda x: x + 1, {}))
        empty_nt = collections.namedtuple("empty_nt", "")
        self.assertEqual(empty_nt(), tree.map_structure(lambda x: x + 1, empty_nt()))

        # This is checking actual equality of types, empty list != empty tuple
        self.assertNotEqual((), tree.map_structure(lambda x: x + 1, []))

        with self.assertRaisesRegex(TypeError, "callable"):
            tree.map_structure("bad", structure1_plus1)
        with self.assertRaisesRegex(ValueError, "at least one structure"):
            tree.map_structure(lambda x: x)
        with self.assertRaisesRegex(ValueError, "have the same structure"):
            tree.map_structure(lambda x, y: None, (3, 4), (3, 4, 5))
        with self.assertRaisesRegex(ValueError, "have the same structure"):
            tree.map_structure(lambda x, y: None, 3, (3,))
        with self.assertRaisesRegex(ValueError, "have the same structure"):
            tree.map_structure(lambda x, y: None, ((3, 4), 5), [(3, 4), 5])
        with self.assertRaisesRegex(ValueError, "have the same structure"):
            tree.map_structure(lambda x, y: None, ((3, 4), 5), (3, (4, 5)))

        structure1_list = [[[1, 2], 3], 4, [5, 6]]
        with self.assertRaisesRegex(ValueError, "have the same structure"):
            tree.map_structure(lambda x, y: None, STRUCTURE1, structure1_list)

    def test_map_structure_up_to(self):
        # Named tuples.
        ab_tuple = collections.namedtuple("ab_tuple", "a, b")
        op_tuple = collections.namedtuple("op_tuple", "add, mul")
        inp_val = ab_tuple(a=2, b=3)
        inp_ops = ab_tuple(a=op_tuple(add=1, mul=2), b=op_tuple(add=2, mul=3))
        out = tree.map_structure_up_to(
            inp_val,
            lambda val, ops: (val + ops.add) * ops.mul,
            inp_val,
            inp_ops,
        )
        self.assertEqual(out.a, 6)
        self.assertEqual(out.b, 15)

        # Lists.
        data_list = [[2, 4, 6, 8], [[1, 3, 5, 7, 9], [3, 5, 7]]]
        name_list = ["evens", ["odds", "primes"]]
        out = tree.map_structure_up_to(
            name_list,
            lambda name, sec: "first_{}_{}".format(len(sec), name),
            name_list,
            data_list,
        )
        self.assertEqual(out, ["first_4_evens", ["first_5_odds", "first_3_primes"]])

    def test_assert_same_structure(self):
        tree.assert_same_structure(STRUCTURE1, STRUCTURE2, check_types=False)
        tree.assert_same_structure("abc", 1.0, check_types=False)
        tree.assert_same_structure(b"abc", 1.0, check_types=False)
        tree.assert_same_structure("abc", 1.0, check_types=False)
        tree.assert_same_structure(bytearray("abc", "ascii"), 1.0, check_types=False)
        tree.assert_same_structure("abc", np.array([0, 1]), check_types=False)

        with self.assertRaisesRegex(ValueError, "have the same structure"):
            tree.assert_same_structure(STRUCTURE1, STRUCTURE_DIFFERENT_NUM_ELEMENTS)
        with self.assertRaisesRegex(ValueError, "have the same structure"):
            tree.assert_same_structure([0, 1], np.array([0, 1]))
        with self.assertRaisesRegex(ValueError, "have the same structure"):
            tree.assert_same_structure(0, [0, 1])
        with self.assertRaisesRegex(ValueError, "have the same structure"):
            tree.assert_same_structure((0, 1), [0, 1])
        with self.assertRaisesRegex(ValueError, "have the same structure"):
            tree.assert_same_structure(STRUCTURE1, STRUCTURE_DIFFERENT_NESTING)
        with self.assertRaisesRegex(ValueError, "have the same structure"):
            tree.assert_same_structure([[3], 4], [3, [4]])
        with self.assertRaisesRegex(ValueError, "have the same structure"):
            tree.assert_same_structure({"a": 1}, {"b": 1})
        structure1_list = [[[1, 2], 3], 4, [5, 6]]
        with self.assertRaisesRegex(ValueError, "have the same structure"):
            tree.assert_same_structure(STRUCTURE1, structure1_list)
        tree.assert_same_structure(STRUCTURE1, STRUCTURE2, check_types=False)
        with self.assertRaisesRegex(ValueError, "have the same structure"):
            tree.assert_same_structure(STRUCTURE1, structure1_list, check_types=False)

    def test_pack_sequence_as(self):
        structure = {"key3": "", "key1": "", "key2": ""}
        flat_sequence = ["value1", "value2", "value3"]
        self.assertEqual(
            tree.pack_sequence_as(structure, flat_sequence),
            {"key3": "value3", "key1": "value1", "key2": "value2"},
        )
        structure = (("a", "b"), ("c", "d", "e"), "f")
        flat_sequence = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        self.assertEqual(
            tree.pack_sequence_as(structure, flat_sequence),
            ((1.0, 2.0), (3.0, 4.0, 5.0), 6.0),
        )
        structure = {
            "key3": {"c": ("alpha", "beta"), "a": ("gamma")},
            "key1": {"e": "val1", "d": "val2"},
        }
        flat_sequence = ["val2", "val1", 3.0, 1.0, 2.0]
        self.assertEqual(
            tree.pack_sequence_as(structure, flat_sequence),
            {
                "key3": {"c": (1.0, 2.0), "a": 3.0},
                "key1": {"e": "val1", "d": "val2"},
            },
        )
        structure = ["a"]
        flat_sequence = [np.array([[1, 2], [3, 4]])]
        self.assertAllClose(
            tree.pack_sequence_as(structure, flat_sequence),
            [np.array([[1, 2], [3, 4]])],
        )
        structure = ["a"]
        flat_sequence = [ops.ones([2, 2])]
        self.assertAllClose(
            tree.pack_sequence_as(structure, flat_sequence),
            [ops.ones([2, 2])],
        )

        with self.assertRaisesRegex(TypeError, "Attempted to pack value:"):
            structure = ["a"]
            flat_sequence = 1
            tree.pack_sequence_as(structure, flat_sequence)
        with self.assertRaisesRegex(ValueError, "The target structure is of"):
            structure = "a"
            flat_sequence = [1, 2]
            tree.pack_sequence_as(structure, flat_sequence)

    def test_lists_to_tuples(self):
        structure = [1, 2, 3]
        self.assertEqual(tree.lists_to_tuples(structure), (1, 2, 3))
        structure = [[1], [2, 3]]
        self.assertEqual(tree.lists_to_tuples(structure), ((1,), (2, 3)))
        structure = [[1], [2, [3]]]
        self.assertEqual(tree.lists_to_tuples(structure), ((1,), (2, (3,))))

    def test_traverse(self):
        # Lists to tuples
        structure = [(1, 2), [3], {"a": [4]}]
        self.assertEqual(
            ((1, 2), (3,), {"a": (4,)}),
            tree.traverse(
                lambda x: tuple(x) if isinstance(x, list) else x,
                structure,
                top_down=False,
            ),
        )
        # EarlyTermination
        structure = [(1, [2]), [3, (4, 5, 6)]]
        visited = []

        def visit(x):
            visited.append(x)
            return "X" if isinstance(x, tuple) and len(x) > 2 else None

        output = tree.traverse(visit, structure)
        self.assertEqual([(1, [2]), [3, "X"]], output)
        self.assertEqual(
            [
                [(1, [2]), [3, (4, 5, 6)]],
                (1, [2]),
                1,
                [2],
                2,
                [3, (4, 5, 6)],
                3,
                (4, 5, 6),
            ],
            visited,
        )
