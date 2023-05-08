from owrx.config import Config
from owrx.source import SdrSource
from owrx.feature import FeatureDetector, UnknownFeatureException

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
        def hasProfiles(device):
            return "profiles" in device and device["profiles"] and len(device["profiles"]) > 0

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
                .filter(hasProfiles) \
                .map(buildNewSource)
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
