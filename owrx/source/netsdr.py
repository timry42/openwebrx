from owrx.source.soapy import SoapyConnectorSource, SoapyConnectorDeviceDescription
from owrx.form.input import Input
from owrx.form.input.device import RemoteInput
from typing import List


class NetsdrSource(SoapyConnectorSource):
    def getEventNames(self):
        return super().getEventNames() + ["remote"]

    def buildSoapyDeviceParameters(self, parsed, values):
        params = super().buildSoapyDeviceParameters(parsed, values)
        params += [{"netsdr": values["remote"]}]
        return params

    def getDriver(self):
        return "netsdr"


class NetsdrDeviceDescription(SoapyConnectorDeviceDescription):
    def getName(self):
        return "NetSDR device"

    def getInputs(self) -> List[Input]:
        return super().getInputs() + [
            RemoteInput()
        ]

    def getDeviceMandatoryKeys(self):
        return super().getDeviceMandatoryKeys() + ["remote"]
