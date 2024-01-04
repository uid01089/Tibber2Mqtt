import asyncio
import os
import sys
import aiomqtt


async def sleep(seconds):
    while True:
        # Some other task that needs to run concurrently
        await asyncio.sleep(seconds)
        print(f"Slept for {seconds} seconds!")


async def listen():
    async with aiomqtt.Client("koserver.iot") as client:
        async with client.messages() as messages:
            # await client.subscribe("/house/#")
            async for message in messages:
                print(message.payload)


async def main():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(sleep(2))
        tg.create_task(listen())  # Start the listener task
        tg.create_task(sleep(3))
        tg.create_task(sleep(1))


# Change to the "Selector" event loop if platform is Windows
if sys.platform.lower() == "win32" or os.name.lower() == "nt":
    from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy
    set_event_loop_policy(WindowsSelectorEventLoopPolicy())

asyncio.run(main())
