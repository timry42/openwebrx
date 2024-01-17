from abc import ABC, abstractmethod
from typing import Union
from functools import partial

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


class ActiveListIndexMoved(ActiveListChange):
    def __init__(self, old_index: int, new_index: int):
        self.old_index = old_index
        self.new_index = new_index


class ActiveListListener(ABC):
    @abstractmethod
    def onListChange(self, source: "ActiveList", changes: list[ActiveListChange]):
        pass


class ActiveListTransformation(ABC):
    @abstractmethod
    def transform(self, value):
        pass

    def monitor(self, member, callback: callable):
        pass

    def unmonitor(self, member):
        pass


class BasicTransformation(ActiveListTransformation):
    def __init__(self, transformation: callable):
        self.transformation = transformation

    def transform(self, value):
        return self.transformation(value)


class ActiveListFilter(ABC):
    @abstractmethod
    def predicate(self, value) -> bool:
        pass

    def monitor(self, member, callback: callable):
        pass

    def unmonitor(self, member):
        pass


class BasicFilter(ActiveListFilter):
    def __init__(self, predicate: callable):
        self.predicate = predicate

    def predicate(self, value) -> bool:
        return self.predicate(value)


class ActiveListTransformationListener(ActiveListListener):
    def __init__(self, transformation: ActiveListTransformation, source: "ActiveList", target: "ActiveList"):
        self.transformation = transformation
        self.source = source
        self.target = target
        for v in self.source:
            transformation.monitor(v, partial(self._onMonitor, v))

    def onListChange(self, source: "ActiveList", changes: list[ActiveListChange]):
        for change in changes:
            if isinstance(change, ActiveListIndexUpdated):
                self.transformation.unmonitor(change.oldValue)
                self.target[change.index] = self.transformation.transform(change.newValue)
                self.transformation.monitor(change.newValue, partial(self._onMonitor, change.newValue))
            elif isinstance(change, ActiveListIndexAdded):
                self.target.insert(change.index, self.transformation.transform(change.newValue))
                self.transformation.monitor(change.newValue, partial(self._onMonitor, change.newValue))
            elif isinstance(change, ActiveListIndexDeleted):
                del self.target[change.index]
                self.transformation.unmonitor(change.oldValue)
            elif isinstance(change, ActiveListIndexMoved):
                self.target.move(change.old_index, change.new_index)

    def _onMonitor(self, value):
        idx = self.source.index(value)
        self.target[idx] = self.transformation.transform(self.source[idx])


class ActiveListFilterListener(ActiveListListener):
    def __init__(self, filter: ActiveListFilter, source: "ActiveList", target: "ActiveList"):
        self.filter = filter
        self.source = source
        self.keyMap = [idx for idx, val in enumerate(self.source) if self.filter.predicate(val)]
        for v in self.source:
            self.filter.monitor(v, partial(self._onMonitor, v))
        self.target = target

    def onListChange(self, source: "ActiveList", changes: list[ActiveListChange]):
        for change in changes:
            if isinstance(change, ActiveListIndexAdded):
                idx = len([x for x in self.keyMap if x < change.index])
                for i in range(idx, len(self.keyMap)):
                    self.keyMap[i] += 1
                if self.filter.predicate(change.newValue):
                    self.keyMap.insert(idx, change.index)
                    self.target.insert(idx, change.newValue)
                self.filter.monitor(change.newValue, partial(self._onMonitor, change.newValue))
            elif isinstance(change, ActiveListIndexUpdated):
                self.filter.unmonitor(change.oldValue)
                if change.index in self.keyMap and not self.filter.predicate(change.newValue):
                    idx = self.keyMap.index(change.index)
                    del self.target[idx]
                    del self.keyMap[idx]
                elif change.index not in self.keyMap and self.filter.predicate(change.newValue):
                    idx = len([x for x in self.keyMap if x < change.index])
                    self.keyMap.insert(idx, change.index)
                    self.target.insert(idx, change.newValue)
                if change.index in self.keyMap:
                    idx = self.keyMap.index(change.index)
                    self.target[idx] = change.newValue
                self.filter.monitor(change.newValue, partial(self._onMonitor, change.newValue))
            elif isinstance(change, ActiveListIndexDeleted):
                self.filter.unmonitor(change.oldValue)
                idx = len([x for x in self.keyMap if x < change.index])
                if change.index in self.keyMap:
                    del self.target[idx]
                    del self.keyMap[idx]
                for i in range(idx, len(self.keyMap)):
                    self.keyMap[i] -= 1
            elif isinstance(change, ActiveListIndexMoved):
                start_idx = len([x for x in self.keyMap if x < change.old_index])
                end_idx = len([x for x in self.keyMap if x < change.new_index])
                offset = 0
                if change.old_index in self.keyMap:
                    offset = 1
                else:
                    end_idx += 1
                if end_idx > start_idx:
                    for i in reversed(range(start_idx, end_idx)):
                        self.keyMap[i] = self.keyMap[i + offset] - 1
                else:
                    for i in reversed(range(end_idx, start_idx)):
                        self.keyMap[i] = self.keyMap[i - offset] + 1
                if offset:
                    self.target.move(start_idx, end_idx)

    def _onMonitor(self, value):
        idx = self.source.index(value)
        if idx in self.keyMap and not self.filter.predicate(value):
            idx = self.keyMap.index(idx)
            del self.target[idx]
            del self.keyMap[idx]
        elif idx not in self.keyMap and self.filter.predicate(value):
            newIndex = len([x for x in self.keyMap if x < idx])
            self.keyMap.insert(newIndex, idx)
            self.target.insert(newIndex, value)


