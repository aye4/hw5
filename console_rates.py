import argparse
import platform
import aiohttp
import asyncio
from datetime import datetime, timedelta

HTTP_STR = "https://api.privatbank.ua/p24api/exchange_rates?date="
CURRENCIES = {"CHF", "CZK", "EUR", "GBP", "PLN", "USD"}

DAYS_ERROR_MSG = "Days should be <int> between 1 and 10"


class ExchangeRates:
    def __init__(self, days: str = "1", currencies: str = "USD,EUR"):
        self.set_days(days)
        self.set_currencies(currencies)

    def set_days(self, days: str):
        self.days = []
        try:
            day_count = int(days)
        except ValueError:
            raise ValueError(DAYS_ERROR_MSG)
        if not 10 >= day_count >= 1:
            raise ValueError(DAYS_ERROR_MSG)
        for d in range(day_count - 1, -1, -1):
            date = datetime.today() - timedelta(days=d)
            self.days.append(date.strftime("%d.%m.%Y"))

    def set_currencies(self, currencies: str):
        self.currencies = set()
        for s in currencies.upper().split(','):
            if s in CURRENCIES:
                self.currencies.add(s)
            else:
                print(f"Currency '{s}' is not available")
        if not self.currencies:
            raise ValueError(f"Valid currencies are: {CURRENCIES}")

    def rates_by_currency(self, data):
        return {
            d['currency']: {
               'sale': d['saleRate'],
               'purchase': d['purchaseRate']
            }
            for d in data["exchangeRate"]
            if d['currency'] in self.currencies
        }

    async def get_rates(self, session, date: str):
        rates = {}
        try:
            async with session.get(HTTP_STR + date) as response:
                if response.ok:
                    data = await response.json()
                    rates = self.rates_by_currency(data)
                else:
                    print(f"Error status: {response.status} for {date}")
        except aiohttp.ClientConnectorError as e:
            print(f'Connection error: {HTTP_STR + date}', str(e))
        return {date: rates}

    async def query(self) -> list[dict]:
        result = []
        async with aiohttp.ClientSession() as session:
            tasks = []
            for date in self.days:
                tasks.append(self.get_rates(session, date))
            result = await asyncio.gather(*tasks, return_exceptions=True)
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exchange Rates (PrivatB)")
    help_curr = "Currency list, e.g. 'USD,EUR'"
    help_days = "Days from the current date (including current date)"
    parser.add_argument("--curr", "-c", default="USD,EUR", help=help_curr)
    parser.add_argument("--days", "-d", default="1", help=help_days)
    args = vars(parser.parse_args())
    try:
        rates = ExchangeRates(args.get("days"), args.get("curr"))
    except ValueError as e:
        exit(str(e))
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    r = asyncio.run(rates.query())
    print(*r, sep="\n")
