import logging
import asyncio
from typing import Callable
import aiohttp
from tibber import Tibber
from PythonLib.Scheduler import Scheduler


logger = logging.getLogger('TibberWrapper')

TIME_OUT_S = 20


class TibberPriceInfo:
    def __init__(self, token: str, callback: Callable[[dict], None]) -> None:
        self.token = token
        self.task = None
        self.callback = callback
        self.background_tasks = set()

    async def execute(self) -> None:
        task = asyncio.create_task(self._asyncRun())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.remove)

    async def _asyncRun(self) -> None:
        try:
            async with aiohttp.ClientSession() as session:
                tibber_connection = Tibber(self.token, websession=session, user_agent="Tibber2Mqtt_Query")
                await tibber_connection.update_info()
                home = tibber_connection.get_homes()[0]
                await home.fetch_consumption_data()
                await home.update_info()
                await home.update_price_info()
                await self.callback(home.current_price_info)

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
        self.background_tasks = set()

    async def runStream(self) -> None:

        self.startTime = Scheduler.getSeconds()

        task = asyncio.create_task(self._asyncRun())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.remove)

    async def loop(self) -> None:

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
                await home.rt_subscribe(self._syncCallback)

        except aiohttp.ClientConnectionError as e:
            logging.exception('_3_')
        except BaseException as e:
            logging.exception('_4_')

        while True:
            await asyncio.sleep(10)

    def _syncCallback(self, pkg):
        data = pkg.get("data")
        if data is None:
            return

        # Reset watchdog
        self.startTime = Scheduler.getSeconds()

        # Provide results
        task = asyncio.create_task(self.callback(data))
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.remove)