class ActiveListFlattenListener(ActiveListListener):
    def __init__(self, source: "ActiveList", target: "ActiveList"):
        self.source = source
        self.target = target
        self.source.addListener(self)
        for member in self.source:
            member.addListener(self)

    def getOffsetFor(self, source: "ActiveList"):
        idx = self.source.index(source)
        return self.getOffsetForIndex(idx)

    def getOffsetForIndex(self, idx: int):
        return sum(len(s) for s in self.source[0:idx])

    def onListChange(self, source: "ActiveList", changes: list[ActiveListChange]):
        for change in changes:
            if source is self.source:
                if isinstance(change, ActiveListIndexAdded):
                    idx = self.getOffsetForIndex(change.index)
                    for n, v in enumerate(change.newValue):
                        self.target.insert(idx + n, v)
                    change.newValue.addListener(self)
                elif isinstance(change, ActiveListIndexUpdated):
                    change.oldValue.removeListener(self)
                    idx = self.getOffsetForIndex(change.index)
                    del self.target[idx, idx + len(change.oldValue)]
                    for n, v in enumerate(change.newValue):
                        self.target.insert(idx + n, v)
                    change.newValue.addListener(self)
                elif isinstance(change, ActiveListIndexDeleted):
                    change.oldValue.removeListener(self)
                    idx = self.getOffsetForIndex(change.index)
                    del self.target[idx, idx + len(change.oldValue)]
                elif isinstance(change, ActiveListIndexMoved):
                    moved_list = self.source[change.new_index]
                    if change.new_index > change.old_index:
                        old_index = self.getOffsetForIndex(change.old_index)
                        new_index = self.getOffsetForIndex(change.new_index + 1)
                    else:
                        old_index = self.getOffsetForIndex(change.old_index + 1) - 1
                        new_index = self.getOffsetForIndex(change.new_index)
                    for _ in moved_list:
                        self.target.move(old_index, new_index)
            else:
                if isinstance(change, ActiveListIndexAdded):
                    self.target.insert(self.getOffsetFor(source) + change.index, change.newValue)
                elif isinstance(change, ActiveListIndexUpdated):
                    self.target[self.getOffsetFor(source) + change.index] = change.newValue
                elif isinstance(change, ActiveListIndexDeleted):
                    del self.target[self.getOffsetFor(source) + change.index]
                elif isinstance(change, ActiveListIndexMoved):
                    offset = self.getOffsetFor(source)
                    self.target.move(offset + change.old_index, offset + change.new_index)


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
        for listener in self.listeners.copy():
            try:
                listener.onListChange(self, changes)
            except Exception:
                logger.exception("Exception during onListChange notification")

    def remove(self, value):
        self.__delitem__(self.delegate.index(value))

    def insert(self, index, value):
        self.delegate.insert(index, value)
        self.__fireChanges([ActiveListIndexInserted(index, value)])

    def move(self, old_index, new_index):
        self.delegate.insert(new_index, self.delegate.pop(old_index))
        self.__fireChanges([ActiveListIndexMoved(old_index, new_index)])

    def index(self, value):
        return self.delegate.index(value)

    def map(self, transformation: Union[callable, ActiveListTransformation]):
        if not isinstance(transformation, ActiveListTransformation):
            transformation = BasicTransformation(transformation)
        res = ActiveList([transformation.transform(v) for v in self])
        self.addListener(ActiveListTransformationListener(transformation, self, res))
        return res

    def filter(self, filter: Union[callable, ActiveListFilter]):
        if not isinstance(filter, ActiveListFilter):
            filter = BasicFilter(filter)
        res = ActiveList([val for val in self if filter.predicate(val)])
        self.addListener(ActiveListFilterListener(filter, self, res))
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
        if isinstance(key, tuple):
            start, stop = key
            changes = [ActiveListIndexDeleted(start + idx, v) for idx, v in enumerate(self.delegate[start:stop])]
            del self.delegate[start:stop]
            self.__fireChanges(changes)
        else:
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
