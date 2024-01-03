from pathlib import Path
from typing import NoReturn
from tibber import Tibber
import time
import logging
import tibber.const
import asyncio
import aiohttp


import paho.mqtt.client as pahoMqtt
from PythonLib.JsonUtil import JsonUtil
from PythonLib.Mqtt import MQTTHandler, Mqtt
from PythonLib.MqttConfigContainer import MqttConfigContainer
from PythonLib.Scheduler import Scheduler
from PythonLib.DictUtil import DictUtil
from PythonLib.DateUtil import DateTimeUtilities
from TibberWrapper import TibberPriceInfo, TibberStreamWrapper

logger = logging.getLogger('Tibber2Mqtt')


# https://github.com/Danielhiversen/pyTibber/tree/master


class Module:
    def __init__(self) -> None:
        self.scheduler = Scheduler()
        self.mqttClient = Mqtt("koserver.iot", "/house/agents/Tibber2Mqtt", pahoMqtt.Client("Tibber2Mqtt1"))
        self.config = MqttConfigContainer(self.mqttClient, "/house/agents/Tibber2Mqtt/config", Path("tibber2Mqtt.json"), {"Token": "5K4MVS-OjfWhK_4yrjOlFe1F6kJXPVf7eQYggo8ebAE"})
        self.token = None

    def getScheduler(self) -> Scheduler:
        return self.scheduler

    def getMqttClient(self) -> Mqtt:
        return self.mqttClient

    def getToken(self) -> str:
        return self.token

    def setup(self) -> None:

        self.config.setup()
        self.config.subscribeToConfigChange(self.__updateConfig)

        self.scheduler.scheduleEach(self.mqttClient.loop, 500)
        self.scheduler.scheduleEach(self.config.loop, 60000)

    def loop(self) -> None:
        self.scheduler.loop()

    def __updateConfig(self, config: dict) -> None:
        self.token = config['Token']


class Tibber2Mqtt:
    def __init__(self, module: Module) -> None:
        self.token = None
        self.mqttClient = module.getMqttClient()
        self.scheduler = module.getScheduler()
        self.token = module.getToken()
        self.tibberQuery = None
        self.tibberStream = None

    def setup(self) -> None:

        self.tibberQuery = TibberPriceInfo(self.token, self._tibberPriceInfoCallback)
        self.tibberStream = TibberStreamWrapper(self.token, self._tibberStreamCallback)
        self.tibberStream.runStream()
        self.scheduler.scheduleEach(self.tibberStream.loop, 1000)

        self.tibberQuery.execute()

        self.scheduler.scheduleEach(self.tibberQuery.execute, 30 * 60000)  # all 30 min
        self.scheduler.scheduleEach(self.__keepAlive, 10000)

    def _tibberPriceInfoCallback(self, data: dict) -> None:
        valuesForSending = DictUtil.flatDict(data, "priceInfo")
        for value in valuesForSending:
            self.mqttClient.publishOnChange(value[0], str(value[1]))

    def _tibberStreamCallback(self, data: dict) -> None:
        valuesForSending = DictUtil.flatDict(data.get("liveMeasurement"), "liveMeasurement")
        for value in valuesForSending:
            self.mqttClient.publish(value[0], str(value[1]))

    def __keepAlive(self) -> None:
        self.mqttClient.publishIndependentTopic('/house/agents/Tibber2Mqtt/heartbeat', DateTimeUtilities.getCurrentDateString())
        self.mqttClient.publishIndependentTopic('/house/agents/Tibber2Mqtt/subscriptions', JsonUtil.obj2Json(self.mqttClient.getSubscriptionCatalog()))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('Tibber2Mqtt').setLevel(logging.DEBUG)
    logging.getLogger('gql.transport.websockets').setLevel(logging.WARNING)

    module = Module()
    module.setup()

    logging.getLogger('Tibber2Mqtt').addHandler(MQTTHandler(module.getMqttClient(), '/house/agents/Tibber2Mqtt/log'))

    Tibber2Mqtt(module).setup()

    print("Tibber2Mqtt is running")

    while (True):
        module.loop()
        time.sleep(0.25)


if __name__ == '__main__':
    main()
