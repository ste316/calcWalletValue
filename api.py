from pycoingecko import CoinGeckoAPI
import json
from lib_tool import lib
from requests import exceptions
from time import sleep
import pandas_datareader as web
import yfinance as yf

#
# CoinGecko api
# Implementation of https://github.com/man-c/pycoingecko
#
class cg_api:
    def __init__(self, currency) -> None:
        self.cg = CoinGeckoAPI()
        self.currency = currency
        self.error_count = 0

        ''' CoinGecko price oracle do NOT work with ticker(eg. $eth, $btc) but with its own id
            it may happen that one ticker have multiple id:
            eg. {'symbol': 'eth', 'id': ['ethereum', 'ethereum-wormhole']}
            usually id with "-" in it is a wrapped token or similar
            BUT sometimes isn't the case, so when you encounter that price is incorrect 
            you may add the right one in cached symbol 
            To find the right one just CTRL + F on cached_id_CG.json file
            and search the right one by looking at name field'''

        self.cachedSymbol = ['crypto-com-chain', 'terra-luna-2', 'the-sandbox', 
                            'astroport', 'energy-web-token', 'terra-name-service',
                            'mars-protocol-2','usd-coin','thorchain', 'avalanche-2', 'cosmos', 'flow']

    # fetch all id, symbol and name from CoinGecko, run only once in a while to update it
    def fetchID(self) -> None: 
        coin = self.cg.get_coins_list() # retrieve a list with {id:'', symbol:'', name:''}

        with open('cached_id_CG.json', 'w') as f:
            f.write(json.dumps(coin, indent=4))

    # convert 'find' to CoinGecko id
    # @param find crypto ticker eg. "ETH"
    # @return dict eg. {'symbol': 'ETH', 'id': ['ethereum', 'ethereum-wormhole']}
    def convertSymbol2ID(self, find: str): 
        try:
            with open('cached_id_CG.json', 'r') as f:
                if f.readable:
                    res = {'symbol': find, 'id': []}
                    coin = json.loads(f.read())

                    for dict in coin:
                        if dict['symbol'] == find:
                            res['id'].append(dict['id'])

                    return res

                else: lib.printFail('Failed to convert symbol')
        except FileNotFoundError:
            lib.printFail("Error, cached_id_CG.json not found")
            exit

    # retrieve price of 'id'
    # @param id CoinGecko id
    # @return float if price is found, False if not
    def retrievePriceOF(self, id: str):
        while True:
            if self.error_count > 5:
                lib.printFail("Api may be down, check https://status.coingecko.com/")
            try:
                rtrn = self.cg.get_price(id.lower(), vs_currencies=self.currency) # rtrn format {<id>: {<currency>: <price>}}
                break
            except exceptions.HTTPError:
                lib.printFail(f'Error retriving price of {id}, retrying...')
                self.error_count +=1
                sleep(0.7)
                continue
            except ValueError as e:
                n = 100
                lib.printFail(f'Error, you are rate limited, sleeping {n} seconds...')
                self.error_count +=1
                sleep(n)
                continue
        
        if rtrn[id] == {}: # ticker found but not listed(not have a price on coingecko)
            return False
        '''
        If an error is raised and the traceback report:
                return rtrn[id][self.currency.lower()]
            KeyError: ''
        means that the id is not found 
        To fix it:
            -update your cached_id_CG.json file
            -search manually your id and add it to self.cachedSymbol list
        '''
        return rtrn[id][self.currency.lower()]

    # convert 'symbol' to CoinGecko id and retrieve its price
    # @param symbol crypto ticker eg. "BTC"
    # @return float if price is found, False if not or if CG id is not found
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

# retrieve price of 'symbol'
# @param symbol string eg. "EURUSD=X"
# @return float, False if symbol cannot be found
def yahooGetPriceOf(symbol: str):
    try:
        data = yf.download(tickers = symbol, period ='1d', interval = '1m', progress=False)
        return data.tail()['Close'][4]
    except web._utils.RemoteDataError: 
        # if symbol cannot be found
        lib.printFail(f'Error getting price of {symbol}')
        return False

from requests import Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import random 

