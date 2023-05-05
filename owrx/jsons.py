from owrx.property import PropertyManager
from owrx.active.list import ActiveList
import json


class Encoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, PropertyManager):
            return o.__dict__()
        if isinstance(o, ActiveList):
            return o.__list__()
        return super().default(o)
