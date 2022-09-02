from pycoingecko import CoinGeckoAPI
import json
from lib_tool import lib
from requests import exceptions
from time import sleep
import pandas_datareader as web
from datetime import date
import yfinance as yf

#
# Main price provider
# Implementation of https://github.com/man-c/pycoingecko
#
class cg_api:
    def __init__(self, currency) -> None:
        self.cg = CoinGeckoAPI()
        self.currency = currency

        # CoinGecko price oracle do NOT work with ticker(eg. $eth, $btc) but with its own id
        # it may happen that one ticker have multiple id:
        # eg. {'symbol': 'eth', 'id': ['ethereum', 'ethereum-wormhole']}
        # usually id with "-" in it is a wrapped token or similar
        # BUT sometimes isn't the case, so when you encounter that price is incorrect 
        # you may add the right one in cached symbol 
        # To find the right one just ctrl/cmd + F on cached_id_CG.json file
        # and search the right one by looking at name field
        self.cachedSymbol = ['crypto-com-chain', 'the-sandbox', 'usd-coin','thorchain']

    # fetch all id, symbol and name from CoinGecko
    # run only once
    def fetchID(self): 
        coin = self.cg.get_coins_list() # retrieve a list with {id:'', symbol:'', name:''}

        with open('cached_id_CG.json', 'w') as f:
            f.write(json.dumps(coin, indent=4))

    # convert ticker(eg. atom, eth) in CG id
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
            try:
                rtrn = self.cg.get_price(id, vs_currencies=self.currency) # format: {<id>: {<currency>: <price>}}
                break
            except exceptions.HTTPError:
                lib.printFail(f'Error retriving price of {id}, retrying...')
                sleep(0.5)
                continue

        return rtrn[id][self.currency.lower()]

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
