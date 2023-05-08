from abc import ABC, abstractmethod

import logging
logger = logging.getLogger(__name__)


class ActiveListChange(ABC):
    pass


class ActiveListIndexUpdated(ActiveListChange):
    def __init__(self, index: int, oldValue, newValue):
        self.index = index
        self.oldValue = oldValue
        self.newValue = newValue


class ActiveListIndexAdded(ActiveListChange):
    def __init__(self, index: int, newValue):
        self.index = index
        self.newValue = newValue


# not sure if differentiation between append and insert is necessary, but we'll offer it for now
# most cases will probably be happy with ActiveListIndexAdded above
class ActiveListIndexAppended(ActiveListIndexAdded):
    pass


class ActiveListIndexInserted(ActiveListIndexAdded):
    pass


class ActiveListIndexDeleted(ActiveListChange):
    def __init__(self, index: int, oldValue):
        self.index = index
        self.oldValue = oldValue


class ActiveListListener(ABC):
    @abstractmethod
    def onListChange(self, source: "ActiveList", changes: list[ActiveListChange]):
        pass


class ActiveListTransformationListener(ActiveListListener):
    def __init__(self, transformation: callable, target: "ActiveList"):
        self.transformation = transformation
        self.target = target

    def onListChange(self, source: "ActiveList", changes: list[ActiveListChange]):
        for change in changes:
            if isinstance(change, ActiveListIndexUpdated):
                self.target[change.index] = self.transformation(change.newValue)
            elif isinstance(change, ActiveListIndexAdded):
                self.target.insert(change.index, self.transformation(change.newValue))
            elif isinstance(change, ActiveListIndexDeleted):
                del self.target[change.index]


class ActiveListFilterListener(ActiveListListener):
    def __init__(self, filter: callable, keyMap: list, target: "ActiveList"):
        self.filter = filter
        self.keyMap = keyMap
        self.target = target

    def onListChange(self, source: "ActiveList", changes: list[ActiveListChange]):
        for change in changes:
            if isinstance(change, ActiveListIndexAdded):
                if self.filter(change.newValue):
                    idx = len([x for x in self.keyMap if x < change.index])
                    self.target.insert(idx, change.newValue)
                    self.keyMap.insert(idx, change.index)
            elif isinstance(change, ActiveListIndexUpdated):
                if change.index in self.keyMap and not self.filter(change.newValue):
                    idx = self.keyMap.index(change.index)
                    del self.target[idx]
                    del self.keyMap[idx]
                elif change.index not in self.keyMap and self.filter(change.newValue):
                    idx = len([x for x in self.keyMap if x < change.index])
                    self.target.insert(idx, change.newValue)
                    self.keyMap.insert(idx, change.index)
            elif isinstance(change, ActiveListIndexDeleted):
                if change.index in self.keyMap:
                    idx = self.keyMap.index(change.index)
                    del self.target[idx]
                    del self.keyMap[idx]


class ActiveListFlattenListener(ActiveListListener):
    def __init__(self, source: "ActiveList", target: "ActiveList"):
        self.source = source
        self.target = target
        for member in self.source:
            member.addListener(self)

    def getOffsetFor(self, source: "ActiveList"):
        idx = self.source.index(source)
        return sum(len(s) for s in self.source[0:idx])

    def onListChange(self, source: "ActiveList", changes: list[ActiveListChange]):
        for change in changes:
            if isinstance(change, ActiveListIndexAdded):
                self.target.insert(self.getOffsetFor(source) + change.index, change.newValue)
            elif isinstance(change, ActiveListIndexUpdated):
                self.target[self.getOffsetFor(source) + change.index] = change.newValue
            elif isinstance(change, ActiveListIndexDeleted):
                del self.target[self.getOffsetFor(source) + change.index]


class ActiveList:
    def __init__(self, elements: list = None):
        self.delegate = elements.copy() if elements is not None else []
        self.listeners = []

    def addListener(self, listener: ActiveListListener):
        if listener in self.listeners:
            return
        self.listeners.append(listener)

    def removeListener(self, listener: ActiveListListener):
        if listener not in self.listeners:
            return
        self.listeners.remove(listener)

    def append(self, value):
        self.delegate.append(value)
        self.__fireChanges([ActiveListIndexAppended(len(self) - 1, value)])

    def __fireChanges(self, changes: list[ActiveListChange]):
        for listener in self.listeners:
            try:
                listener.onListChange(self, changes)
            except Exception:
                logger.exception("Exception during onListChange notification")

    def remove(self, value):
        self.__delitem__(self.delegate.index(value))

    def insert(self, index, value):
        self.delegate.insert(index, value)
        self.__fireChanges([ActiveListIndexInserted(index, value)])

    def index(self, value):
        return self.delegate.index(value)

    def map(self, transform: callable):
        res = ActiveList([transform(v) for v in self])
        self.addListener(ActiveListTransformationListener(transform, res))
        return res

    def filter(self, filter: callable):
        res = ActiveList()
        keyMap = []
        for idx, val in enumerate(self):
            if filter(val):
                res.append(val)
                keyMap.append(idx)
        self.addListener(ActiveListFilterListener(filter, keyMap, res))
        return res

    def flatten(self):
        res = ActiveList([y for x in self for y in x])
        handler = ActiveListFlattenListener(self, res)
        return res

    def __setitem__(self, key, value):
        if self.delegate[key] == value:
            return
        oldValue = self.delegate[key]
        self.delegate[key] = value
        self.__fireChanges([ActiveListIndexUpdated(key, oldValue, value)])

    def __delitem__(self, key):
        oldValue = self.delegate[key]
        del self.delegate[key]
        self.__fireChanges([ActiveListIndexDeleted(key, oldValue)])

    def __getitem__(self, key):
        return self.delegate[key]

    def __len__(self):
        return len(self.delegate)

    def __iter__(self):
        return self.delegate.__iter__()

    def __list__(self):
        return [x for x in self.delegate]
