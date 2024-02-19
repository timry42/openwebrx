from owrx.feature import FeatureDetector
from owrx.audio import ProfileSource
from functools import reduce
from abc import ABCMeta, abstractmethod
from typing import Dict, List


class Bandpass(object):
    def __init__(self, low_cut, high_cut):
        self.low_cut = low_cut
        self.high_cut = high_cut


class Mode:
    def __init__(self, modulation: str, name: str, bandpass: Bandpass = None, ifRate=None, requirements=None, service=False, squelch=True):
        self.modulation = modulation
        self.name = name
        self.requirements = requirements if requirements is not None else []
        self.service = service
        self.bandpass = bandpass
        self.ifRate = ifRate
        self.squelch = squelch

    def is_available(self):
        fd = FeatureDetector()
        return reduce(lambda a, b: a and b, [fd.is_available(r) for r in self.requirements], True)

    def is_service(self):
        return self.service

    def get_bandpass(self):
        return self.bandpass

    def get_modulation(self):
        return self.modulation


EmptyMode = Mode("empty", "Empty")


class AnalogMode(Mode):
    pass


class DigitalUnderlyingConfig(object):
    def __init__(self, bandpass: Bandpass = None):
        self.bandpass = bandpass


class DigitalMode(Mode):
    def __init__(
        self,
        modulation,
        name,
        bandpass: Bandpass = None,
        ifRate=None,
        requirements=None,
        service=False,
        squelch=True,
        secondaryFft=True,
        configs: List[str] | Dict[str, DigitalUnderlyingConfig] = None,
    ):
        super().__init__(modulation, name, bandpass, ifRate, requirements, service, squelch)
        self.secondaryFft = secondaryFft
        if configs is None:
            self.configs = {}
        elif isinstance(configs, list):
            self.configs = {x: DigitalUnderlyingConfig() for x in configs}
        else:
            self.configs = configs

    def get_underlying_mode(self):
        mode = Modes.findByModulation(list(self.configs.keys())[0])
        if mode is None:
            mode = EmptyMode
        return mode

    def get_bandpass(self):
        if self.bandpass is not None:
            return self.bandpass
        return self.get_underlying_mode().get_bandpass()

    def get_modulation(self):
        return self.get_underlying_mode().get_modulation()

    def for_underlying(self, underlying: str):
        if underlying not in self.configs:
            raise ValueError("{} is not a valid underlying mode for {}".format(underlying, self.modulation))
        config = self.configs[underlying]
        bandpass = self.bandpass if config.bandpass is None else config.bandpass
        return DigitalMode(
            self.modulation,
            self.name,
            bandpass,
            self.ifRate,
            self.requirements,
            self.service,
            self.squelch,
            self.secondaryFft,
            {underlying: self.configs[underlying]}
        )


class AudioChopperMode(DigitalMode, metaclass=ABCMeta):
    def __init__(self, modulation, name, bandpass=None, requirements=None):
        if bandpass is None:
            bandpass = Bandpass(0, 3000)
        super().__init__(modulation, name, bandpass=bandpass, requirements=requirements, service=True, configs=["usb"])

    @abstractmethod
    def get_profile_source(self) -> ProfileSource:
        pass


class WsjtMode(AudioChopperMode):
    def __init__(self, modulation, name, bandpass=None, requirements=None):
        if requirements is None:
            requirements = ["wsjt-x"]
        super().__init__(modulation, name, bandpass=bandpass, requirements=requirements)

    def get_profile_source(self) -> ProfileSource:
        # inline import due to circular dependencies
        from owrx.wsjt import WsjtProfiles
        return WsjtProfiles.getSource(self.modulation)


class Js8Mode(AudioChopperMode):
    def __init__(self, modulation, name, bandpass=None, requirements=None):
        if requirements is None:
            requirements = ["js8call"]
        super().__init__(modulation, name, bandpass, requirements)

    def get_profile_source(self) -> ProfileSource:
        # inline import due to circular dependencies
        from owrx.js8 import Js8ProfileSource
        return Js8ProfileSource()


