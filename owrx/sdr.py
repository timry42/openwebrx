from owrx.config import Config
from owrx.source import SdrSource

import logging

logger = logging.getLogger(__name__)


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
    def getSource(id):
        sources = SdrService.getActiveSources()
        if not sources:
            return None
        try:
            return next(s for s in sources if s.getId() == id)
        except StopIteration:
            return None

    @staticmethod
    def getAllSources():
        def buildNewSource(props):
            sdrType = props["type"]
            className = "".join(x for x in sdrType.title() if x.isalnum()) + "Source"
            module = __import__("owrx.source.{0}".format(sdrType), fromlist=[className])
            cls = getattr(module, className)
            return cls(props)

        if SdrService.sources is None:
            SdrService.sources = Config.get()["sdrs"].map(buildNewSource)
        return SdrService.sources

    @staticmethod
    def getActiveSources():
        def isAvailable(source: SdrSource):
            return source.isEnabled() and not source.isFailed()

        if SdrService.activeSources is None:
            SdrService.activeSources = SdrService.getAllSources().filter(isAvailable)
        return SdrService.activeSources

    @staticmethod
    def getAvailableProfiles():
        def buildProfiles(source):
            return source.getProfiles().map(lambda profile: {"id": "{}|{}".format(source.getId(), profile["id"]), "name": "{} {}".format(source.getName(), profile["name"])})

        if SdrService.availableProfiles is None:
            SdrService.availableProfiles = SdrService.getActiveSources().map(buildProfiles).flatten()
        return SdrService.availableProfiles

    @staticmethod
    def stopAllSources():
        for source in SdrService.getAllSources():
            source.stop()
