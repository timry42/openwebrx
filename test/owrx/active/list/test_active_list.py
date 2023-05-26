from owrx.active.list import ActiveList, ActiveListIndexUpdated, ActiveListIndexAppended, ActiveListIndexDeleted, ActiveListIndexInserted
from unittest import TestCase
from unittest.mock import Mock


class ActiveListTest(TestCase):
    def testListIndexReadAccess(self):
        list = ActiveList(["testvalue"])
        self.assertEqual(list[0], "testvalue")

    def testListIndexWriteAccess(self):
        list = ActiveList(["initialvalue"])
        list[0] = "testvalue"
        self.assertEqual(list[0], "testvalue")

    def testListLength(self):
        list = ActiveList(["somevalue"])
        self.assertEqual(len(list), 1)

    def testListIndexChangeNotification(self):
        list = ActiveList(["initialvalue"])
        listenerMock = Mock()
        list.addListener(listenerMock)
        list[0] = "testvalue"
        listenerMock.onListChange.assert_called_once()
        source, changes = listenerMock.onListChange.call_args.args
        self.assertIs(source, list)
        self.assertEqual(len(changes), 1)
        self.assertIsInstance(changes[0], ActiveListIndexUpdated)
        self.assertEqual(changes[0].index, 0)
        self.assertEqual(changes[0].oldValue, "initialvalue")
        self.assertEqual(changes[0].newValue, "testvalue")

    def testListIndexChangeNotficationNotDisturbedByException(self):
        list = ActiveList(["initialvalue"])
        throwingMock = Mock()
        throwingMock.onListChange.side_effect = RuntimeError("this is a drill")
        list.addListener(throwingMock)
        listenerMock = Mock()
        list.addListener(listenerMock)
        list[0] = "testvalue"
        listenerMock.onListChange.assert_called_once()

    def testListAppend(self):
        list = ActiveList()
        list.append("testvalue")
        self.assertEqual(len(list), 1)
        self.assertEqual(list[0], "testvalue")

    def testListAppendNotification(self):
        list = ActiveList()
        listenerMock = Mock()
        list.addListener(listenerMock)
        list.append("testvalue")
        listenerMock.onListChange.assert_called_once()
        source, changes = listenerMock.onListChange.call_args.args
        self.assertIs(source, list)
        self.assertEqual(len(changes), 1)
        self.assertIsInstance(changes[0], ActiveListIndexAppended)
        self.assertEqual(changes[0].index, 0)
        self.assertEqual(changes[0].newValue, "testvalue")

    def testListDelete(self):
        list = ActiveList(["value1", "value2"])
        del list[0]
        self.assertEqual(len(list), 1)
        self.assertEqual(list[0], "value2")

    def testListDeleteNotification(self):
        list = ActiveList(["value1", "value2"])
        listenerMock = Mock()
        list.addListener(listenerMock)
        del list[0]
        listenerMock.onListChange.assert_called_once()
        source, changes = listenerMock.onListChange.call_args.args
        self.assertIs(source, list)
        self.assertEqual(len(changes), 1)
        self.assertIsInstance(changes[0], ActiveListIndexDeleted)
        self.assertEqual(changes[0].index, 0)
        self.assertEqual(changes[0].oldValue, 'value1')

    def testListDeleteByValue(self):
        list = ActiveList(["value1", "value2"])
        list.remove("value1")
        self.assertEqual(len(list), 1)
        self.assertEqual(list[0], "value2")

    def testActiveListDeleteByValueNotification(self):
        list = ActiveList(["value1", "value2"])
        listenerMock = Mock()
        list.addListener(listenerMock)
        list.remove("value1")
        listenerMock.onListChange.assert_called_once()
        source, changes = listenerMock.onListChange.call_args.args
        self.assertIs(source, list)
        self.assertEqual(len(changes), 1)
        self.assertIsInstance(changes[0], ActiveListIndexDeleted)
        self.assertEqual(changes[0].index, 0)
        self.assertEqual(changes[0].oldValue, 'value1')

    def testListInsert(self):
        list = ActiveList(["value1", "value2"])
        list.insert(1, "value1.5")
        self.assertEqual(len(list), 3)
        self.assertEqual(list[1], "value1.5")

    def testListInsertNotification(self):
        list = ActiveList(["value1", "value2"])
        listenerMock = Mock()
        list.addListener(listenerMock)
        list.insert(1, "value1.5")
        listenerMock.onListChange.assert_called_once()
        source, changes = listenerMock.onListChange.call_args.args
        self.assertIs(source, list)
        self.assertEqual(len(changes), 1)
        self.assertIsInstance(changes[0], ActiveListIndexInserted)
        self.assertEqual(changes[0].index, 1)
        self.assertEqual(changes[0].newValue, "value1.5")

    def testListComprehension(self):
        list = ActiveList(["initialvalue"])
        x = [m for m in list]
        self.assertEqual(len(x), 1)
        self.assertEqual(x[0], "initialvalue")

    def testListenerRemoval(self):
        list = ActiveList(["initialvalue"])
        listenerMock = Mock()
        list.addListener(listenerMock)
        list[0] = "testvalue"
        listenerMock.onListChange.assert_called_once()
        listenerMock.reset_mock()
        list.removeListener(listenerMock)
        list[0] = "someothervalue"
        listenerMock.onListChange.assert_not_called()

    def testListMapTransformation(self):
        list = ActiveList(["somevalue"])
        transformedList = list.map(lambda x: "prefix-{}".format(x))
        self.assertEqual(transformedList[0], "prefix-somevalue")

    def testActiveTransformationUpdate(self):
        list = ActiveList(["initialvalue"])
        transformedList = list.map(lambda x: "prefix-{}".format(x))
        list[0] = "testvalue"
        self.assertEqual(transformedList[0], "prefix-testvalue")

    def testActiveTransformationAppend(self):
        list = ActiveList(["initialvalue"])
        transformedList = list.map(lambda x: "prefix-{}".format(x))
        list.append("newvalue")
        self.assertEqual(transformedList[1], "prefix-newvalue")

    def testActiveTransformationDelete(self):
        list = ActiveList(["value1", "value2"])
        transformedList = list.map(lambda x: "prefix-{}".format(x))
        del list[0]
        self.assertEqual(transformedList[0], "prefix-value2")

    def testFilter(self):
        list = ActiveList([1, 2, 3, 4, 5])
        filteredList = list.filter(lambda x: x < 3)
        self.assertEqual(len(filteredList), 2)
        self.assertEqual(filteredList[0], 1)
        self.assertEqual(filteredList[1], 2)

    def testActiveFilterAppend(self):
        list = ActiveList([1, 2, 3, 4, 5])
        filteredList = list.filter(lambda x: x < 3)
        list.append(0)
        self.assertEqual(len(filteredList), 3)
        self.assertEqual(filteredList[2], 0)

    def testActiveFilterUpdate(self):
        list = ActiveList([1, 2, 3, 4, 5])
        filteredList = list.filter(lambda x: x < 3)
        list[3] = 0
        self.assertEqual(len(filteredList), 3)
        self.assertEqual(filteredList[2], 0)

    def testActiveFilterUpdatePreservesSequence(self):
        list = ActiveList([0, 9, 8, 2, 7, 1, 5])
        filteredList = list.filter(lambda x: x < 3)
        list[1] = 1
        self.assertEqual(len(filteredList), 4)
        self.assertEqual(filteredList[1], 1)

    def testActiveFilterDelete(self):
        list = ActiveList([1, 2, 3, 4, 5])
        filteredList = list.filter(lambda x: x < 3)
        del list[1]
        self.assertEqual(len(filteredList), 1)
        self.assertEqual(filteredList[0], 1)

    def testIndex(self):
        list = ActiveList([1, 2, 3, 4, 5])
        self.assertEqual(list.index(3), 2)

    def testFlatten(self):
        list = ActiveList([ActiveList([1, 2]), ActiveList([3, 4])])
        flattenedList = list.flatten()
        self.assertEqual(len(flattenedList), 4)
        self.assertEqual(flattenedList[0], 1)
        self.assertEqual(flattenedList[1], 2)
        self.assertEqual(flattenedList[2], 3)
        self.assertEqual(flattenedList[3], 4)

    def testActiveFlattenMemberAppend(self):
        sublist = ActiveList([3, 4])
        list = ActiveList([ActiveList([1, 2]), sublist, ActiveList([6, 7])])
        flattenedList = list.flatten()
        sublist.append(5)
        self.assertEqual(len(flattenedList), 7)
        self.assertEqual(flattenedList[4], 5)

    def testActiveFlattenMemberInsert(self):
        sublist = ActiveList([3, 5])
        list = ActiveList([ActiveList([1, 2]), sublist, ActiveList([6, 7])])
        flattenedList = list.flatten()
        sublist.insert(1, 4)
        self.assertEqual(len(flattenedList), 7)
        self.assertEqual(flattenedList[3], 4)

    def testActiveFlattenListInsert(self):
        list = ActiveList([ActiveList([1, 2]), ActiveList([6, 7])])
        flattenedList = list.flatten()
        sublist = ActiveList([3, 4])
        list.insert(1, sublist)
        self.assertEqual(len(flattenedList), 6)
        self.assertEqual(flattenedList[2], 3)

    def testActiveFlattenListUpdate(self):
        sublist = ActiveList([3, 9, 5])
        list = ActiveList([ActiveList([1, 2]), sublist, ActiveList([6, 7])])
        flattenedList = list.flatten()
        sublist = ActiveList([3, 4, 5])
        list[1] = sublist
        self.assertEqual(flattenedList[3], 4)

    def testActiveFlattenMemberUpdate(self):
        sublist = ActiveList([3, 9, 5])
        list = ActiveList([ActiveList([1, 2]), sublist, ActiveList([6, 7])])
        flattenedList = list.flatten()
        sublist[1] = 4
        self.assertEqual(len(flattenedList), 7)
        self.assertEqual(flattenedList[3], 4)

    def testActiveFlattenMemberDelete(self):
        sublist = ActiveList([3, 4, 9, 5])
        list = ActiveList([ActiveList([1, 2]), sublist, ActiveList([6, 7])])
        flattenedList = list.flatten()
        del sublist[2]
        self.assertEqual(len(flattenedList), 7)
        self.assertEqual(flattenedList[4], 5)

    def testActiveFlattenListDelete(self):
        list = ActiveList([ActiveList([1, 2]), ActiveList([9]), ActiveList([3, 4]), ActiveList([5, 6])])
        flattenedList = list.flatten()
        del list[1]
        self.assertEqual(len(flattenedList), 6)
        self.assertEqual(flattenedList[2], 3)

    def testListFilterRenumber(self):
        list = ActiveList([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

        # a simple filter that does not affect our values
        filteredList = list.filter(lambda x: x < 100)

        # some sanity checks before we start modifying the list
        self.assertEqual(len(filteredList), 10)
        self.assertEqual(filteredList[4], 5)

        # delete index 4 (value should be 5)
        del list[4]
        self.assertEqual(len(filteredList), 9)
        self.assertEqual(filteredList[4], 6)

        # modify an index > 4 to check the internal keymap
        list[5] = 42
        # expected result: value is passed on to the filteredList because it is still < 100
        self.assertEqual(filteredList[5], 42)

    def testFilterPropagation(self):
        list = ActiveList([1, 2, 3, 4, 5])
        filteredList = list.filter(lambda x: x < 100)

        list[4] = 6
        self.assertEqual(filteredList[4], 6)

        list.insert(4, 5)
        self.assertEqual(filteredList[4], 5)

        del list[1]
        self.assertEqual(filteredList[3], 5)

    def testFilterPropagationWithActiveFilter(self):
        list = ActiveList([1, 2, 3, 4, 5])
        filteredList = list.filter(lambda x: x != 3)

        list[4] = 6
        self.assertEqual(filteredList[3], 6)

        list.insert(4, 5)
        self.assertEqual(filteredList[3], 5)

        del list[1]
        self.assertEqual(filteredList[2], 5)
