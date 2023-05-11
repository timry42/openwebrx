from owrx.config import Config
from owrx.source import SdrSourceEventClient
from owrx.feature import FeatureDetector, UnknownFeatureException
from owrx.active.list import ActiveListTransformation, ActiveListFilter, ActiveListListener, ActiveList, ActiveListChange

import logging

logger = logging.getLogger(__name__)


class ProfileNameMapper(ActiveListTransformation):
    def __init__(self, source_id, source_name):
        self.source_id = source_id
        self.source_name = source_name
        self.subscriptions = {}

    def transform(self, profile):
        return {"id": "{}|{}".format(self.source_id, profile["id"]), "name": "{} {}".format(self.source_name, profile["name"])}

    def monitor(self, profile, callback: callable):
        self.subscriptions[id(profile)] = profile.filter("name").wire(lambda _: callback())

    def unmonitor(self, profile):
        self.subscriptions[id(profile)].cancel()


class ProfileMapper(ActiveListTransformation):
    def __init__(self):
        self.subscriptions = {}

    def transform(self, source):
        return source.getProfiles().map(ProfileNameMapper(source.getId(), source.getName()))

    def monitor(self, source, callback: callable):
        self.subscriptions[id(source)] = source.getProps().filter("name").wire(lambda _: callback())

    def unmonitor(self, source):
        self.subscriptions[id(source)].cancel()


class ProfileChangeListener(ActiveListListener):
    def __init__(self, callback: callable):
        self.callback = callback

    def onListChange(self, source: ActiveList, changes: list[ActiveListChange]):
        self.callback()


class HasProfilesFilter(ActiveListFilter):
    def __init__(self):
        self.monitors = {}

    def predicate(self, device) -> bool:
        return "profiles" in device and device["profiles"] and len(device["profiles"]) > 0

    def monitor(self, device, callback: callable):
        self.monitors[id(device)] = monitor = ProfileChangeListener(callback)
        device["profiles"].addListener(monitor)

    def unmonitor(self, device):
        device["profiles"].removeListener(self.monitors[id(device)])


class SourceIsEnabledListener(SdrSourceEventClient):
    def __init__(self, callback: callable):
        self.callback = callback

    def onEnable(self):
        self.callback()

    def onDisable(self):
        self.callback()


class SourceIsEnabledFilter(ActiveListFilter):
    def __init__(self):
        self.monitors = {}

    def predicate(self, source) -> bool:
        return source.isEnabled()

    def monitor(self, source, callback: callable):
        self.monitors[id(source)] = monitor = SourceIsEnabledListener(callback)
        source.addClient(monitor)

    def unmonitor(self, source):
        source.removeClient(self.monitors[id(source)])


class SourceIsNotFailedListener(SdrSourceEventClient):
    def __init__(self, callback: callable):
        self.callback = callback

    def onFail(self):
        self.callback()


class SourceIsNotFailedFilter(ActiveListFilter):
    def __init__(self):
        self.monitors = {}

    def predicate(self, source) -> bool:
        return not source.isFailed()

    def monitor(self, source, callback: callable):
        self.monitors[id(source)] = monitor = SourceIsNotFailedListener(callback)
        source.addClient(monitor)

    def unmonitor(self, source):
        source.removeClient(self.monitors[id(source)])


class SdrService(object):
    sources = None
    activeSources = None
    availableProfiles = None

    @staticmethod
    def getFirstSource():
        sources = SdrService.getActiveSources()
        if not sources:
            return None
        # TODO: configure default sdr in config? right now it will pick the first one off the list.
        return sources[0]

    @staticmethod
    def _findSource(sources, id):
        if not sources:
            return None
        try:
            return next(s for s in sources if s.getId() == id)
        except StopIteration:
            return None

    @staticmethod
    def getActiveSource(id):
        return SdrService._findSource(SdrService.getActiveSources(), id)

    @staticmethod
    def getSource(id):
        return SdrService._findSource(SdrService.getAllSources(), id)

    @staticmethod
    def getAllSources():
        def sdrTypeAvailable(value):
            featureDetector = FeatureDetector()
            try:
                if not featureDetector.is_available(value["type"]):
                    logger.error(
                        'The SDR source type "{0}" is not available. please check the feature report for details.'.format(
                            value["type"]
                        )
                    )
                    return False
                return True
            except UnknownFeatureException:
                logger.error(
                    'The SDR source type "{0}" is invalid. Please check your configuration'.format(value["type"])
                )
                return False

        def buildNewSource(props):
            sdrType = props["type"]
            className = "".join(x for x in sdrType.title() if x.isalnum()) + "Source"
            module = __import__("owrx.source.{0}".format(sdrType), fromlist=[className])
            cls = getattr(module, className)
            return cls(props)

        if SdrService.sources is None:
            SdrService.sources = Config.get()["sdrs"] \
                .filter(sdrTypeAvailable) \
                .filter(HasProfilesFilter()) \
                .map(buildNewSource)
        return SdrService.sources

    @staticmethod
    def getActiveSources():
        if SdrService.activeSources is None:
            SdrService.activeSources = SdrService.getAllSources() \
                .filter(SourceIsEnabledFilter()) \
                .filter(SourceIsNotFailedFilter())
        return SdrService.activeSources

    @staticmethod
    def getAvailableProfiles():
        if SdrService.availableProfiles is None:
            SdrService.availableProfiles = SdrService.getActiveSources().map(ProfileMapper()).flatten()
        return SdrService.availableProfiles

    @staticmethod
    def stopAllSources():
        for source in SdrService.getAllSources():
            source.stop()
