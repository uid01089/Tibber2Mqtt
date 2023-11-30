from pathlib import Path
import time
import os
import logging
import requests


import paho.mqtt.client as pahoMqtt
from PythonLib.JsonUtil import JsonUtil
from PythonLib.Mqtt import MQTTHandler, Mqtt
from PythonLib.MqttConfigContainer import MqttConfigContainer
from PythonLib.Scheduler import Scheduler
from PythonLib.DictUtil import DictUtil
from PythonLib.DateUtil import DateTimeUtilities

logger = logging.getLogger('Tibber2Mqtt')


_QUERY = """
{
  viewer {
    homes {
      currentSubscription{
        priceInfo{
          current{
            total
            energy
            tax
            startsAt
          }
          today {
            total
            energy
            tax
            startsAt
          }
          tomorrow {
            total
            energy
            tax
            startsAt
          }
        }
      }
    }
  }
}
"""


# TOKEN = os.environ.get("TOKEN") or "5K4MVS-OjfWhK_4yrjOlFe1F6kJXPVf7eQYggo8ebAE"


class Module:
    def __init__(self) -> None:
        self.scheduler = Scheduler()
        self.mqttClient = Mqtt("koserver.iot", "/house/agents/Tibber2Mqtt", pahoMqtt.Client("Tibber2Mqtt"))
        self.config = MqttConfigContainer(self.mqttClient, "/house/agents/Tibber2Mqtt/config", Path("tibber2Mqtt.json"), {"Token": "5K4MVS-OjfWhK_4yrjOlFe1F6kJXPVf7eQYggo8ebAE"})

    def getScheduler(self) -> Scheduler:
        return self.scheduler

    def getConfig(self) -> MqttConfigContainer:
        return self.config

    def getMqttClient(self) -> Mqtt:
        return self.mqttClient

    def setup(self) -> None:
        self.scheduler.scheduleEach(self.mqttClient.loop, 500)
        self.scheduler.scheduleEach(self.config.loop, 60000)

    def loop(self) -> None:
        self.scheduler.loop()


class Tibber2Mqtt:
    def __init__(self, module: Module) -> None:
        self.token = None
        self.mqttClient = module.getMqttClient()
        self.scheduler = module.getScheduler()
        self.config = module.getConfig()

    def __updateIncludePattern(self, config: dict) -> None:
        self.token = config['Token']

    def setup(self) -> None:

        self.config.setup()
        self.config.subscribeToConfigChange(self.__updateIncludePattern)

        self.scheduler.scheduleEach(self.mirrorToMqtt, 10000)
        self.scheduler.scheduleEach(self.__keepAlive, 10000)

    def readData(self) -> dict:

        responseObj = {}

        try:
            response = requests.post('https://api.tibber.com/v1-beta/gql',
                                     json={'query': _QUERY},
                                     headers={'Content-Type': 'application/json', 'Authorization': 'Bearer {}'.format(self.token)}, timeout=10)

            responseObj = response.json()

        except BaseException:
            logging.exception('')

        return responseObj

    def mirrorToMqtt(self) -> None:

        priceData = self.readData()['data']['viewer']['homes'][0]['currentSubscription']['priceInfo']

        valuesForSending = DictUtil.flatDict(priceData, "priceInfo")
        # print (valuesForSending)

        for value in valuesForSending:
            self.mqttClient.publishOnChange(value[0], str(value[1]))

    def __keepAlive(self) -> None:
        self.mqttClient.publishIndependentTopic('/house/agents/Tibber2Mqtt/heartbeat', DateTimeUtilities.getCurrentDateString())
        self.mqttClient.publishIndependentTopic('/house/agents/Tibber2Mqtt/subscriptions', JsonUtil.obj2Json(self.mqttClient.getSubscriptionCatalog()))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('Tibber2Mqtt').setLevel(logging.DEBUG)

    module = Module()
    module.setup()

    logging.getLogger('Tibber2Mqtt').addHandler(MQTTHandler(module.getMqttClient(), '/house/agents/Tibber2Mqtt/log'))

    Tibber2Mqtt(module).setup()

    while (True):
        module.loop()
        time.sleep(0.25)


if __name__ == '__main__':
    main()
