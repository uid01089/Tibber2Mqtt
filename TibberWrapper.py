import logging
import asyncio
from typing import Callable
import aiohttp
from tibber import Tibber
from PythonLib.Scheduler import Scheduler


logger = logging.getLogger('TibberWrapper')

TIME_OUT_S = 5


class TibberPriceInfo:
    def __init__(self, token: str, callback: Callable[[dict], None]) -> None:
        self.token = token
        self.task = None
        self.callback = callback

    def execute(self) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._asyncRun())

    async def _asyncRun(self) -> None:
        try:
            async with aiohttp.ClientSession() as session:
                tibber_connection = Tibber(self.token, websession=session, user_agent="Tibber2Mqtt_Query")
                await tibber_connection.update_info()
                home = tibber_connection.get_homes()[0]
                await home.fetch_consumption_data()
                await home.update_info()
                await home.update_price_info()

                self.callback(home.current_price_info)

        except aiohttp.ClientConnectionError as e:
            logging.exception('_1_')
            # Handle the connection error here
        except BaseException as e:
            logging.exception('_2_')


class TibberStreamWrapper:
    def __init__(self, token: str, callback: Callable[[dict], None]) -> None:
        self.token = token
        self.task = None
        self.callback = callback
        self.startTime = 0

    def runStream(self) -> None:
        self.startTime = Scheduler.getSeconds()
        self.task = asyncio.ensure_future(self._asyncRun())
        loop = asyncio.get_event_loop()
        loop.run_forever()

    def loop(self) -> None:

        if self.task is None:
            return

        if Scheduler.getSeconds() - self.startTime > TIME_OUT_S:

            logger.error("Restart TibberStreamWrapper")

            self.task.cancel()
            self.task = None
            self.runStream()

    async def _asyncRun(self) -> None:
        try:
            async with aiohttp.ClientSession() as session:
                tibber_connection = Tibber(self.token, websession=session, user_agent="Tibber2Mqtt_Stream")
                await tibber_connection.update_info()
                home = tibber_connection.get_homes()[0]
                await home.rt_subscribe(self._callback)

        except aiohttp.ClientConnectionError as e:
            logging.exception('_3_')
        except BaseException as e:
            logging.exception('_4_')

        while True:
            await asyncio.sleep(10)

    def _callback(self, pkg):
        data = pkg.get("data")
        if data is None:
            return

        # Reset watchdog
        self.startTime = Scheduler.getSeconds()

        # Provide results
        self.callback(data)
