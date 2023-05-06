from owrx.config.core import CoreConfig
from owrx.config.migration import Migrator
from owrx.property import PropertyLayer, PropertyDeleted
from owrx.active.list import ActiveList
from owrx.jsons import Encoder
import json


class DynamicConfig(PropertyLayer):
    def __init__(self):
        super().__init__()
        try:
            with open(DynamicConfig._getSettingsFile(), "r") as f:
                for k, v in json.load(f).items():
                    self[k] = DynamicConfig._toValue(v)
        except FileNotFoundError:
            pass
        Migrator.migrate(self)

    @staticmethod
    def _toValue(value):
        if isinstance(value, dict):
            layer = PropertyLayer()
            for k, v in value.items():
                layer[k] = DynamicConfig._toValue(v)
            return layer
        if isinstance(value, list):
            return ActiveList([DynamicConfig._toValue(item) for item in value])
        return value

    @staticmethod
    def _getSettingsFile():
        coreConfig = CoreConfig()
        return "{data_directory}/settings.json".format(data_directory=coreConfig.get_data_directory())

    def store(self):
        # don't write directly to file to avoid corruption on exceptions
        jsonContent = json.dumps(self.__dict__(), indent=4, cls=Encoder)
        with open(DynamicConfig._getSettingsFile(), "w") as file:
            file.write(jsonContent)

    def __delitem__(self, key):
        self.__setitem__(key, PropertyDeleted)

    def __contains__(self, item):
        if not super().__contains__(item):
            return False
        if super().__getitem__(item) is PropertyDeleted:
            return False
        return True

    def __getitem__(self, item):
        if self.__contains__(item):
            return super().__getitem__(item)
        raise KeyError('Key "{key}" does not exist'.format(key=item))

    def __dict__(self):
        return {k: v for k, v in super().__dict__().items() if v is not PropertyDeleted}

    def keys(self):
        return [k for k in super().keys() if self.__contains__(k)]
