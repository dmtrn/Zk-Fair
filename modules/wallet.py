from eth_account.messages import encode_defunct
from random import uniform, randint
from typing import Union, Optional
from ccxt import bybit as Bybit
import requests, hmac, base64
from web3.eth import AsyncEth
from datetime import datetime
from time import time
from web3 import Web3
import asyncio

from modules.utils import logger, sleeping
import modules.config as config
import settings


class Wallet:
    def __init__(self, privatekey: str, recipient: str, tg_report, browser, proxy):
        self.privatekey = privatekey
        self.recipient = Web3().to_checksum_address(recipient) if recipient else None
        self.account = Web3().eth.account.from_key(privatekey)
        self.address = self.account.address
        self.tg_report = tg_report
        self.browser = browser
        self.proxy = proxy

        self.max_retries = 5
        self.stats = {}


    def get_web3(self, chain_name: str):
        web3 = Web3(Web3.AsyncHTTPProvider(settings.RPCS[chain_name], request_kwargs={"proxy": self.proxy}), modules={'eth': (AsyncEth,)}, middlewares=[])
        # web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        return web3


    async def wait_for_ether_gwei(self):
        first_check = True
        while True:
            try:
                web3 = self.get_web3(chain_name='ethereum')
                new_gwei = round(await web3.eth.gas_price / 10 ** 9, 2)
                if new_gwei <= settings.MAX_GWEI:
                    if not first_check: logger.debug(f'[•] Web3 | New GWEI is {new_gwei}')
                    break
                await asyncio.sleep(5)
                if first_check:
                    first_check = False
                    logger.debug(f'[•] Web3 | Waiting for GWEI in Ethereum at least {settings.MAX_GWEI}. Now it is {new_gwei}')
            except Exception as err:
                logger.warning(f'[•] Web3 | Gwei waiting error: {err}')
                await asyncio.sleep(10)


    async def wait_for_zkfair_gwei(self):
        first_check = True
        while True:
            try:
                web3 = self.get_web3(chain_name='zkfair')
                new_gwei = round(await web3.eth.gas_price / 10 ** 9, 2)
                if new_gwei <= settings.MAX_ZKFAIR_GWEI:
                    if not first_check: logger.debug(f'[•] Web3 | New GWEI is {new_gwei}')
                    break
                await asyncio.sleep(5)
                if first_check:
                    first_check = False
                    logger.debug(f'[•] Web3 | Waiting for GWEI in ZKFair at least {settings.MAX_ZKFAIR_GWEI}. Now it is {new_gwei}')
            except Exception as err:
                logger.warning(f'[•] Web3 | ZKFair Gwei waiting error: {err}')
                await asyncio.sleep(10)


    async def wait_for_gwei(self):
        await self.wait_for_ether_gwei()
        await self.wait_for_zkfair_gwei()


    async def get_gas(self, chain_name):
        if chain_name == 'zkfair':
            web3 = self.get_web3(chain_name=chain_name)
            if settings.ZKFAIR_GWEI == "Auto": gas_price = await web3.eth.gas_price
            else: gas_price = int(settings.ZKFAIR_GWEI * 1e9)

            if settings.ZKFAIR_GASLIMIT == "Auto": return {'gasPrice': gas_price}
            else: return {'gasPrice': gas_price, 'gas': int(settings.ZKFAIR_GASLIMIT)}

        elif chain_name == 'linea': return {'gasPrice': self.get_web3(chain_name=chain_name).eth.gas_price}
        max_priority = await self.get_web3(chain_name=chain_name).eth.max_priority_fee
        last_block = await self.get_web3(chain_name=chain_name).eth.get_block('latest')
        base_fee = last_block['baseFeePerGas']
        block_filled = last_block['gasUsed'] / last_block['gasLimit'] * 100
        if block_filled > 50: base_fee *= 1.125
        if settings.GWEI_MULTIPLIER > 1: base_fee *= settings.GWEI_MULTIPLIER
        max_fee = int(base_fee + max_priority)

        return {'maxPriorityFeePerGas': max_priority, 'maxFeePerGas': max_fee}


    async def approve(self, chain_name: str, spender: str, token_name: Optional[str] = False, token_address: Optional[str] = False, amount=None, value=None, retry=0):
        try:
            module_str = f'approve {token_name} to {spender}'

            web3 = self.get_web3(chain_name=chain_name)
            spender = web3.to_checksum_address(spender)
            if token_name: token_address = config.TOKEN_ADDRESSES[token_name]
            token_contract = web3.eth.contract(address=web3.to_checksum_address(token_address),
                                         abi='[{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"}]')
            if not token_name:
                token_name = await token_contract.functions.name().call()
                module_str = f'approve {token_name} to {spender}'

            decimals = await token_contract.functions.decimals().call()
            if amount:
                value = int(amount * 10 ** decimals)
                new_amount = round(amount * randint(30, 80), 5)
                new_value = int(new_amount * 10 ** decimals)
            else:
                new_value = int(value * randint(30, 80))
                new_amount = round(new_value / 10 ** decimals, 5)
            module_str = f'approve {new_amount} {token_name} to {spender}'

            allowance = await token_contract.functions.allowance(self.address, spender).call()
            if allowance < value:
                tx = token_contract.functions.approve(spender, new_value)
                tx_hash = await self.sent_tx(chain_name=chain_name, tx=tx, tx_label=module_str)
                await sleeping(20, 40)
                return tx_hash
        except Exception as error:
            if retry < settings.RETRY:
                logger.error(f'{module_str} | {error}')
                logger.info(f'try again | {self.address}')
                await asyncio.sleep(10)
                await self.approve(chain_name=chain_name, token_name=token_name, spender=spender, amount=amount, value=value, retry=retry+1)
            else:
                self.tg_report.update_logs(f'❌ {module_str}: {error}')
                raise ValueError(f'{module_str}: {error}')


    async def sent_tx(self, chain_name: str, tx, tx_label, tx_raw=False, value=0):
        try:
            web3 = self.get_web3(chain_name=chain_name)
            if not tx_raw:
                if type(tx) != dict:
                    tx = await tx.build_transaction({
                        'from': self.address,
                        'chainId': await web3.eth.chain_id,
                        'nonce': await web3.eth.get_transaction_count(self.address),
                        'value': value,
                        **await self.get_gas(chain_name=chain_name),
                    })

            signed_tx = web3.eth.account.sign_transaction(tx, self.privatekey)
            raw_tx_hash = await web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash = web3.to_hex(raw_tx_hash)
            tx_link = f'{config.CHAINS_DATA[chain_name]["explorer"]}{tx_hash}'
            logger.debug(f'[•] Web3 | {tx_label} tx sent: {tx_link}')

            while True:
                try:
                    status = dict(await web3.eth.wait_for_transaction_receipt(tx_hash, timeout=int(settings.TO_WAIT_TX * 60)))['status']
                    if status != None: break
                except Exception as err:
                    logger.debug(f'some error while waiting tx: {err}')
                await asyncio.sleep(1)

            if status == 1:
                logger.info(f'[+] Web3 | {tx_label} tx confirmed\n')
                self.tg_report.update_logs(f'✅ {tx_label}')
                return tx_hash
            else:
                self.tg_report.update_logs(f'❌ {tx_label} <a href="{tx_link}">TX</a>')
                raise ValueError(f'tx failed: {tx_link}')

        except Exception as err:
            if 'already known' in str(err):
                try: raw_tx_hash
                except: raw_tx_hash = ''
                logger.warning(f'{tx_label} | Couldnt get tx hash, thinking tx is success ({raw_tx_hash})')
                await asyncio.sleep(15)
                return True
            elif 'Drop already claimed' in str(err):
                return 'claimed'

            try: encoded_tx = f'\nencoded tx: {tx._encode_transaction_data()}'
            except: encoded_tx = ''
            raise ValueError(f'tx failed error: {err}{encoded_tx}')


    async def get_balance(self, chain_name: str, token_name=False, token_address=False, human=False):
        web3 = self.get_web3(chain_name=chain_name)
        if token_name: token_address = config.TOKEN_ADDRESSES[token_name]
        if token_address: contract = web3.eth.contract(address=web3.to_checksum_address(token_address),
                                     abi='[{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"}]')
        while True:
            try:
                if token_address: balance = await contract.functions.balanceOf(self.address).call()
                else: balance = await web3.eth.get_balance(self.address)

                decimals = await contract.functions.decimals().call() if token_address else 18
                if not human: return balance
                return balance / 10 ** decimals
            except Exception as err:
                logger.warning(f'[•] Web3 | Get balance error: {err}')
                await asyncio.sleep(5)


    async def wait_balance(self, chain_name: str, needed_balance: Union[int, float], only_more: bool = False, token_name: Optional[str] = False, token_address: Optional[str] = False):
        " needed_balance: human digit "
        if token_name:
            token_address = config.TOKEN_ADDRESSES[token_name]

        elif token_address:
            contract = self.get_web3(chain_name=chain_name).eth.contract(address=Web3().to_checksum_address(token_address),
                                         abi='[{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"}]')
            token_name = await contract.functions.name().call()

        else:
            token_name = 'ETH'

        if only_more: logger.debug(f'[•] Web3 | Waiting for balance more than {round(needed_balance, 6)} {token_name} in {chain_name.upper()}')
        else: logger.debug(f'[•] Web3 | Waiting for {round(needed_balance, 6)} {token_name} balance in {chain_name.upper()}')

        while True:
            try:
                new_balance = await self.get_balance(chain_name=chain_name, human=True, token_address=token_address)

                if only_more: status = new_balance > needed_balance
                else: status = new_balance >= needed_balance
                if status:
                    logger.debug(f'[•] Web3 | New balance: {round(new_balance, 6)} {token_name}\n')
                    return new_balance
                await asyncio.sleep(5)
            except Exception as err:
                logger.warning(f'[•] Web3 | Wait balance error: {err}')
                await asyncio.sleep(10)


    async def okx_withdraw(self, chain: str, retry=0):

        def okx_data(api_key, secret_key, passphras, request_path="/api/v5/account/balance?ccy=ETH", body='', meth="GET"):

            try:
                import datetime
                def signature(
                        timestamp: str, method: str, request_path: str, secret_key: str, body: str = ""
                ) -> str:
                    if not body:
                        body = ""

                    message = timestamp + method.upper() + request_path + body
                    mac = hmac.new(
                        bytes(secret_key, encoding="utf-8"),
                        bytes(message, encoding="utf-8"),
                        digestmod="sha256",
                    )
                    d = mac.digest()
                    return base64.b64encode(d).decode("utf-8")

                dt_now = datetime.datetime.utcnow()
                ms = str(dt_now.microsecond).zfill(6)[:3]
                timestamp = f"{dt_now:%Y-%m-%dT%H:%M:%S}.{ms}Z"

                base_url = "https://www.okex.com"
                headers = {
                    "Content-Type": "application/json",
                    "OK-ACCESS-KEY": api_key,
                    "OK-ACCESS-SIGN": signature(timestamp, meth, request_path, secret_key, body),
                    "OK-ACCESS-TIMESTAMP": timestamp,
                    "OK-ACCESS-PASSPHRASE": passphras,
                    'x-simulated-trading': '0'
                }
            except Exception as ex:
                logger.error(ex)
            return base_url, request_path, headers

        self.wait_for_gwei()

        amount_from = settings.WITHDRAW_VALUES[chain][0]
        amount_to = settings.WITHDRAW_VALUES[chain][1]
        wallet = self.address
        SUB_ACC = True
        SYMBOL = 'ETH'

        old_balance = self.get_balance(chain_name=chain, human=True)
        if old_balance >= amount_from: return 'funded'

        match chain:
            case 'arbitrum': CHAIN = 'Arbitrum One'
            case 'optimism': CHAIN = 'Optimism'
            case 'linea': CHAIN = 'Linea'

        api_key = settings.OKX_KEY
        secret_key = settings.OKX_SECRET
        passphras = settings.OKX_PASSWORD

        # take FEE for withdraw
        _, _, headers = okx_data(api_key, secret_key, passphras, request_path=f"/api/v5/asset/currencies?ccy={SYMBOL}",
                                 meth="GET")
        response = requests.get(f"https://www.okx.cab/api/v5/asset/currencies?ccy={SYMBOL}", timeout=10,
                                headers=headers)

        for lst in response.json()['data']:
            if lst['chain'] == f'{SYMBOL}-{CHAIN}':
                FEE = lst['minFee']

        try:
            while True:
                if SUB_ACC == True:
                    _, _, headers = okx_data(api_key, secret_key, passphras,
                                             request_path=f"/api/v5/users/subaccount/list", meth="GET")
                    list_sub = requests.get("https://www.okx.cab/api/v5/users/subaccount/list", timeout=10,
                                            headers=headers)
                    list_sub = list_sub.json()

                    for sub_data in list_sub['data']:
                        while True:
                            name_sub = sub_data['subAcct']

                            _, _, headers = okx_data(api_key, secret_key, passphras,
                                                     request_path=f"/api/v5/asset/subaccount/balances?subAcct={name_sub}&ccy={SYMBOL}",
                                                     meth="GET")
                            sub_balance = requests.get(
                                f"https://www.okx.cab/api/v5/asset/subaccount/balances?subAcct={name_sub}&ccy={SYMBOL}",
                                timeout=10, headers=headers)
                            sub_balance = sub_balance.json()
                            if sub_balance.get('msg') == f'Sub-account {name_sub} doesn\'t exist':
                                logger.warning(f'[-] OKX | Error: {sub_balance["msg"]}')
                                continue
                            sub_balance = sub_balance['data'][0]['bal']

                            logger.info(f'[•] OKX | {name_sub} | {sub_balance} {SYMBOL}')

                            if float(sub_balance) > 0:
                                body = {"ccy": f"{SYMBOL}", "amt": str(sub_balance), "from": 6, "to": 6, "type": "2",
                                        "subAcct": name_sub}
                                _, _, headers = okx_data(api_key, secret_key, passphras,
                                                         request_path=f"/api/v5/asset/transfer", body=str(body),
                                                         meth="POST")
                                a = requests.post("https://www.okx.cab/api/v5/asset/transfer", data=str(body),
                                                  timeout=10, headers=headers)
                            break

                try:
                    _, _, headers = okx_data(api_key, secret_key, passphras,
                                             request_path=f"/api/v5/account/balance?ccy={SYMBOL}")
                    balance = requests.get(f'https://www.okx.cab/api/v5/account/balance?ccy={SYMBOL}', timeout=10,
                                           headers=headers)
                    balance = balance.json()
                    balance = balance["data"][0]["details"][0]["cashBal"]

                    if balance != 0:
                        body = {"ccy": f"{SYMBOL}", "amt": float(balance), "from": 18, "to": 6, "type": "0",
                                "subAcct": "", "clientId": "", "loanTrans": "", "omitPosRisk": ""}
                        _, _, headers = okx_data(api_key, secret_key, passphras, request_path=f"/api/v5/asset/transfer",
                                                 body=str(body), meth="POST")
                        a = requests.post("https://www.okx.cab/api/v5/asset/transfer", data=str(body), timeout=10,
                                          headers=headers)
                except Exception as ex:
                    pass

                # CHECK MAIN BALANCE
                _, _, headers = okx_data(api_key, secret_key, passphras,
                                         request_path=f"/api/v5/asset/balances?ccy={SYMBOL}", meth="GET")
                main_balance = requests.get(f'https://www.okx.cab/api/v5/asset/balances?ccy={SYMBOL}', timeout=10,
                                            headers=headers)
                main_balance = main_balance.json()
                main_balance = float(main_balance["data"][0]['availBal'])
                logger.info(f'[•] OKX | Total balance: {main_balance} {SYMBOL}')

                if amount_from > main_balance:
                    logger.warning(f'[•] OKX | Not enough balance ({main_balance} < {amount_from}), waiting 10 secs...')
                    await asyncio.sleep(10)
                    continue

                if amount_to > main_balance:
                    logger.warning(
                        f'[•] OKX | You want to withdraw MAX {amount_to} but have only {round(main_balance, 7)}')
                    amount_to = round(main_balance, 7)

                AMOUNT = round(uniform(amount_from, amount_to), 7)
                break

            body = {"ccy": SYMBOL, "amt": AMOUNT, "fee": FEE, "dest": "4", "chain": f"{SYMBOL}-{CHAIN}",
                    "toAddr": wallet}
            _, _, headers = okx_data(api_key, secret_key, passphras, request_path=f"/api/v5/asset/withdrawal",
                                     meth="POST", body=str(body))
            a = requests.post("https://www.okx.cab/api/v5/asset/withdrawal", data=str(body), timeout=10,
                              headers=headers)
            result = a.json()

            if result['code'] == '0':
                logger.success(f"[+] OKX | Success withdraw {AMOUNT} {SYMBOL} to {wallet}")
                self.tg_report.update_logs(f'✅ OKX withdraw {AMOUNT} {SYMBOL} to {wallet}')
                new_balance = self.wait_balance(chain_name=chain, needed_balance=old_balance, only_more=True)
                return round(new_balance - old_balance, 6) ###
            else:
                error = result['msg']
                if retry < self.max_retries:
                    logger.error(f"[-] OKX | Withdraw unsuccess to {wallet} | error : {error}")
                    await asyncio.sleep(10)
                    return self.okx_withdraw(chain=chain, retry=retry + 1)
                else:
                    raise ValueError(f'OKX withdraw error: {error}')

        except Exception as error:
            logger.error(f"[-] OKX | Withdraw unsuccess to {wallet} | error : {error}")
            if retry < self.max_retries:
                await asyncio.sleep(10)
                if 'Insufficient balance' in str(error): return self.okx_withdraw(chain=chain, retry=retry)
                return self.okx_withdraw(chain=chain, retry=retry + 1)
            else:
                raise ValueError(f'OKX withdraw error: {error}')


    async def bybit_withdraw(self, chain: str, retry=0):
        try:
            self.wait_for_gwei()
            old_balance = self.get_balance(chain_name=chain, human=True)

            min_withdraw, max_withdraw = settings.WITHDRAW_VALUES[chain]

            if old_balance >= min_withdraw: return 'funded'

            bybit = Bybit({
                'apiKey': settings.BYBIT_KEY,
                'secret': settings.BYBIT_SECRET,
                'enableRateLimit': True,
            })

            try:
                old_coins_balances = bybit.privateGetAssetV3PrivateTransferAccountCoinsBalanceQuery({'accountType': 'UNIFIED', 'coin': 'ETH'})['result']['balance']
                old_trading_eth_balance = float(old_coins_balances[0]['transferBalance'])
            except Exception as err:
                if 'Too many visits.' in str(err):
                    logger.info(f'Bybit API Rate Limit (fetch old ETH balance)')
                    await asyncio.sleep(60)
                    return self.bybit_withdraw(chain=chain, retry=retry)
                else:
                    logger.error(f'Couldnt get ETH UNIFIED balance')
                    raise Exception(str(err))

            if old_trading_eth_balance:
                try:
                    r = bybit.transfer(code='ETH', amount=old_trading_eth_balance, fromAccount='UNIFIED', toAccount='FUND')
                except Exception as err:
                    if 'Too many visits.' in str(err):
                        logger.info(f'Bybit API Rate Limit (transfer)')
                        await asyncio.sleep(60)
                        return self.bybit_withdraw(chain=chain, retry=retry)
                    else: raise Exception(str(err))

                if r.get('status') == 'ok':
                    logger.info(f'Transfered {old_trading_eth_balance} ETH from SPOT to FUND')
                else:
                    logger.error(f'Couldnt transfer {old_trading_eth_balance} ETH from SPOT to FUND: {r}')

            try:
                coins_balances = bybit.privateGetAssetV3PrivateTransferAccountCoinsBalanceQuery({'accountType': 'FUND', 'coin': 'ETH'})['result']['balance']
                fund_eth_balance = float(coins_balances[0]['transferBalance'])
            except Exception as err:
                if 'Too many visits.' in str(err):
                    logger.info(f'Bybit API Rate Limit (get coins balance)')
                    await asyncio.sleep(60)
                    return self.bybit_withdraw(chain=chain, retry=retry)
                else:
                    logger.error(f'Couldnt get ETH FUND balance')
                    raise Exception(str(err))

            if fund_eth_balance > min_withdraw and fund_eth_balance < max_withdraw:
                logger.info(f'Bybit balance less than `{max_withdraw}`. Now this value is {fund_eth_balance}')
                max_withdraw = fund_eth_balance
            elif fund_eth_balance < min_withdraw:
                logger.info(f'No funds in Bybit to withdraw. Balance: {fund_eth_balance} but need at least {min_withdraw}')
                await asyncio.sleep(10)
                return self.bybit_withdraw(chain=chain)

            to_withdraw = round(uniform(min_withdraw, max_withdraw), 5)

            try:
                result = bybit.withdraw(code='ETH', amount=to_withdraw, address=self.address, params={'chain': 'LINEA', 'timestamp': int(time() * 1000), 'accountType': 'FUND'})
            except Exception as err:
                if 'Withdraw address chain or destination tag are not equal' in str(err):
                    try:
                        await asyncio.sleep(15)
                        result = bybit.withdraw(code='ETH', amount=to_withdraw, address=self.address.lower(), params={'chain': 'LINEA', 'timestamp': int(time() * 1000), 'accountType': 'FUND'})
                    except Exception as err:
                        if 'Too many visits.' in str(err):
                            logger.info(f'Bybit API Rate Limit (withdraw x2)')
                            await asyncio.sleep(60)
                            return self.bybit_withdraw(chain=chain, retry=retry)
                        else:
                            raise Exception(str(err))
                elif 'Too many visits.' in str(err):
                    logger.info(f'Bybit API Rate Limit (withdraw)')
                    await asyncio.sleep(60)
                    return self.bybit_withdraw(chain=chain, retry=retry)
                else:
                    raise Exception(str(err))

            if result.get('id'):
                logger.success(f'Success Bybit withdraw {to_withdraw} ETH to {self.address}')
                self.tg_report.update_logs(f'✅ Bybit withdraw {to_withdraw} ETH to {self.address}')

                new_balance = self.wait_balance(chain_name=chain, needed_balance=old_balance, only_more=True)
                return round(new_balance - old_balance, 6)

        except Exception as err:
            logger.error(f'Bybit withdraw error to {self.address}: {err}')

            if retry < self.max_retries:
                await asyncio.sleep(10)
                if 'Withdrawal amount is greater than your available balance' in str(err) or 'Please wait at least 10 seconds between withdrawals' in str(err):
                    return self.bybit_withdraw(chain=chain, retry=retry)
                return self.bybit_withdraw(chain=chain, retry=retry+1)
            else:
                raise ValueError(f'Bybit withdraw error to {self.address}: {err}')


    def withdraw_funds(self, chain: str):
        if settings.EXCHANGE_TO_WITHDRAW.lower() == 'bybit':
            return self.bybit_withdraw(chain=chain)
        elif settings.EXCHANGE_TO_WITHDRAW.lower() == 'okx':
            return self.okx_withdraw(chain=chain)


    async def get_human_token_amount(self, chain_name: str, token_name: str, value: Union[int, float], human=True):
        if token_name != 'ETH':
            web3 = self.get_web3(chain_name=chain_name)
            token_contract = web3.eth.contract(address=web3.to_checksum_address(config.TOKEN_ADDRESSES[token_name]),
                                               abi='[{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"}]')

            decimals = token_contract.functions.decimals().call()
        else: decimals = 18

        if human: return round(value / 10 ** decimals, 7)
        else: return int(value * 10 ** decimals)


    async def send_to_okx(self, chain: str, retry=0):

        try:
            module_str = f'sent ETH to {self.recipient}'

            web3 = self.get_web3(chain_name=chain)
            keep_values = settings.KEEP_VALUES

            if keep_values['all_balance']:
                balance = self.get_balance(chain_name=chain, human=False)
                value = balance
            else:
                balance = self.get_balance(chain_name=chain, human=True)
                amount = round(balance - uniform(keep_values['keep_from'], keep_values['keep_to']), 6)
                value = int(amount * 10 ** 18)

            value = int(value - 21000 * web3.eth.gas_price * 1.1 // 10 ** 12 * 10 ** 12)  # round value
            amount = round(value / 10 ** 18, 5)

            if value < 0: raise Exception(f'no funds to send')

            module_str = f'sent {amount} ETH to {self.recipient}'

            tx = {
                'from': self.address,
                'to': self.recipient,
                'chainId': web3.eth.chain_id,
                'nonce': web3.eth.get_transaction_count(self.address),
                'value': value,
                **await self.get_gas(chain_name=chain),
            }

            await self.sent_tx(chain, tx, module_str, tx_raw=True)

        except Exception as error:
            if 'no funds to send' in str(error):
                raise ValueError(f'{module_str}: {error}')
            elif retry < settings.RETRY:
                logger.error(f'{module_str} | {error}')
                await asyncio.sleep(10)
                return await self.send_to_okx(chain=chain, retry=retry + 1)
            else:
                self.tg_report.update_logs(f'❌ {module_str}: {error}')
                raise ValueError(f'{module_str}: {error}')


    def get_zkfair_signature(self):
        current_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + "Z"

        text = f'{current_time}GET/api/airdrop?address={self.address.lower()}'

        signature = Web3().eth.account.sign_message(encode_defunct(text=text), private_key=self.privatekey).signature.hex()

        return {"address": self.address.lower(), "API-SIGNATURE": signature, "TIMESTAMP": current_time}


