from unittest import TestCase
from owrx.active.list import ActiveList, ActiveListFilter


class AdvancedFilter(ActiveListFilter):
    def __init__(self, result: bool):
        self.result = result
        self.callback = None

    def predicate(self, value) -> bool:
        return self.result

    def monitor(self, member, callback: callable):
        self.callback = callback

    def trigger(self, newResult: bool):
        self.result = newResult
        self.callback()


class AdvancedFilterTest(TestCase):
    def testAdvancedFilter(self):
        list = ActiveList([1, 2, 3])
        filteredList = list.filter(AdvancedFilter(True))
        self.assertEqual(len(filteredList), 3)
        filteredList = list.filter(AdvancedFilter(False))
        self.assertEqual(len(filteredList), 0)

    def testListMonitor(self):
        list = ActiveList([1, 2, 3])
        filter = AdvancedFilter(True)
        filteredList = list.filter(filter)
        filter.trigger(False)
        self.assertEqual(len(filteredList), 2)
