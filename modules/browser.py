from pyuseragents import random as random_ua
from requests import get
from aiohttp import ClientSession
import asyncio

from modules.utils import logger
from modules.wallet import Wallet


class Browser:
    def __init__(self):
        self.proxies = None

    async def create_session(self, proxy: str):
        self.max_retries = 5
        self.session = ClientSession()
        self.session.headers['user-agent'] = random_ua()
        if proxy:
            await self.change_ip(proxy=proxy)
            # self.proxies = {'http': proxy.split(",")[0], 'https': proxy.split(",")[0]}
            self.proxies = proxy.split(",")[0]
        else:
            logger.warning('You are not using proxy')


    async def change_ip(self, proxy: str):
        if len(proxy.split(",")) > 1:
            while True:
                r = await self.session.get(proxy.split(",")[1])
                if r.status == 200:
                    logger.info(f'[+] Proxy | Changed ip: {await r.text()}')
                    return True
                logger.warning(f'[•] Proxy | Change IP error: {await r.text()} | {r.status} {r.reason}')
                await asyncio.sleep(10)


    def get_eth_price(self):
        r = get('https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT')
        return float(r.json()['price'])


    async def get_izumi_eth_price(self):
        url = 'https://api.izumi.finance/api/v1/izi_swap/summary_record/?chain_id=42766&contract_addr=0x4b21b980d0Dc7D3C0C6175b0A412694F3A1c7c6b&type=7&page_size=90'
        r = await self.session.get(url, proxy=self.proxies)

        r_json = await r.json()
        return round(r_json['data'][0]['price'], 2)


    async def get_zkfair_rewards(self, wallet: Wallet):
        zkfair_data = wallet.get_zkfair_signature()

        # REFUNDABLE
        url = 'https://airdrop.zkfair.io/api/refundable'
        params = {
            'address': zkfair_data["address"],
            'API-SIGNATURE': zkfair_data["API-SIGNATURE"],
            'TIMESTAMP': zkfair_data["TIMESTAMP"],
        }

        r = await self.session.get(url, params=params, proxy=self.proxies)

        try:
            if r.status == 403:
                logger.warning(f'{wallet.address} | Get response refundable 403 error, sleeping 10 secs')
                await asyncio.sleep(10)
                return await self.get_zkfair_rewards(wallet=wallet)
            r_json = await r.json()
        except Exception as err:
            logger.warning(f'get response refundable error: {err}\nreponse: {await r.text()}')
            return await self.get_zkfair_rewards(wallet=wallet)

        phases_data = r_json.get("data")

        # REWARDS
        url = "https://airdrop.zkfair.io/api/airdrop"
        r = await self.session.get(url, params=params, proxy=self.proxies)

        try:
            if r.status == 403:
                logger.warning(f'{wallet.address} | Get response airdrop 403 error, sleeping 10 secs')
                await asyncio.sleep(10)
                return await self.get_zkfair_rewards(wallet=wallet)
            r_json = await r.json()
        except Exception as err:
            logger.warning(f'get response airdrop error: {err}\nreponse: {await r.text()}')
            return await self.get_zkfair_rewards(wallet=wallet)

        if r_json["data"]["account_profit"] == "": airdrop_data = None
        else: airdrop_data = r_json["data"]

        return {'airdrop_data': airdrop_data, 'phases_data': phases_data}


    async def get_refund_merkle(self, wallet: Wallet, phase_num: int):
        zkfair_data = wallet.get_zkfair_signature()

        # REFUNDABLE
        url = 'https://airdrop.zkfair.io/api/refund_merkle'
        params = {
            'address': zkfair_data["address"],
            'API-SIGNATURE': zkfair_data["API-SIGNATURE"],
            'TIMESTAMP': zkfair_data["TIMESTAMP"],
            'phase': int(phase_num),
        }

        r = await self.session.get(url, params=params, proxy=self.proxies)

        try:
            if r.status == 403:
                logger.warning(f'{wallet.address} | Get response refund merkle 403 error, sleeping 10 secs')
                await asyncio.sleep(10)
                return await self.get_refund_merkle(wallet=wallet, phase_num=phase_num)
            r_json = await r.json()
        except Exception as err:
            logger.warning(f'get response refund merkle error: {err}\nreponse: {await r.text()}')
            return await self.get_refund_merkle(wallet=wallet, phase_num=phase_num)

        return r_json["data"]["proof"]


    async def get_airdrop_merkle(self, wallet: Wallet):
        zkfair_data = wallet.get_zkfair_signature()

        # REFUNDABLE
        url = 'https://airdrop.zkfair.io/api/airdrop_merkle'
        params = {
            'address': zkfair_data["address"],
            'API-SIGNATURE': zkfair_data["API-SIGNATURE"],
            'TIMESTAMP': zkfair_data["TIMESTAMP"],
        }

        r = await self.session.get(url, params=params, proxy=self.proxies)

        try:
            if r.status == 403:
                logger.warning(f'{wallet.address} | Get response airdrop merkle 403 error, sleeping 10 secs')
                await asyncio.sleep(10)
                return await self.get_airdrop_merkle(wallet=wallet)
            r_json = await r.json()
        except Exception as err:
            logger.warning(f'get response airdrop merkle error: {err}\nreponse: {await r.text()}')
            return await self.get_airdrop_merkle(wallet=wallet)

        return r_json["data"]["proof"]
