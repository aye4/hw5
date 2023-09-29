import asyncio
import logging
from websockets import serve
from names import get_full_name
from websockets import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosedOK
from re import search
from datetime import datetime
import platform
from aiopath import AsyncPath
from aiofile import async_open
from console_rates import ExchangeRates

logging.basicConfig(level=logging.INFO)

LOG_EXCHANGE = "exchange.log"
RATE_STR = "Exchange Rates for {}: EUR {} USD {}"


class Server:
    clients = set()
    log_exchange = AsyncPath(LOG_EXCHANGE)

    async def register(self, ws: WebSocketServerProtocol):
        ws.name = get_full_name()
        self.clients.add(ws)
        logging.info(f'{ws.remote_address} connects')

    async def unregister(self, ws: WebSocketServerProtocol):
        self.clients.remove(ws)
        logging.info(f'{ws.remote_address} disconnects')

    async def send_to_clients(self, message: str):
        if self.clients:
            [await client.send(message) for client in self.clients]

    async def ws_handler(self, ws: WebSocketServerProtocol):
        await self.register(ws)
        try:
            await self.distrubute(ws)
        except ConnectionClosedOK:
            pass
        finally:
            await self.unregister(ws)

    async def distrubute(self, ws: WebSocketServerProtocol):
        async for message in ws:
            await self.send_to_clients(f"{ws.name}: {message}")
            if message.lower().startswith("exchange"):
                async with async_open(self.log_exchange, 'a') as f:
                    await f.write(f"{datetime.now()}: {ws.name}: {message}\n")
                await self.show_rates(message[8:])

    async def show_rates(self, days: str):
        days = days[1:] if search(r"\s([1-9]|10)$", days) else "1"
        pb_api = ExchangeRates(days)
        rates = await pb_api.query()
        for dr in rates:
            day = next(iter(dr))
            await self.send_to_clients(
                RATE_STR.format(day, dr[day]['EUR'], dr[day]['USD'])
            )


async def main():
    server = Server()
    async with serve(server.ws_handler, 'localhost', 8080):
        await asyncio.Future()  # run forever

if __name__ == '__main__':
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
