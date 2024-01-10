import asyncio
import random

from modules.utils import logger
from modules.wallet import Wallet
import settings


class SelfTX(Wallet):
    def __init__(self, wallet: Wallet):
        super().__init__(privatekey=wallet.privatekey, recipient=wallet.recipient, tg_report=wallet.tg_report, browser=wallet.browser, proxy=wallet.proxy)

        self.from_chain = 'zkfair'
        self.web3 = self.get_web3(self.from_chain)


    async def send_tx(self, retry=0):
        await self.wait_for_gwei()

        try:
            module_str = f'self tx'

            tx = {
                'from': self.address,
                'to': self.address,
                'chainId': await self.web3.eth.chain_id,
                'nonce': await self.web3.eth.get_transaction_count(self.address),
                'value': random.randint(1, 100000),
                **await self.get_gas(chain_name=self.from_chain),
            }

            tx_hash = await self.sent_tx(chain_name=self.from_chain, tx=tx, tx_label=module_str, tx_raw=True)
            return True

        except Exception as error:
            if retry < settings.RETRY:
                logger.error(f'{module_str} | {error}')
                await asyncio.sleep(10)
                return await self.send_tx(retry=retry+1)
            else:
                self.tg_report.update_logs(f'❌ {module_str}: {error}')
                raise ValueError(f'{module_str}: {error}')
