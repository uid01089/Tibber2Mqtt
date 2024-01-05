import logging
import asyncio
from typing import Callable
import aiohttp
from tibber import Tibber


logger = logging.getLogger('TibberWrapper')


class TibberWrapper:
    def __init__(self, token: str, priceInfoCallBack: Callable[[dict], None], rtDataCallBack: Callable[[dict], None]) -> None:
        self.token = token
        self.priceInfoCallBack = priceInfoCallBack
        self.rtDataCallBack = rtDataCallBack
        self.background_tasks = set()

    async def execute(self) -> None:
        task = asyncio.create_task(self.__asyncRun())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.remove)

    async def __asyncRun(self) -> None:
        async with aiohttp.ClientSession() as session:
            tibber_connection = Tibber(self.token, websession=session, user_agent="Tibber2Mqtt_Stream")
            await tibber_connection.update_info()
            home = tibber_connection.get_homes()[0]

            await home.rt_subscribe(self._syncCallback)
            await asyncio.sleep(5)
            home.rt_unsubscribe()

            while True:

                await home.fetch_consumption_data()
                await home.update_info()
                await home.update_price_info()
                await self.priceInfoCallBack(home.current_price_info)
                await asyncio.sleep(1)
                await home.rt_resubscribe()
                await asyncio.sleep(15 * 60)
                home.rt_unsubscribe()
                await asyncio.sleep(1)

    def _syncCallback(self, pkg):
        data = pkg.get("data")
        if data is None:
            return

        # Provide results
        task = asyncio.create_task(self.rtDataCallBack(data))
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.remove)
