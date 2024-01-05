from pathlib import Path
import logging
import asyncio


import paho.mqtt.client as pahoMqtt
from PythonLib.JsonUtil import JsonUtil
from PythonLib.AsyncMqtt import AsyncMQTTHandler, AsyncMqtt
from PythonLib.AsyncMqttConfigContainer import AsyncMqttConfigContainer
from PythonLib.AsyncScheduler import AsyncScheduler
from PythonLib.DictUtil import DictUtil
from PythonLib.DateUtil import DateTimeUtilities
from TibberWrapper import TibberWrapper

logger = logging.getLogger('Tibber2Mqtt')


# https://github.com/Danielhiversen/pyTibber/tree/master


class Module:
    def __init__(self) -> None:
        self.scheduler = AsyncScheduler()
        self.mqttClient = AsyncMqtt("koserver.iot", "/house/agents/Tibber2Mqtt", pahoMqtt.Client("Tibber2Mqtt"))
        self.config = AsyncMqttConfigContainer(
            self.mqttClient, "/house/agents/Tibber2Mqtt/config", Path("tibber2Mqtt.json"),
            {"Token": "5K4MVS-OjfWhK_4yrjOlFe1F6kJXPVf7eQYggo8ebAE"})
        self.token = None

    async def getScheduler(self) -> AsyncScheduler:
        return self.scheduler

    async def getMqttClient(self) -> AsyncMqtt:
        return self.mqttClient

    async def getToken(self) -> str:
        return self.token

    async def setup(self) -> None:

        await self.mqttClient.connectAndRun()
        await self.config.setup()
        await self.config.subscribeToConfigChange(self.__updateConfig)
        await self.scheduler.scheduleEach(self.config.loop, 60000)

    async def __updateConfig(self, config: dict) -> None:
        self.token = config['Token']


class Tibber2Mqtt:
    def __init__(self, module: Module) -> None:
        self.token = None
        self.mqttClient = None
        self.scheduler = None
        self.token = None
        self.tibberQuery = None
        self.tibberStream = None
        self.tibberWrapper = None

        self.module = module

    async def setup(self) -> None:

        self.mqttClient = await self.module.getMqttClient()
        self.scheduler = await self.module.getScheduler()
        self.token = await self.module.getToken()

        self.tibberWrapper = TibberWrapper(self.token, self._tibberPriceInfoCallback, self._tibberStreamCallback)
        await self.tibberWrapper.execute()

        await self.scheduler.scheduleEach(self.__keepAlive, 10000)

    async def _tibberPriceInfoCallback(self, data: dict) -> None:
        valuesForSending = DictUtil.flatDict(data, "priceInfo")
        for value in valuesForSending:
            await self.mqttClient.publishOnChange(value[0], str(value[1]))

    async def _tibberStreamCallback(self, data: dict) -> None:
        valuesForSending = DictUtil.flatDict(data.get("liveMeasurement"), "liveMeasurement")
        for value in valuesForSending:
            await self.mqttClient.publish(value[0], str(value[1]))

    async def __keepAlive(self) -> None:
        await self.mqttClient.publishIndependentTopic('/house/agents/Tibber2Mqtt/heartbeat', DateTimeUtilities.getCurrentDateString())
        await self.mqttClient.publishIndependentTopic('/house/agents/Tibber2Mqtt/subscriptions', JsonUtil.obj2Json(await self.mqttClient.getSubscriptionCatalog()))


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('Tibber2Mqtt').setLevel(logging.DEBUG)
    logging.getLogger('gql.transport.websockets').setLevel(logging.WARNING)

    module = Module()
    await module.setup()

    logging.getLogger('Tibber2Mqtt').addHandler(AsyncMQTTHandler(module.getMqttClient(), '/house/agents/Tibber2Mqtt/log'))

    tibber2Mqtt = Tibber2Mqtt(module)
    await tibber2Mqtt.setup()

    while True:
        await asyncio.sleep(1)


if __name__ == '__main__':

    asyncio.run(main())