#
# CoinMarketCap Api
#
class cmc_api:
    def __init__(self, currency: str, api_key: str) -> None:
        self.currency = currency
        self.key = api_key
        self.baseurl = f'https://pro-api.coinmarketcap.com/v1/'
        self.cachedSymbol = lib.loadJsonFile('used_id_CMC.json')

        headers = { 
            'Accepts': 'application/json',
            'Accept-Encoding': 'deflate, gzip',
            'X-CMC_PRO_API_KEY': self.key,
        }

        self.session = Session()
        self.session.headers.update(headers)

    # check that self.key is valid by making a request to CMC endpoint
    # @return True is CMC key is valid, False if not or other error is encoutered
    def isKeyValid(self):
        if self.key.strip() == '' or len(self.key) != 36:
            return False

        path = 'key/info'
        while True:
            res = self.session.get(self.baseurl+path)
            if res.status_code == 200:
                return True
            elif res.status_code == 429:
                lib.printWarn('You have been rate limited, sleeping for 60 second')
                sleep(60)
            elif res.status_code == 500:
                x = random.randrange(range(50,160))
                lib.printWarn(f'Server error, sleeping for {x}')
                sleep(x)
            else: # all others status code means that key is not valid
                return False

    # fetch all id, symbol and name from CMC, run only once in a while to update it
    def fetchID(self) -> int:
        url = 'cryptocurrency/map'
        res = self.session.get(self.baseurl+url)
        open('cached_id_CMC.json', 'w').write(json.dumps(res.json(), indent=4))

    # convert 'symbols' in CMC ids
    # @param symbols list of crypto tickers ["BTC", "ETH"]
    # @return dict eg. {"BTC": "1", }
    def convertSymbols2ID(self, symbols: list) -> dict:
        id = {}

        # check if there are some cached symbol
        for i, symb in enumerate(symbols):
            if symb in self.cachedSymbol:
                id[symb] = self.cachedSymbol[symb]
                symbols.pop(i) # remove from searching list

        if len(symbols) > 0: 
            found = 0
            data = json.loads(open('cached_id_CMC.json', 'r').read())['data'] # once in a while run fetchID() to update it

            # check for every symbol in data
            for i in range(len(data)):
                if data[i]['symbol'] in symbols:
                    id[data[i]['symbol']] = str(data[i]['id'])
                    found +=1
                    symbols.pop(symbols.index(data[i]['symbol']))

            if found > 0:
                self.cachedSymbol.update(id)
                self.updateUsedSymbol()
                
        return id

    # update used_id_CMC.json
    def updateUsedSymbol(self) -> None:
        with open('used_id_CMC.json', 'w') as f:
            f.write(json.dumps(self.cachedSymbol))

    # convert 'symbols' to CMC ids and retrieve their prices
    # @param symbols list of crypto tickers eg. ["BTC", "ETH"]
    # @return (dict, True) if all symbols are found eg. ({"BTC": 20102.0348, "ETH": 1483.31747 }, True), 
    #         (dict, False, set, data) if not all symbols are found eg ({"BTC": 20102.0348}, False, ("ETH"), data)
    #          data is complete http response body loaded in a dict
    def getPriceOf(self, symbols: list):
        path = 'cryptocurrency/quotes/latest'
        convertedSymbol = self.convertSymbols2ID(symbols)
        id = list(convertedSymbol.values())

        toReturn = {}        

        parameters = {
            'id': ','.join(id),
            'convert': self.currency
        }

        try:
            response = self.session.get(self.baseurl+path, params=parameters)
            data = json.loads(response.text)
            for symb, id in convertedSymbol.items():
                toReturn[symb] = data['data'][id]["quote"][self.currency]["price"] # store only price

        except (ConnectionError, Timeout, TooManyRedirects):
            data = json.loads(response.text)
        
        # if one or more symbols are not found for any kind of problem 
        # return also the missing one(s) and data
        if (set(convertedSymbol.keys()) & set(toReturn.keys())) != set(symbols):
            return (toReturn, False, set(symbols) - set(toReturn.keys()), data)
        
        print(toReturn)
        return (toReturn, True)

if __name__ == '__main__':
    sett = lib.getSettings()
    cg = cg_api(sett['currency'])
    cg.getPriceOf("BTC")
    '''
    cmc = cmc_api(sett['currency'], sett['CMC_key'])
    print(cmc.getPriceOf(['BTC','MATIC','JUNO','AVAX', 'DJERNB']))
    '''