class Modes(object):
    mappings = [
        AnalogMode("nfm", "FM", bandpass=Bandpass(-4000, 4000)),
        AnalogMode("wfm", "WFM", bandpass=Bandpass(-75000, 75000)),
        AnalogMode("am", "AM", bandpass=Bandpass(-4000, 4000)),
        AnalogMode("lsb", "LSB", bandpass=Bandpass(-3000, -300)),
        AnalogMode("usb", "USB", bandpass=Bandpass(300, 3000)),
        AnalogMode("cw", "CW", bandpass=Bandpass(700, 900)),
        AnalogMode("dmr", "DMR", bandpass=Bandpass(-6250, 6250), requirements=["digital_voice_digiham"], squelch=False),
        AnalogMode(
            "dstar", "D-Star", bandpass=Bandpass(-3250, 3250), requirements=["digital_voice_digiham"], squelch=False
        ),
        AnalogMode("nxdn", "NXDN", bandpass=Bandpass(-3250, 3250), requirements=["digital_voice_digiham"], squelch=False),
        AnalogMode("ysf", "YSF", bandpass=Bandpass(-6250, 6250), requirements=["digital_voice_digiham"], squelch=False),
        AnalogMode("m17", "M17", bandpass=Bandpass(-6250, 6250), requirements=["digital_voice_m17"], squelch=False),
        AnalogMode(
            "freedv", "FreeDV", bandpass=Bandpass(300, 3000), requirements=["digital_voice_freedv"], squelch=False
        ),
        AnalogMode("drm", "DRM", bandpass=Bandpass(-5000, 5000), requirements=["drm"], squelch=False),
        AnalogMode("dab", "DAB", bandpass=None, ifRate=2.048e6, requirements=["dab"], squelch=False),
        DigitalMode("bpsk31", "BPSK31", configs=["usb"]),
        DigitalMode("bpsk63", "BPSK63", configs=["usb"]),
        DigitalMode("rtty170", "RTTY 45/170", configs=["usb", "lsb"]),
        DigitalMode("rtty450", "RTTY 50N/450", configs=["lsb", "usb"]),
        DigitalMode("rtty85", "RTTY 50N/85", configs=["lsb", "usb"]),
        DigitalMode(
            "sstv",
            "SSTV",
            configs={
                "usb": DigitalUnderlyingConfig(bandpass=Bandpass(1100, 2400)),
                "lsb": DigitalUnderlyingConfig(bandpass=Bandpass(-2400, -1100)),
            },
            bandpass=Bandpass(1100, 2400),
            requirements=["sstv"],
            service=True
        ),
        WsjtMode("ft8", "FT8"),
        WsjtMode("ft4", "FT4"),
        WsjtMode("jt65", "JT65"),
        WsjtMode("jt9", "JT9"),
        WsjtMode("wspr", "WSPR", bandpass=Bandpass(1350, 1650)),
        WsjtMode("fst4", "FST4", requirements=["wsjt-x-2-3"]),
        WsjtMode("fst4w", "FST4W", bandpass=Bandpass(1350, 1650), requirements=["wsjt-x-2-3"]),
        WsjtMode("q65", "Q65", requirements=["wsjt-x-2-4"]),
        DigitalMode("msk144", "MSK144", requirements=["msk144"], configs=["usb"], service=True),
        Js8Mode("js8", "JS8Call"),
        DigitalMode(
            "packet",
            "Packet",
            configs=["nfm", "usb", "lsb"],
            bandpass=Bandpass(-6250, 6250),
            requirements=["packet"],
            service=True,
            squelch=False,
        ),
        DigitalMode(
            "pocsag",
            "Pocsag",
            configs=["nfm"],
            bandpass=Bandpass(-6250, 6250),
            requirements=["pocsag"],
            service=True,
            squelch=False,
        ),
        DigitalMode(
            "adsb",
            "ADS-B",
            configs=["empty"],
            bandpass=None,
            ifRate=2.4e6,
            requirements=["dump1090"],
            service=True,
            squelch=False,
            secondaryFft=False,
        ),
        DigitalMode(
            "ism",
            "ISM",
            configs=["empty"],
            bandpass=Bandpass(-125000, 125000),
            requirements=["ism"],
            service=True,
            squelch=False,
        ),
        DigitalMode(
            "hfdl",
            "HFDL",
            configs=["empty"],
            bandpass=Bandpass(0, 3000),
            requirements=["dumphfdl"],
            service=True,
            squelch=False,
        ),
        DigitalMode(
            "vdl2",
            "VDL2",
            configs=["empty"],
            bandpass=Bandpass(-12500, 12500),
            requirements=["dumpvdl2"],
            service=True,
            squelch=False,
        )
    ]

    @staticmethod
    def getModes():
        return Modes.mappings

    @staticmethod
    def getAvailableModes():
        return [m for m in Modes.getModes() if m.is_available()]

    @staticmethod
    def getAvailableServices():
        return [m for m in Modes.getAvailableModes() if m.is_service()]

    @staticmethod
    def findByModulation(modulation):
        modes = [m for m in Modes.getAvailableModes() if m.modulation == modulation]
        if modes:
            return modes[0]
