from owrx.active.list import ActiveList, ActiveListTransformation
from unittest import TestCase


class TestTranformation(ActiveListTransformation):
    def __init__(self):
        self.callback = None
        self.prefix = "value"

    def transform(self, value):
        return "{}{}".format(self.prefix, value)

    def monitor(self, member, callback: callable):
        self.callback = callback

    def trigger(self, newPrefix: str):
        self.prefix = newPrefix
        self.callback()


class AdvancedTransformationTest(TestCase):
    def testListAdvancedTransformation(self):
        list = ActiveList([1, 2])
        transformedList = list.map(TestTranformation())
        self.assertEqual(len(transformedList), 2)
        self.assertEqual(transformedList[0], "value1")
        self.assertEqual(transformedList[1], "value2")

    def testListMonitor(self):
        list = ActiveList([1, 2])
        transformation = TestTranformation()
        transformedList = list.map(transformation)
        transformation.trigger("foobar")
        self.assertEqual(transformedList[1], "foobar2")
