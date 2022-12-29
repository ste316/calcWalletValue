from api import cg_api, cmc_api, yahooGetPriceOf
from lib_tool import lib
from pandas import read_csv
from datetime import datetime
from numpy import array
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import json
import os

# 
# Calculate your wallet value 
# add cryptos and fiat in input.csv
# add currency, api_provider and path in settings.json
# specify type: crypto or total
# 
class calculateWalletValue:
    # Initialization variable and general settings
    def __init__(self, type: str, load = False) -> None:
        self.settings = lib.getSettings()
        self.invalid_sym = []
        self.provider = ''
        self.supportedCurrency =  ['eur', 'usd']
        self.supportedStablecoin = ['usdt', 'usdc','dai']
        self.load = load # option to load data from json, see calculateWalletValue.genPltFromJson()
        self.total_invested = 0 
        lib.printWelcome(f'Welcome to Calculate Wallet Value!')
        lib.printWarn(f'Currency: {self.settings["currency"]}')

        # set price provider
        if self.settings['api_provider']['provider'] == 'cg':
            lib.printWarn('Api Provider: CoinGecko')
            self.provider = 'cg'
            self.cg = cg_api(self.settings['currency'])

        elif self.settings['api_provider']['provider'] == 'cmc':
            lib.printWarn('Api Provider: CoinMarketCap')
            self.provider = 'cmc'
            self.cmc = cmc_api(self.settings['currency'], self.settings['api_provider']['CMC_key'])
        else:
            lib.printFail("Specify a correct price provider")
            exit()

        # fetch all crypto symbol and name from CoinGecko or CoinMarketCap
        # run once or if there is any new crypto
        if self.settings['api_provider']['fetchSymb'] == True: 
            if self.provider == 'cg':
                self.cg.fetchID()
            if self.provider == 'cmc':
                self.cmc.fetchID()
            lib.printOk('Coin list successfully fetched and saved')

        # if path is not specified in settings.json
        if not len(self.settings['path'] ) > 0:
            lib.printFail('Specify path in settings.json file')
            exit()
        else: basePath = self.settings['path']

        # set type of grafic visualization and json file
        # N.B. <type> is passed in arguments when you execute the script
        if type in ['crypto', 'total']: 
            self.type = type
            lib.printWarn(f'Report type: {self.type} wallet')
        else:
            lib.printFail('Unexpected error, pass the correct argument, run again with option --help')
            exit()

        if os.path.isdir(basePath):
            # create the needed folder and json file
            try:
                os.mkdir(basePath)
                os.mkdir(basePath+'\\grafico') 
            except FileExistsError:
                pass
            except FileNotFoundError:
                lib.printFail('Error on init, check path in settings.json')
                exit()
            
            if not os.path.exists(basePath+'\\walletValue.json'):
                open(basePath+'\\walletValue.json', 'w')

            if not os.path.exists(basePath+'\\walletGeneralOverview.json'):
                open(basePath+'\\walletGeneralOverview.json', 'w')
                
            # set paths variable
            self.settings['grafico_path'] = basePath+'\\grafico'
            if self.type == 'total': # set json file based on type
                self.settings['json_path'] = basePath+'\\walletGeneralOverview.json'
            else:
                self.settings['json_path'] = basePath+'\\walletValue.json'
        else: 
            lib.printFail('Specify a correct path in settings.json')
            exit()

    # acquire csv data and convert it to a list
    def loadCSV(self) -> list:
        lib.printWarn('Loading value from input.csv...')
        df = read_csv('input.csv', parse_dates=True) # pandas.read_csv()
        return df.values.tolist() # convert dataFrame to list []

    # CoinGecko retrieve price of a crypto vs currency
    def getPriceOf(self, symbol: str) -> float: 
        if self.provider == 'cg': # coingecko
            # if symbol is the main currency, just return the qta
            # no need to retrieve exchange rate 
            if symbol.upper() == self.settings['currency']:
                return 1

            price = self.cg.getPriceOf(symbol)
            if price == False: # if api wasn't able to retrieve price it return false
                self.invalid_sym.append(symbol)
                lib.printFail(f'Error getting price of {symbol}-{self.settings["currency"]}')
                return False
            return price

        lib.printFail('Unexpected error, incorrect price provider')
        exit()

    # CoinMarketCap retrieve price of a crypto vs currency
    def CMCgetPriceOf(self, symbol: list) -> dict:
        if self.provider == 'cmc': #CoinMarketCap
            symbol = list(symbol)
            symbol = [x.upper() for x in symbol] 
            temp = self.cmc.getPriceOf(symbol)
            if not temp[1]: # if temp[1] is false, it means that one or more prices are missing 
                (dict, _, missing, data) = temp
                self.invalid_sym.extend(list(missing))
                if len(dict) <= 0: # check if all price are missing
                    lib.printFail('Unexpected error, unable to retrieve price data')
                    exit()
            else:
                (dict, _) = temp
            return dict
        lib.printFail('Unexpected error, incorrect price provider')
        exit()

    # print invalid pairs, incorrect symbol
    def showInvalidSymbol(self) -> None:
        if len(self.invalid_sym) > 0:
            lib.printFail('The following pair(s) cannot be found:')
            for i in self.invalid_sym:
                print(f'\t{i}-{self.settings["currency"]}', end=' ')
            print('')

    # convert dict of str to dict of float
    def checkInput(self, crypto: list) -> dict:
        data = dict()
        lib.printWarn('Validating data...')
        
        for (symbol, qta, _addy) in crypto:
            # since input.csv file serves both crypto and total
            # when you calc crypto you DO NOT want eur or usd included
            if self.type == 'crypto' and symbol.lower() in self.supportedCurrency: 
                continue

            # _addy is refering to a certain address of a certain crypto (future use)
            try:
                qta = float(qta) # convert str to float
            except ValueError:
                lib.printFail(f'Error parsing value of {symbol}')
                continue

            # add total_invested from csv to self.total_invested if crypto otherwise igore it
            if symbol == 'total_invested':
                if self.type == 'crypto':
                    self.total_invested = qta
                    continue
                else:
                    continue
            
            # if input.csv contain a symbol multiple time
            if symbol in list(data.keys()): 
                data[symbol] += qta
            else:
                data[symbol] = qta
        return data

    # CoinMarketCap calculate the value of crypto and format data to be used in handleDataPlt()
    def CMCcalcValue(self, crypto: dict):
        data = list()
        tot = 0.0
        lib.printWarn('Retriving current price...')
        rawData = self.CMCgetPriceOf(crypto.keys()) # get prices

        for (symbol, price) in rawData.items(): # unpack and calc value
            value = round(price * crypto[symbol.lower()], 2)
            data.append([symbol, crypto[symbol.lower()], value]) # crypto[symbol] is qta
            tot += value

        if self.type == 'total':
            for (symbol, qta) in crypto.items():
                # you want to exchange the other fiat currency into the currency in settings
                if symbol.upper() != self.settings['currency'] and symbol.lower() in self.supportedCurrency:
                    price = yahooGetPriceOf(f'{self.settings["currency"]}{symbol}=X')
                    value = round(price * qta, 2)
                    data.append([symbol, qta, value])
                    tot += value 

                # if symbol is the main currency, just return the qta
                # no need to retrieve exchange rate 
                if symbol.upper() == self.settings['currency']:
                    value = round(qta, 2)
                    data.append([symbol, qta, value])
                    tot += value

        return {
            'date': str(datetime.now().strftime("%d/%m/%Y %H:%M:%S")), # current data
            'total': round(tot,2), # total value of all crypto
            'currency': self.settings["currency"], 
            'symbol': sorted(data) # is list of [symbol,qta,value]
        }

    # CoinGecko calculate the value of crypto and format data to be used in handleDataPlt()
    def calcValue(self, crypto: dict) -> dict:
        data = list()
        tot = 0.0
        lib.printWarn('Retriving current price...')

        for (symbol, qta) in crypto.items():
            # when you calc total
            # you want to exchange the other fiat currency into the currency in settings
            if self.type == 'total' and symbol.upper() != self.settings['currency'] and symbol.lower() in self.supportedCurrency:
                price = yahooGetPriceOf(f'{self.settings["currency"]}{symbol}=X')
            else:
                # if you calc crypto and isn't a fiat currency
                price = self.getPriceOf(symbol)

            if price == False: # if api cannot retrieve price
                continue # skip

            symbol = symbol.upper()
            value = round(price*qta, 2)
            data.append([symbol,qta,value])
            tot += value

        return {
            'date': str(datetime.now().strftime("%d/%m/%Y %H:%M:%S")), # current data
            'total': round(tot,2), # total value of all crypto
            'currency': self.settings["currency"], 
            'symbol': data # is list of [symbol,qta,value]
        }

    # format data to generate PLT
    # for crypto:
    #   if value of a certain crypto is <= 2%
    #   add special symbol 'other' and sum all crypto whose value is <= 2%
    # 
    # for total:
    #   there are only 2 symbols: crypto and fiat
    #   crypto value is the total sum of cryptos
    #   fiat value is the total sum of fiat and stablecoins converted in self.settings['currency']
    def handleDataPlt(self, dict: dict) -> dict:
        newdict = {
            'total': dict['total'],
            'currency': dict['currency'],
            'symbol': [], # symbolo[0] = [symbol, value]
            'date': dict['date']
        }

        lib.printWarn('Preparing data...')
        if self.type == 'crypto':
            for (symb, _, value) in dict['symbol']:
                if symb in ['other', 'EUR', 'USD']: continue

                # group together all elements in the dictionary whose value is less than 2%
                if value / dict['total'] <= 0.02:
                    if newdict['symbol'][0][0] != 'other': 
                        # create 'other' only once
                        newdict['symbol'] = [['other', 0.0], *newdict['symbol']] # add 'other' as first element

                    newdict['symbol'][0][1] += value # increment value of symbol 'other'
                    # symbolo[0] = [symbol, value]

                else:
                    newdict['symbol'].append([symb, value]) # add symbol to PLT if its value is greater than 2%

            return newdict

        elif self.type == 'total':
            newdict['symbol'].append(['Crypto', 0]) # [<name>, <value>]
            newdict['symbol'].append(['Fiat', 0])

            for (symb, _, value) in dict['symbol']:

                if symb.lower() not in self.supportedCurrency and symb.lower() not in self.supportedStablecoin:
                    newdict['symbol'][0][1] += value # add value to crypto
                else:
                    newdict['symbol'][1][1] += value # add value to fiat

            return newdict
        else:
            lib.printFail('Unexpected error on wallet type, choose crypto or total')

    # create plt, save and show it
    # rawcrypto is needed to save raw data(without 'other' symb) in self.settings['json_path']
    # when --loadJson argument is specified rawcrypto isn't used
    def genPlt(self, dict: dict, rawcrypto = {}) -> None:
        mylabels = [] # symbols
        val = [] # value in currency of symbols

        lib.printWarn('Creating pie chart...')
        for (symb, value) in dict['symbol']: # unpack value and add to correct list
            mylabels.append(symb)
            val.append(value)

        y = array(val) # numpy.array()

        # grafic settings
        sns.set_style('whitegrid')
        #sns.color_palette('pastel')
        # define size of the image
        plt.figure(figsize=(6, 5), tight_layout=True)
        # create a pie chart with value in 'xx.x%' format
        plt.pie(y, labels = mylabels, autopct='%1.1f%%', startangle=90, shadow=False)

        skip = False
        ti = self.total_invested # total invested
        if self.total_invested == 0:
            if 'total_invested' in dict.keys():
                if dict['total_invested'] != 0:
                    ti = dict['total_invested']
                else: skip = True
            else: skip = True # if both are 0

        # add legend and title to pie chart
        plt.legend(title = "Symbols:")
        if self.type == 'crypto' and not skip:
            increasePercent = round((dict['total'] - ti)/ti *100, 2)
            plt.title(f'{self.type.capitalize()} Balance: {dict["total"]} {dict["currency"]} ({increasePercent if self.type == "crypto" else ""}{" ↑" if increasePercent>0 else " ↓" if self.type == "crypto" else ""}) | {dict["date"]}', fontsize=13, weight='bold')
        else:
            plt.title(f'{self.type.capitalize()} Balance: {dict["total"]} {dict["currency"]} | {dict["date"]}', fontsize=13, weight='bold')

        # format filename using current date
        filename = dict['date'].replace("/",'_').replace(':','_').replace(' ',' T')+'.png'

        if not self.load: 
            # when you specify --loadJson you already have json data in walletValue/walletGeneralOverview and image saved
            # so only if --loadJson isn't specified save img and json file
            plt.savefig(f'{self.settings["grafico_path"]}\\{filename}') #save image
            lib.printOk(f'Pie chart image successfully saved in {self.settings["grafico_path"]}\{filename}')
            self.updateJson(rawcrypto, filename) # update walletValue.json

        plt.show() 

    # update data in self.settings['json_path']
    def updateJson(self, crypto: dict, filename: str):
        new_file = ''
        temp = json.dumps({
            'date': crypto['date'],
            'total_value': crypto['total'],
            'total_invested': self.total_invested,
            'currency': crypto['currency'],
            'img_file': filename,
            'crypto': [['COIN, QTA, VALUE IN CURRENCY']]+crypto['symbol'],
            }
        )

        # read dates from json file
        # if today date is already in the json file, overwrite it
        with open(self.settings['json_path'], 'r') as f:
            for line in f:
                try:
                    date = json.loads(line)
                except json.decoder.JSONDecodeError: # sometimes it throw error on line 2
                    pass
                # parse date and convert to dd/mm/yyyy
                new_date = datetime.strptime(date['date'].split(' ')[0], '%d/%m/%Y')
                file_date = datetime.strptime(crypto['date'].split(' ')[0], '%d/%m/%Y')

                if new_date != file_date: # if file dates aren't equal to today's date
                    new_file += line # add line to new file
        
        new_file += temp # add the latest record to new file

        with open(self.settings['json_path'], 'w') as f:
            f.write(f'{new_file}\n')
        
        lib.printOk(f'Data successfully saved in {self.settings["json_path"]}\n')

    # given a past date and json data from a json file, create grafic visualization with a pie chart
    def genPltFromJson(self, filename: str):
        lib.printWelcome('Select one of the following date to load data from.')
        record = []

        with open(filename, 'r') as f:
            for line in f:
                record.append(json.loads(line))
        
        for (i, rec) in enumerate(record):
            print(f"[{i}] {rec['date']}", end='\n')
        
        lib.printWarn('Type one number...')
        gotIndex = False

        while not gotIndex:
            try:
                index = int(input())
                if index >= 0 and index <= len(record):
                    gotIndex = True
                else: lib.printFail('Insert an in range number...')
            except KeyboardInterrupt:
                exit()
            except:
                lib.printFail('Insert a valid number...')

        record = record[index]
        newdict = {
            'total': record['total_value'],
            'currency': record['currency'],
            'symbol': record['crypto'][1:], # skip the first value (["COIN, QTA, VALUE IN CURRENCY"])
            'date': record['date']
        }

        newdict = self.handleDataPlt(newdict)
        if 'total_invested' in record.keys():
            newdict['total_invested'] = record['total_invested']
        else: newdict['total_invested'] = 0
        self.genPlt(newdict)

    # main 
    def calculateValue(self) -> None: 
        if self.load:
            self.genPltFromJson(self.settings['json_path'])
        else:
            rawCrypto = self.loadCSV()
            rawCrypto = self.checkInput(rawCrypto)
            if self.provider == 'cg':
                rawCrypto = self.calcValue(rawCrypto)
            if self.provider == 'cmc':
                rawCrypto = self.CMCcalcValue(rawCrypto)
            if self.invalid_sym:
                self.showInvalidSymbol()

            crypto = self.handleDataPlt(rawCrypto)
            self.genPlt(crypto, rawCrypto)

