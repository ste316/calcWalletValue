from pycoingecko import CoinGeckoAPI
import json
from lib_tool import lib
from requests import exceptions
from time import sleep
import pandas_datareader as web
import yfinance as yf

#
# Main price provider
# Implementation of https://github.com/man-c/pycoingecko
#
class cg_api:
    def __init__(self, currency) -> None:
        self.cg = CoinGeckoAPI()
        self.currency = currency
        self.error_count = 0

        # CoinGecko price oracle do NOT work with ticker(eg. $eth, $btc) but with its own id
        # it may happen that one ticker have multiple id:
        # eg. {'symbol': 'eth', 'id': ['ethereum', 'ethereum-wormhole']}
        # usually id with "-" in it is a wrapped token or similar
        # BUT sometimes isn't the case, so when you encounter that price is incorrect 
        # you may add the right one in cached symbol 
        # To find the right one just ctrl/cmd + F on cached_id_CG.json file
        # and search the right one by looking at name field
        self.cachedSymbol = ['crypto-com-chain', 'terra-luna-2', 'the-sandbox', 
                            'astroport', 'energy-web-token', 'terra-name-service',
                            'mars-protocol','usd-coin','thorchain', 'avalanche-2', 'cosmos']

    # fetch all id, symbol and name from CoinGecko
    # run only once
    def fetchID(self) -> None: 
        coin = self.cg.get_coins_list() # retrieve a list with {id:'', symbol:'', name:''}

        with open('cached_id_CG.json', 'w') as f:
            f.write(json.dumps(coin, indent=4))

    # convert ticker(eg. atom, eth) in CoinGecko id
    def convertSymbol2ID(self, find: str): 
        try:
            with open('cached_id_CG.json', 'r') as f:
                if f.readable:
                    res = {'symbol': find, 'id': []}
                    coin = json.loads(f.read())

                    for dict in coin:
                        if dict['symbol'] == find:
                            res['id'].append(dict['id'])
                    
                    return res # return {'symbol': 'eth', 'id': ['ethereum', 'ethereum-wormhole']}

                else: lib.printFail('Failed to convert symbol')
        except FileNotFoundError:
            lib.printFail("Error, cached_id_CG.json not found")
            exit

    # given an CG id, it return its price
    def retrievePriceOF(self, id: str):
        while True:
            if self.error_count > 5:
                lib.printFail("Api may be down, check https://status.coingecko.com/")
            try:
                rtrn = self.cg.get_price(id, vs_currencies=self.currency) # rtrn format {<id>: {<currency>: <price>}}
                break
            except exceptions.HTTPError:
                lib.printFail(f'Error retriving price of {id}, retrying...')
                self.error_count +=1
                sleep(0.7)
                continue
            except ValueError as e:
                lib.printFail('Error, you are rate limited, sleeping 61 seconds...')
                self.error_count +=1
                sleep(61)
                continue
        
        if rtrn[id] == {}: # ticker found but not listed(not have a price on coingecko)
            return False

        return rtrn[id][self.currency.lower()]
        #
        # if a traceback report
        #       return rtrn[id][self.currency.lower()]
        #   KeyError: ''
        # means that the id is not found 
        # To fix it:
        #   -update your cached_id_CG.json file
        #   -search manually your id and add it to self.cachedSymbol list
        #

    # 'symbol' is a ticker
    # getPriceOf() return current price of that symbol
    def getPriceOf(self, symbol: str):
        dict = self.convertSymbol2ID(symbol)
        if len(dict['id']) < 1: return False # if no id is found, let the caller handle the error

        newId = ''
        if len(dict['id']) > 1: # in case convertSymbol2ID() found multiple id
            check = False
            for id in dict['id']:
                for cs in self.cachedSymbol: # check cached symbol
                    if id == cs:
                        newId = id
                        check = True
                        break
            if not check:
                for id in dict['id']: 
                    if '-' not in id:
                            newId = id
        else: newId = dict['id'][0]  # in case convertSymbol2ID() found only one id

        return self.retrievePriceOF(newId)

# retrieve price of forex pair
# symbol format "<currency1><currency2>=X"
def yahooGetPriceOf(symbol: str):
    try:
        data = yf.download(tickers = symbol, period ='15m', interval = '1m', progress=False)
        return data.tail()['Close'][4]
    except web._utils.RemoteDataError: 
        # if symbol cannot be found
        lib.printFail(f'Error getting price of {symbol}')
        return False

from requests import Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects

class cmc_api:
    def __init__(self, currency: str, api_key: str) -> None:
        self.currency = currency
        self.key = api_key
        self.baseurl = f'https://pro-api.coinmarketcap.com/v1/cryptocurrency/'
        self.cachedSymbol = lib.loadJsonFile('used_id_CMC.json')

        headers = {
            'Accepts': 'application/json',
            'Accept-Encoding': 'deflate, gzip',
            'X-CMC_PRO_API_KEY': self.key,
        }

        self.session = Session()
        self.session.headers.update(headers)

    # fetch all id, symbol and name from CoinMarketCap
    # run only once
    def fetchID(self) -> int:
        url = 'map'
        res = self.session.get(self.baseurl+url)
        open('cached_id_CMC.json', 'w').write(json.dumps(res.json(), indent=4))

    # convert a list of symbol in cmc id
    def convertSymbols2ID(self, symbol: list) -> dict:
        id = {}
        symbol = symbol

        for i, symb in enumerate(symbol):
            if symb in self.cachedSymbol:
                id[symb] = self.cachedSymbol[symb]
                symbol.pop(i)

        if len(symbol) > 0:
            found = 0
            data = json.loads(open('cached_id_CMC.json', 'r').read())['data']

            for i in range(len(data)):
                if data[i]['symbol'] in symbol:
                    id[data[i]['symbol']] = str(data[i]['id'])
                    found +=1
                    symbol.pop(symbol.index(data[i]['symbol']))

            if found > 0:
                self.cachedSymbol.update(id)
                self.updateCachedSymbol()

        return id # format {'<ticker>': <id>, }

    def updateCachedSymbol(self) -> None:
        with open('used_id_CMC.json', 'w') as f:
            f.write(json.dumps(self.cachedSymbol))

    def getPriceOf(self, symbol: list):
        url = 'quotes/latest'
        symbol = self.convertSymbols2ID(symbol)
        id = list(symbol.values())

        toReturn = {}        

        parameters = {
            'id': ','.join(id),
            'convert': self.currency
        }

        try:
            response = self.session.get(self.baseurl+url, params=parameters)
            data = json.loads(response.text)
            for symb, id in symbol.items():
                toReturn[symb] = data['data'][id]["quote"][self.currency]["price"]

        except (ConnectionError, Timeout, TooManyRedirects):
            data = json.loads(response.text)
        
        if (set(symbol.keys()) & set(toReturn.keys())) != set(symbol):
            return (toReturn, False, set(symbol.keys()) - set(toReturn.keys()))
        
        return (toReturn, True)

if __name__ == '__main__':
    sett = lib.getSettings()
    cmc = cmc_api(sett['currency'], sett['api_provider']['CMC_key'])
    cmc.getPriceOf([['BTC','MATIC','JUNO','AVAX','SOL']])
