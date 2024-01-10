from random import uniform
from time import time
import asyncio

from modules.utils import logger
from modules.wallet import Wallet
from modules import config
import settings


class Izumi(Wallet):
    def __init__(self, wallet: Wallet):
        super().__init__(privatekey=wallet.privatekey, recipient=wallet.recipient, tg_report=wallet.tg_report, browser=wallet.browser, proxy=wallet.proxy)

        self.chain = 'zkfair'
        self.web3 = self.get_web3(self.chain)
        self.izumi_contract = self.web3.eth.contract(address=self.web3.to_checksum_address('0x02F55D53DcE23B4AA962CC68b0f685f26143Bdb2'),
                                                        abi='[{"inputs":[{"internalType":"address","name":"_factory","type":"address"},{"internalType":"address","name":"_weth","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},{"inputs":[],"name":"WETH9","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function","constant":true,"signature":"0x4aa4a4fc"},{"inputs":[],"name":"factory","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function","constant":true,"signature":"0xc45a0155"},{"inputs":[{"internalType":"bytes[]","name":"data","type":"bytes[]"}],"name":"multicall","outputs":[{"internalType":"bytes[]","name":"results","type":"bytes[]"}],"stateMutability":"payable","type":"function","payable":true,"signature":"0xac9650d8"},{"inputs":[{"internalType":"address","name":"tokenX","type":"address"},{"internalType":"address","name":"tokenY","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"}],"name":"pool","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function","constant":true,"signature":"0xbecbcc6a"},{"inputs":[],"name":"refundETH","outputs":[],"stateMutability":"payable","type":"function","payable":true,"signature":"0x12210e8a"},{"inputs":[{"components":[{"internalType":"bytes","name":"path","type":"bytes"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint128","name":"amount","type":"uint128"},{"internalType":"uint256","name":"minAcquired","type":"uint256"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"internalType":"structSwap.SwapAmountParams","name":"params","type":"tuple"}],"name":"swapAmount","outputs":[{"internalType":"uint256","name":"cost","type":"uint256"},{"internalType":"uint256","name":"acquire","type":"uint256"}],"stateMutability":"payable","type":"function","payable":true,"signature":"0x75ceafe6"},{"inputs":[{"components":[{"internalType":"bytes","name":"path","type":"bytes"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint128","name":"desire","type":"uint128"},{"internalType":"uint256","name":"maxPayed","type":"uint256"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"internalType":"structSwap.SwapDesireParams","name":"params","type":"tuple"}],"name":"swapDesire","outputs":[{"internalType":"uint256","name":"cost","type":"uint256"},{"internalType":"uint256","name":"acquire","type":"uint256"}],"stateMutability":"payable","type":"function","payable":true,"signature":"0x115ff67e"},{"inputs":[{"components":[{"internalType":"address","name":"tokenX","type":"address"},{"internalType":"address","name":"tokenY","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"int24","name":"boundaryPt","type":"int24"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint128","name":"amount","type":"uint128"},{"internalType":"uint256","name":"maxPayed","type":"uint256"},{"internalType":"uint256","name":"minAcquired","type":"uint256"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"internalType":"structSwap.SwapParams","name":"swapParams","type":"tuple"}],"name":"swapX2Y","outputs":[],"stateMutability":"payable","type":"function","payable":true,"signature":"0x46edd9c8"},{"inputs":[{"internalType":"uint256","name":"x","type":"uint256"},{"internalType":"uint256","name":"y","type":"uint256"},{"internalType":"bytes","name":"data","type":"bytes"}],"name":"swapX2YCallback","outputs":[],"stateMutability":"nonpayable","type":"function","signature":"0x18780684"},{"inputs":[{"components":[{"internalType":"address","name":"tokenX","type":"address"},{"internalType":"address","name":"tokenY","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"int24","name":"boundaryPt","type":"int24"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint128","name":"amount","type":"uint128"},{"internalType":"uint256","name":"maxPayed","type":"uint256"},{"internalType":"uint256","name":"minAcquired","type":"uint256"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"internalType":"structSwap.SwapParams","name":"swapParams","type":"tuple"}],"name":"swapX2YDesireY","outputs":[],"stateMutability":"payable","type":"function","payable":true,"signature":"0xf3da61a9"},{"inputs":[{"components":[{"internalType":"address","name":"tokenX","type":"address"},{"internalType":"address","name":"tokenY","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"int24","name":"boundaryPt","type":"int24"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint128","name":"amount","type":"uint128"},{"internalType":"uint256","name":"maxPayed","type":"uint256"},{"internalType":"uint256","name":"minAcquired","type":"uint256"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"internalType":"structSwap.SwapParams","name":"swapParams","type":"tuple"}],"name":"swapY2X","outputs":[],"stateMutability":"payable","type":"function","payable":true,"signature":"0x247ec02c"},{"inputs":[{"internalType":"uint256","name":"x","type":"uint256"},{"internalType":"uint256","name":"y","type":"uint256"},{"internalType":"bytes","name":"data","type":"bytes"}],"name":"swapY2XCallback","outputs":[],"stateMutability":"nonpayable","type":"function","signature":"0xd3e1c284"},{"inputs":[{"components":[{"internalType":"address","name":"tokenX","type":"address"},{"internalType":"address","name":"tokenY","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"int24","name":"boundaryPt","type":"int24"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint128","name":"amount","type":"uint128"},{"internalType":"uint256","name":"maxPayed","type":"uint256"},{"internalType":"uint256","name":"minAcquired","type":"uint256"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"internalType":"structSwap.SwapParams","name":"swapParams","type":"tuple"}],"name":"swapY2XDesireX","outputs":[],"stateMutability":"payable","type":"function","payable":true,"signature":"0x826377f6"},{"inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"uint256","name":"minAmount","type":"uint256"},{"internalType":"address","name":"recipient","type":"address"}],"name":"sweepToken","outputs":[],"stateMutability":"payable","type":"function","payable":true,"signature":"0xdf2ab5bb"},{"inputs":[{"internalType":"uint256","name":"minAmount","type":"uint256"},{"internalType":"address","name":"recipient","type":"address"}],"name":"unwrapWETH9","outputs":[],"stateMutability":"payable","type":"function","payable":true,"signature":"0x49404b7c"},{"stateMutability":"payable","type":"receive","payable":true}]')


    async def swap(self, retry=0):
        try:
            module_str = f'izumi swap'

            usdc_balance = await self.get_balance(chain_name=self.chain, human=True)
            if usdc_balance < settings.LEAVE_BALANCE:
                raise Exception(f'✅ Current USDC balance: {round(usdc_balance, 2)} lower than {settings.LEAVE_BALANCE}. Ending work.')

            await self.wait_for_gwei()

            eth_balance = await self.get_balance(chain_name=self.chain, token_name='ETH', human=False)
            if eth_balance > 0:
                from_token = 'ETH'
                to_token = 'USDC'
            else:
                from_token = 'USDC'
                to_token = 'ETH'


            module_str = f'*izumi swap {from_token} -> {to_token}'
            price = await self.browser.get_izumi_eth_price()

            if from_token == 'USDC':
                amount_to_send = round(uniform(settings.TO_BUY_TOKEN[0], settings.TO_BUY_TOKEN[1]), 2)
                value_to_send = int(amount_to_send * 10 ** 18)
                tx_value = value_to_send

                value_to_receive = int(value_to_send / price * (1 - settings.SLIPPAGE / 100))
                amount_to_receive = round(value_to_receive / 10 ** 18, 6)

                module_str = f'izumi swap {amount_to_send} {from_token} -> {amount_to_receive} {to_token}'
            elif from_token == "ETH":
                tx_value = 0
                eth_balance_amount = round(eth_balance / 10 ** 18, 6)

                value_to_receive = int(eth_balance * price * (1 - settings.SLIPPAGE / 100))
                amount_to_receive = round(value_to_receive / 10 ** 18, 6)

                module_str = f'izumi swap {eth_balance_amount} {from_token} -> {amount_to_receive} {to_token}'

                await self.approve(chain_name=self.chain, token_name=from_token, spender=self.izumi_contract.address, value=eth_balance)

            # path_connector = f'00' \
            #                  f'{hex(contract_fee // 4096 % 16)[2:]}' \
            #                  f'{hex(contract_fee // 256 % 16)[2:]}' \
            #                  f'{hex(contract_fee // 16 % 16)[2:]}' \
            #                  f'{hex(contract_fee % 16)[2:]}'
            path_connector = '000bb8'
            path = config.TOKEN_ADDRESSES[from_token] + path_connector + config.TOKEN_ADDRESSES[to_token][2:]

            multicall_bytes = []
            if from_token == 'USDC':
                p = (path, self.address, value_to_send, value_to_receive, int(time()) + 300)
                multicall_bytes.append(self.izumi_contract.functions.swapAmount(p)._encode_transaction_data())
                multicall_bytes.append(self.izumi_contract.functions.refundETH()._encode_transaction_data())
            elif from_token == "ETH":
                p = (path, '0x0000000000000000000000000000000000000000', eth_balance, value_to_receive, int(time()) + 300)
                multicall_bytes.append(self.izumi_contract.functions.swapAmount(p)._encode_transaction_data())
                multicall_bytes.append(self.izumi_contract.functions.unwrapWETH9(0, self.address)._encode_transaction_data())

            contract_txn = self.izumi_contract.functions.multicall(multicall_bytes)
            tx_hash = await self.sent_tx(chain_name=self.chain, tx=contract_txn, tx_label=module_str, value=tx_value)

        except Exception as error:
            if 'insufficient' in str(error):
              raise ValueError(f'✅ No more funds in wallet {self.address}')

            elif 'Ending work.' in str(error):
                logger.info(f"{self.address} | {module_str} | {str(error)}")
                return str(error)

            elif retry < settings.RETRY:
                logger.error(f'{module_str} | {error}')
                await asyncio.sleep(10)
                return await self.swap(retry=retry+1)

            else:
                self.tg_report.update_logs(f'❌ {module_str}: {error}')
                raise ValueError(f'{module_str}: {error}')