# 
# See value of you wallet over time
# specify type: crypto or total
# 
class walletBalanceReport:
    # Initialization variable and general settings
    def __init__(self, type) -> None: 
        self.settings = lib.getSettings()
        self.type = type # set type of grafic visualization and json file
        lib.printWelcome(f'Welcome to Wallet Balance Report!')
        if self.type == 'total':
            self.settings['json_path'] = self.settings['path']+ '\\walletGeneralOverview.json'
        elif self.type == 'crypto':
            self.settings['json_path'] = self.settings['path']+ '\\walletValue.json'
        else: 
            lib.printFail('Unexpected error, select crypto or total using arguments.')
            exit()
        lib.printWarn(f'Currency: {self.settings["currency"]}')
        lib.printWarn(f'Report type: {self.type} wallet')

    # get forex rate based on self.settings["currency"]
    def getForexRate(self, line: dict):
        if self.settings["currency"] == 'EUR' and line['currency'] == 'USD':
            # get forex rate using yahoo api
            return yahooGetPriceOf(f'{self.settings["currency"]}{line["currency"]}=X', '', True)
        elif line['currency'] == 'EUR' and self.settings["currency"] == 'USD':
            return yahooGetPriceOf(f'{line["currency"]}{self.settings["currency"]}=X', '', True)
        else:
            lib.printFail('Currency not supported')
            exit()

    # 
    # load all DATETIME from json file
    # to have a complete graph, when the next date is not the following date
    # add the following date and the value of the last updated
    #
    def loadDatetime(self, data):
        lib.printWarn(f'Loading value from {self.settings["json_path"]}...')
        with open(self.settings['json_path'], 'r') as f:
            firstI = True # first interaction
            f = list(f) # each element of 'f' is a line
            for i, line in enumerate(f):
                if type(line) != dict:
                    line = json.loads(line)

                temp_date = lib.parse_formatDate(line['date']) # parse date format: dd/mm/yyyy
                total_value = line['total_value']

                # if currency of json line is different from settings.json currency
                if line['currency'] != self.settings['currency']: 
                    rate = self.getForexRate(line)
                    total_value /= rate # convert value using current forex rate

                if firstI:
                    data['date'].append(temp_date)
                    data['total_value'].append(total_value)
                    firstI = False
                    continue
                
                # calculate the last date in list + 1 day
                lastDatePlus1d = lib.getNextDay(data['date'][-1])
                # check if temp_date (new date to add) is equal to lastDatePlus1d
                if temp_date == lastDatePlus1d:
                    data['total_value'].append(total_value)
                else:
                    data['total_value'].append(data['total_value'][-1])
                    f.insert(int(i)+1, line)
                    # add line again because we added the same amount of the last in list
                    # otherwise it didn't work properly

                data['date'].append(lastDatePlus1d)

        return data

    # parse and format data to create PLT
    def genPlt(self):
        data = {
            'date': [],
            'total_value': [],
            'currency': self.settings['currency']
        }

        data = self.loadDatetime(data)

        # create line chart
        lib.printWarn(f'Creating chart...')
        # set back ground [white, dark, whitegrid, darkgrid, ticks]
        sns.set_style('darkgrid') 
        # define size of the image
        plt.figure(figsize=(7, 6), tight_layout=True)
        plt.plot(data['date'], data['total_value'], color='red', marker='')
        plt.title(f'{self.type.capitalize()} Balance from {data["date"][0].strftime("%d %b %Y")} to {data["date"][-1].strftime("%d %b %Y")} \nCurrency: {self.settings["currency"]}', fontsize=14, weight='bold') # add title
        # changing the fontsize and rotation of x ticks
        plt.xticks(fontsize=6.5, rotation = 45)
        plt.show()

# 
# See amount and fiat value of a single crypto over time
# a crypto ticker will be asked as user input from a list
# 
class cryptoBalanceReport:
    # Initialization variable and general settings
    def __init__(self) -> None: 
        self.settings = lib.getSettings()
        lib.printWelcome(f'Welcome to Crypto Balance Report!')
        self.settings['json_path'] = self.settings['path']+ '\\walletValue.json'
        self.cryptos = set()
        self.ticker = ''
        self.type = ''
        self.data = {
            'date': [],
            'amt': [],
            'fiat': []
        }

    # retrieve all cryptos ever recorded in json file
    def retrieveCryptoList(self) -> None:
        with open(self.settings['json_path'], 'r') as f:
            for line in f:
                clist = json.loads(line)['crypto'][1:] # skip the first element, it's ["COIN, QTA, VALUE IN CURRENCY"]
                for sublist in clist:
                    if sublist[0].isupper():
                        self.cryptos.add(sublist[0])
        
        self.cryptos = sorted(list(self.cryptos))

    # ask user input for a crypto from a list
    def getTickerInput(self) -> None:
        for (i, r) in enumerate(self.cryptos):
            print(f"[{i}] {r}", end='\n')
        
        lib.printWarn('Type one number...')
        gotIndex = False

        while not gotIndex:
            try:
                index = int(input())
                if index >= 0 and index < len(self.cryptos):
                    gotIndex = True
                else: lib.printFail('Insert an in range number...')
            except:
                lib.printFail('Insert a valid number...')
        
        self.ticker = self.cryptos[index]

    # OUTDATED CODE
    # ask user input to choose type
    def getTypeInput(self) -> None:
        lib.printWarn('Choose between: ')
        print('[1] Amount\n[2] Fiat Value')
        gotIndex = False

        while not gotIndex:
            try:
                index = int(input())
                if index in [1,2] :
                    gotIndex = True
                else: lib.printFail('Insert an in range number...')
            except:
                lib.printFail('Insert a valid number...')
        
        if index == 1:
            self.type = 'amt'
        elif index == 2:
            self.type = 'fiat'
        else: exit()

    # collect amount and date
    # fill amounts of all empty day with the last available
    def retrieveAmountOverTime(self) -> None:
        lib.printWarn(f'Loading value from {self.settings["json_path"]}...')
        with open(self.settings['json_path'], 'r') as f:
            firstI = True # first interaction
            f = list(f) # each element of 'f' is a line
            for index, line in enumerate(f):
                temp = json.loads(line)
                temp['date'] = lib.parse_formatDate(temp['date'])
                clist = temp['crypto'][1:] # skip the first element, it's ["COIN, QTA, VALUE IN CURRENCY"]
                for sublist in clist:
                    if sublist[0] == self.ticker:
                        if firstI: # first iteration of external loop
                            self.data['amt'].append(sublist[1])
                            self.data['fiat'].append(sublist[2])
                            self.data['date'].append(temp['date'])
                            firstI = False
                            continue
                        
                        # calculate the last date in list + 1 day
                        lastDatePlus1d = lib.getNextDay(self.data['date'][-1])
                        # check if temp['date'] (new date to add) is equal to lastDatePlus1d
                        if temp['date'] == lastDatePlus1d:
                            self.data['amt'].append(sublist[1])
                            self.data['fiat'].append(sublist[2])
                        else:
                            self.data['amt'].append(self.data['amt'][-1])
                            self.data['fiat'].append(self.data['fiat'][-1])
                            f.insert( int(index)+1, line) 
                            # add line again because we added the same amount of the last in list
                            # otherwise it didn't work properly
                        self.data['date'].append(lastDatePlus1d)

        # add zero value
        day0 = lib.getPreviousDay(self.data['date'][0])
        self.data['date'] = [day0, *self.data['date']]
        self.data['amt'] = [0, * self.data['amt']]
        self.data['fiat'] = [0, *self.data['fiat']]

    def genPlt(self) -> None:
        self.retrieveCryptoList()
        self.getTickerInput()
        #self.getTypeInput()
        self.retrieveAmountOverTime()

        lib.printWarn(f'Creating chart...')
        # set background [white, dark, whitegrid, darkgrid, ticks]
        sns.set_style('darkgrid') 

        # create 2 subplots for amount and value over time
        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        ax1.plot(self.data['date'], self.data['amt'], 'g-')
        ax2.plot(self.data['date'], self.data['fiat'], 'r-')
        ax1.set_xlabel('Dates')
        ax1.set_ylabel('Amount', color='g')
        ax2.set_ylabel('Fiat Value', color='r')
        # add title
        plt.title(f'Amount and fiat value of {self.ticker} in eur from {self.data["date"][0].strftime("%d %b %Y")} to {self.data["date"][-1].strftime("%d %b %Y")}', fontsize=12, weight='bold')
        # changing the fontsize and rotation of x ticks
        plt.xticks(fontsize=6.5, rotation = 45)
        plt.show()

# 
# Unimplemented
# 
class retrieveCryptoBalance:
    def __init__(self) -> None:
        pass

# parse arguments
def get_args(): 
    parser = argparse.ArgumentParser()
    parser.add_argument('-c','--crypto', dest='crypto', action="store_true", help='view balance of crypto assets')
    parser.add_argument('-t','--total', dest='total',action="store_true", help='view balance of fiat vs crypto assets')
    parser.add_argument('--calc', dest='calcV',action="store_true", help='calculate wallet value')
    parser.add_argument('-r','--report', dest='report',action="store_true", help='view wallet value over time')
    parser.add_argument('--loadJson', dest='load', action='store_true', help='load past data and view it')
    parser.add_argument('--singleCrypto', dest='reportSingleCrypto', action='store_true', help='view balance of a crypto over time')
    option = parser.parse_args()
    if (not option.calcV and not option.report) or (not option.crypto and not option.total and not option.reportSingleCrypto):
        parser.error("[-] Specify value or report and crypto or total balance")
    return option

if __name__ == '__main__':
    option = get_args()

    if (option.report or option.calcV or option.load) and (option.crypto or option.total or option.reportSingleCrypto):
        if option.report:
            if option.crypto:
                main = walletBalanceReport('crypto')
            elif option.total:
                main = walletBalanceReport('total')
            elif option.reportSingleCrypto:
                main = cryptoBalanceReport()
            else: 
                lib.printFail('Select crypto or total option')
                exit
            main.genPlt()

        elif option.calcV:
            if option.load:
                if option.crypto:
                    main = calculateWalletValue('crypto', True)
                elif option.total:
                    main = calculateWalletValue('total', True)
            elif not option.load:
                if option.crypto:
                    main = calculateWalletValue('crypto')
                elif option.total:
                    main = calculateWalletValue('total')
            else: 
                lib.printFail('Select crypto or total option')
                exit
            main.calculateValue()
        else:
            lib.printFail('Select calculate or report option')
            exit
