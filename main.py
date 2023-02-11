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
# add your crypto and fiat in input.csv
# fill currency, provider and path in settings.json
# specify type: crypto or total
# type affect only the visualization of the data
# wallet data is calculated the same way with both crypto and total type
# 
class calculateWalletValue:
    # Initialization variable and general settings
    def __init__(self, type: str, load = False, privacy = False) -> None:
        self.settings = lib.getSettings()
        self.version = 'CWV_1.0'
        self.invalid_sym = []
        self.provider = ''
        self.supportedFiat =  ['eur', 'usd']
        self.supportedStablecoin = ['usdt', 'usdc','dai']
        self.load = load # option to load data from json, see calculateWalletValue.genPltFromJson()
        self.privacy = privacy
        self.wallet = {
            # stable, crypto and fiat are structured so 
            # {<symbol>: [<amount>, <value>], ...}
            'stable': dict(),
            'crypto': dict(),
            'fiat': dict(),
            'total_invested': 0,
            'currency': self.settings['currency']
        }
        lib.printWelcome(f'Welcome to Calculate Wallet Value!')
        lib.printWarn(f'Currency: {self.wallet["currency"]}')
        lib.printWarn(f'Privacy: {"ON" if self.privacy else "OFF"}')

        # if path is not specified in settings.json
        if not len(self.settings['path'] ) > 0:
            lib.printFail('Specify path in settings.json file')
            exit()
        else: basePath = self.settings['path']

        # set price provider
        if self.settings['provider'] == 'cg':
            lib.printWarn('Api Provider: CoinGecko')
            self.provider = 'cg'
            self.cg = cg_api(self.wallet["currency"])
        elif self.settings['provider'] == 'cmc':
            lib.printWarn('Api Provider: CoinMarketCap')
            self.provider = 'cmc'
            self.cmc = cmc_api(self.wallet["currency"], self.settings['CMC_key'])
        else:
            lib.printFail("Specify a correct price provider")
            exit()

        # fetch all crypto symbol and name from CoinGecko or CoinMarketCap
        # run once or if there is any new crypto
        if self.settings['fetchSymb'] == True: 
            if self.provider == 'cg':
                self.cg.fetchID()
            if self.provider == 'cmc':
                self.cmc.fetchID()
            lib.printOk('Coin list successfully fetched and saved')

        # set type
        if type in ['crypto', 'total']: 
            self.type = type
            lib.printWarn(f'Report type: {self.type} wallet')
        else:
            lib.printFail('Unexpected error, pass the correct argument, run again with option --help')
            exit()

        if os.path.isdir(basePath):
            # create the needed folder and json file
            try:
                if not os.path.isdir(basePath+'\\grafico'):
                    os.mkdir(basePath+'\\grafico') 
            except FileExistsError:
                pass
            except FileNotFoundError:
                lib.printFail('Error on init, check path in settings.json')
                exit()
            
            if not os.path.exists(basePath+'\\walletValue.json'):
                open(basePath+'\\walletValue.json', 'w')
            
            # set paths variable
            self.settings['grafico_path'] = basePath+'\\grafico'
            self.settings['json_path'] = basePath+'\\walletValue.json'
        else:
            lib.printFail('Specify a correct path in settings.json')
            exit()

    # acquire csv data and convert it to a list
    # return a list
    def loadCSV(self) -> list:
        lib.printWarn('Loading value from input.csv...')
        df = read_csv('input.csv', parse_dates=True) # pandas.read_csv()
        return df.values.tolist() # convert dataFrame to list []

    # CoinGecko retrieve price of a single crypto
    # return a float
    def CGgetPriceOf(self, symbol: str) -> float: 
        if self.provider == 'cg': # coingecko
            price = self.cg.getPriceOf(symbol.lower())
            if price == False: # if api wasn't able to retrieve price it return false
                self.invalid_sym.append(symbol)
                return False
            return price

        lib.printFail('Unexpected error, incorrect price provider')
        exit()

    # CoinMarketCap retrieve price of multiple crypto
    # return a dict with symbol as key and price as value
    def CMCgetPriceOf(self, symbol: list) -> dict:
        if self.provider == 'cmc': #CoinMarketCap
            symbol = [x.upper() for x in symbol] 
            temp = self.cmc.getPriceOf(symbol)
            if not temp[1]: # if temp[1] is false, it means that one or more prices are missing, see api.py for more info
                (dict, _, missing, _) = temp
                self.invalid_sym.extend(list(missing))
                if len(dict) <= 0: # check if all price are missing
                    lib.printFail('Unexpected error, unable to retrieve price data')
                    exit()
            else:
                (dict, _) = temp
            return dict
        lib.printFail('Unexpected error, incorrect price provider')
        exit()

    # print invalid pairs or incorrect symbol
    def showInvalidSymbol(self) -> None:
        if len(self.invalid_sym) > 0:
            lib.printFail('The following pair(s) cannot be found:')
            for ticker in self.invalid_sym:
                print(f'\t{ticker}-{self.wallet["currency"]}', end=' ')
            print('')

    # check data and sort assets in crypto, stable and fiat
    def checkInput(self, crypto: list) -> dict:
        lib.printWarn('Validating data...')
        
        # value refer to 'label' column in input.csv and it's NOT used
        # when self.load is true INSTEAD value refer to fiat value in the 
        # list 'crypto' walletValue.json inside and it is used
        for (symbol, qta, value) in crypto:
            try:
                qta = float(qta) # convert str to float
            except ValueError:
                lib.printFail(f'Error parsing value of {symbol}')
                self.invalid_sym.append(str(symbol))
                continue

            # add total_invested from csv to self.wallet['total_invested']
            if symbol == 'total_invested':
                self.wallet['total_invested'] = qta
                continue

            # this block of 3 if statement sort the symbol 
            # in fiat, stablecoin crypto
            if symbol.lower() in self.supportedFiat: 
                if symbol.upper() in self.wallet['fiat'].keys():
                    # when symbol is already in wallet
                    # add new qta (+=)
                    self.wallet['fiat'][str(symbol).upper()][0] += qta
                else: 
                    # when symbol is NOT in wallet
                    if self.load:
                        # when self.load is true add qta and value directly
                        # without += operator since, it get wallet data 
                        # from walletValue.json record
                        # this implies that qta and value is correct
                        self.wallet['fiat'][str(symbol).upper()] = [qta, value]
                    else: 
                        # add qta, value will be calculated later
                        self.wallet['fiat'][str(symbol).upper()] = [qta, 0.0]

            elif symbol.lower() in self.supportedStablecoin:
                if symbol.upper() in self.wallet['stable'].keys():
                    self.wallet['stable'][str(symbol).upper()][0] += qta
                else: 
                    if self.load:
                        self.wallet['stable'][str(symbol).upper()] = [qta, value]
                    else: self.wallet['stable'][str(symbol).upper()] = [qta, 0.0]

            else:
                if symbol.upper() in self.wallet['crypto'].keys():
                    self.wallet['crypto'][str(symbol).upper()][0] += qta
                else: 
                    if self.load:
                        self.wallet['crypto'][str(symbol).upper()] = [qta, value]
                    else: self.wallet['crypto'][str(symbol).upper()] = [qta, 0.0]

    # CoinMarketCap calculate the value of crypto and format data to be used in handleDataPlt()
    def CMCcalcValue(self):
        tot = 0.0
        tot_crypto_stable = 0.0
        lib.printWarn('Retriving current price...')

        # get prices of crypto and stable
        cryptoList = list(self.wallet['crypto'].keys())
        stableList = list(self.wallet['stable'].keys())
        rawData = self.CMCgetPriceOf(cryptoList+stableList)

        # unpack value and divide it back to crypto and stable
        for (symbol, price) in rawData.items():
            if symbol in cryptoList:
                value = round(price * self.wallet['crypto'][symbol][0] ,2) # price * qta
                self.wallet['crypto'][symbol][1] = value
                tot += value
                tot_crypto_stable += value
            
            elif symbol in stableList:
                value = round(price * self.wallet['stable'][symbol][0] ,2) # price * qta
                self.wallet['stable'][symbol][1] = value
                tot += value
                tot_crypto_stable += value
            
            else:
                lib.printFail(f'Unexpected error, {symbol} not reconised')
                continue

        for (symbol, [qta, _]) in self.wallet['fiat'].items():
            # if symbol is the main currency -> return the qta
            if symbol.upper() == self.wallet["currency"]:
                value = round(qta, 2)
                tot += value
                self.wallet['fiat'][symbol][1] = value

            # you want to exchange the other fiat currency into the currency in settings
            elif symbol.lower() in self.supportedFiat:
                price = yahooGetPriceOf(f'{self.wallet["currency"]}{symbol}=X')
                value = round(price * qta, 2)
                self.wallet['fiat'][symbol][1] = value
                tot += value 
            else:
                self.invalid_sym.append(symbol)

        self.wallet['total_value'] = round(tot, 2)
        self.wallet['total_crypto_stable'] = round(tot_crypto_stable, 2)
        self.wallet['date'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # CoinGecko calculate the value of crypto and format data to be used in handleDataPlt()
    def CGcalcValue(self) -> dict:
        tot = 0.0
        tot_crypto_stable = 0.0
        lib.printWarn('Retriving current price...')

        # retrieve price and calc value
        for (symbol, [qta, _]) in self.wallet['crypto'].items():
            price = self.CGgetPriceOf(symbol)
            if price == False: # if api cannot retrieve price
                continue # skip

            value = round(price*qta, 2)
            self.wallet['crypto'][symbol][1] = value
            tot += value
            tot_crypto_stable += value

        for (symbol, [qta, _]) in self.wallet['stable'].items():
            price = self.CGgetPriceOf(symbol)
            if price == False: # if api cannot retrieve price
                continue # skip

            value = round(price*qta, 2)
            self.wallet['stable'][symbol][1] = value
            tot += value
            tot_crypto_stable += value

        for (symbol, [qta, _]) in self.wallet['fiat'].items():
            # if symbol is the main currency, just return the qta
            if symbol.upper() == self.wallet["currency"]:
                price = 1
            elif symbol.lower() in self.supportedFiat:
                # you want to exchange the other fiat currency into the currency in settings
                price = yahooGetPriceOf(f'{self.wallet["currency"]}{symbol}=X')
            else:
                self.invalid_sym.append(symbol)
                continue

            value = round(price*qta, 2)
            self.wallet['fiat'][symbol][1] = value
            tot += value

        self.wallet['total_value'] = round(tot, 2)
        self.wallet['total_crypto_stable'] = round(tot_crypto_stable, 2)
        self.wallet['date'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # format data to generate PLT
    # for crypto:
    #   if value of a certain crypto is <= 2%
    #   add special symbol 'other' and sum all crypto whose value is <= 2%
    # 
    # for total:
    #   there are only 2 symbols: crypto and fiat
    #   crypto value is the total sum of cryptos
    #   fiat value is the total sum of fiat and stablecoins converted in self.wallet["currency"]
    def handleDataPlt(self) -> list:
        symbol_to_visualize = list()  # [ [symbol, value], ...]
        lib.printWarn('Preparing data...')
        if self.type == 'crypto':
            temp = self.wallet['stable'] | self.wallet['crypto'] # merge into one dict
            for (symbol, [_, value]) in temp.items():
                if symbol == 'other': continue

                # group together all element whose value is <= than 2% 
                if value / self.wallet['total_crypto_stable'] <= 0.02:
                    if symbol_to_visualize[0][0] != 'other':
                        # add 'other' as first element
                        symbol_to_visualize = [['other', 0.0], *symbol_to_visualize]
                    # increment value of symbol 'other'
                    symbol_to_visualize[0][1] += value
                else: symbol_to_visualize.append([symbol, value])
            
            return symbol_to_visualize
        
        elif self.type == 'total':
            symbol_to_visualize = [
                ['Crypto', 0.0], ['Fiat', 0.0]
            ]
            temp = self.wallet['stable'] | self.wallet['crypto'] | self.wallet['fiat'] # merge into one dict
            for (symbol, [_, value]) in temp.items():
                if symbol.lower() not in self.supportedFiat and symbol.lower() not in self.supportedStablecoin:
                    # crypto
                    symbol_to_visualize[0][1] += value
                else: 
                    # stable and fiat
                    symbol_to_visualize[1][1] += value
            return symbol_to_visualize
        else:
            lib.printFail('Unexpected error on wallet type, choose crypto or total')
            exit()

    # create a pie chart, save it(unless self.load is checked) and show it
    def genPlt(self, symbol_to_visualize: list, ) -> None:
        mylabels = [] # symbols
        val = [] # value in currency of symbols

        lib.printWarn('Creating pie chart...')
        for (symb, value) in symbol_to_visualize:
            mylabels.append(symb)
            val.append(value)

        y = array(val)# numpy.array()

        # grafic settings
        sns.set_style('whitegrid')
        #sns.color_palette('pastel')
        # define size of the image
        plt.figure(figsize=(6, 5), tight_layout=True)
        # create a pie chart with value in 'xx.x%' format
        plt.pie(y, labels = mylabels, autopct='%1.1f%%', startangle=90, shadow=False)

        # add legend and title to pie chart
        plt.legend(title = "Symbols:")
        if self.privacy:
            # do not show total value
            plt.title(f'{self.type.capitalize()} Balance: ***** {self.wallet["currency"]} | {self.wallet["date"]}', fontsize=13, weight='bold')
 
        elif self.type == 'crypto' and self.wallet['total_invested'] > 0:
            # if type == crypto AND total_invested > 0
            # show total value and percentage of change given total_invested
            increasePercent = round((self.wallet['total_crypto_stable'] - self.wallet['total_invested'])/self.wallet['total_invested'] *100, 2)
            plt.title(f'{self.type.capitalize()} Balance: {self.wallet["total_crypto_stable"]} {self.wallet["currency"]} ({increasePercent}{" ↑" if increasePercent>0 else " ↓"}) | {self.wallet["date"]}', fontsize=13, weight='bold')
        else:
            # if type == total OR
            # if type == crypto AND total_invested <= 0
            if self.type == 'crypto':
                total = self.wallet['total_crypto_stable']
            elif self.type == 'total':
                total = self.wallet['total_value']
            else: exit()

            # show total value
            plt.title(f'{self.type.capitalize()} Balance: {total} {self.wallet["currency"]} | {self.wallet["date"]}', fontsize=13, weight='bold')

        # format filename using current date
        filename = self.wallet['date'].replace("/",'_').replace(':','_').replace(' ',' T')+'.png'

        if not self.load:
            # when load is enabled it get data from past record from walletValue.json
            # so you do NOT need to save the img and do NOT need to update json file
            plt.savefig(f'{self.settings["grafico_path"]}\\{"C_" if self.type == "crypto" else "T_" if self.type == "total" else ""}{filename}') #save image
            lib.printOk(f'Pie chart image successfully saved in {self.settings["grafico_path"]}\{"C_" if self.type == "crypto" else "T_" if self.type == "total" else ""}{filename}')
            self.updateJson()

        plt.show()

    # return a list containing all asset in self.wallet
    # the list is composed of other list that are composed so:
    # [symbol, qta, value]
    def getWalletAsList(self) -> list:
        li = list()
        temp =  self.wallet['crypto'] | self.wallet['stable'] | self.wallet['fiat'] # merge dict
        for (symbol, [qta, value]) in temp.items():
            li.append([symbol, qta, value]) # convert dict to list
        return li

    # append the record in walletValue.json
    # it overwrite the record with the same date of today
    def updateJson(self):
        new_file = ''
        temp = json.dumps({ # data to be dumped
            'date': self.wallet['date'],
            'total_value': self.wallet['total_value'],
            'total_crypto_stable': self.wallet['total_crypto_stable'],
            'total_invested': self.wallet['total_invested'],
            'currency': self.wallet['currency'],
            'price_provider': f"{'coinMarkerCap' if self.provider == 'cmc' else 'coinGecko' if self.provider == 'cg' else ''}",
            'crypto': [['COIN, QTA, VALUE IN CURRENCY']]+self.getWalletAsList(), # all symbols
            }
        )

        # read dates from json file
        # store the updated record so
        # if today's date is already in the json file, overwrite it,
        with open(self.settings['json_path'], 'r') as f:
            for line in f:
                try:
                    date = json.loads(line)
                except json.decoder.JSONDecodeError: # sometimes it throw error on line 2
                    pass
                # parse date and convert to dd/mm/yyyy
                old_file_date = datetime.strptime(date['date'].split(' ')[0], '%d/%m/%Y')
                new_date = datetime.strptime(self.wallet['date'].split(' ')[0], '%d/%m/%Y')

                if old_file_date != new_date: # if file dates aren't equal to today's date
                    new_file += line # add line to new file
        
        # add the latest record to new file
        new_file += temp

        with open(self.settings['json_path'], 'w') as f:
            f.write(f'{new_file}\n')
        
        lib.printOk(f'Data successfully saved in {self.settings["json_path"]}\n')

    # given a past date and json data from walletValue.json file, 
    # create a pie chart
    def genPltFromJson(self):
        lib.printWelcome('Select one of the following date to load data from.')
        record = []

        # load records of json file
        with open(self.settings['json_path'], 'r') as f:
            for line in f:
                record.append(json.loads(line))
        # print all date of records
        for (i, rec) in enumerate(record):
            print(f"[{i}] {rec['date']}", end='\n')

        # get user inputs 
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

        lib.printWarn('Choose between crypto and total visualization:')
        gotType = False
        type = ''
        while not gotType:
            try:
                type = input().lower()
                if type in ['crypto', 'total']:
                    self.load = True
                    self.type = type
                    gotType = True
                else: lib.printFail('Insert a valid option("crypto" or "total")...')
            except KeyboardInterrupt:
                exit()
            except:
                lib.printFail('Insert a valid string...')

        # set variable to use genPlt()
        self.wallet['total_crypto_stable'] = record['total_crypto_stable']
        self.wallet['total_value'] = record['total_value']
        self.wallet['date'] = record['date']
        self.wallet['currency'] = record['currency']

        self.checkInput(record['crypto'][1:]) # skip the first element, it's ["COIN, QTA, VALUE IN CURRENCY"]
        newdict = self.handleDataPlt()
        # if total invested is in the input.csv
        if 'total_invested' in record.keys():
            self.wallet['total_invested'] = record['total_invested']
        else: self.wallet['total_invested'] = 0

        self.genPlt(newdict)

    # main 
    def run(self) -> None: 
        if self.load:
            self.genPltFromJson()
        else:
            rawCrypto = self.loadCSV()
            self.checkInput(rawCrypto)
            if self.provider == 'cg':
                rawCrypto = self.CGcalcValue()
            if self.provider == 'cmc':
                rawCrypto = self.CMCcalcValue()
            if self.invalid_sym:
                self.showInvalidSymbol()

            crypto = self.handleDataPlt()
            self.genPlt(crypto)

# 
# See value of your crypto/total wallet over time
# based on previous saved data in walletValue.json
# 
class walletBalanceReport:
    # Initialization variable and general settings
    def __init__(self, type: str) -> None: 
        self.settings = lib.getSettings()
        self.version = 'WBR_1.0'
        self.settings['json_path'] = self.settings['path']+ '\\walletValue.json'
        self.data = {
            'date': [],
            'total_value': [],
            'currency': self.settings['currency']
        }
        lib.printWelcome(f'Welcome to Wallet Balance Report!')
        lib.printWarn(f'Currency: {self.settings["currency"]}')
        # set type
        # N.B. <type> is passed in arguments when you execute the script
        if type in ['crypto', 'total']: 
            self.type = type
            lib.printWarn(f'Report type: {self.type} wallet')
        else:
            lib.printFail('Unexpected error, pass the correct argument, run again with option --help')
            exit()

    # get forex rate based on self.settings["currency"]
    def getForexRate(self, line: dict):
        if self.settings["currency"] == 'EUR' and line['currency'] == 'USD':
            # get forex rate using yahoo api
            return yahooGetPriceOf(f'{self.settings["currency"]}{line["currency"]}=X')
        elif self.settings["currency"] == 'USD' and line['currency'] == 'EUR':
            return yahooGetPriceOf(f'{line["currency"]}{self.settings["currency"]}=X')
        else:
            return False

    # 
    # load all DATETIME from json file
    # to have a complete graph, when the next date is not the following date
    # add the following date and the value of the last updated
    #
    def loadDatetime(self) -> None:
        lib.printWarn(f'Loading value from {self.settings["json_path"]}...')
        with open(self.settings['json_path'], 'r') as f:
            firstI = True # first interaction
            f = list(f) # each element of 'f' is a line
            for i, line in enumerate(f):
                if type(line) != dict:
                    line = json.loads(line)

                # check field needed
                if 'total_crypto_stable' not in line.keys() and self.type == 'crypto':
                    continue
                if 'total_value' not in line.keys() and self.type == 'total':
                    continue

                temp_date = lib.parse_formatDate(line['date']) # parse date format: dd/mm/yyyy
                if self.type == 'total':
                    total_value = line['total_value']
                elif self.type == 'crypto':
                    total_value = line['total_crypto_stable']
                else: 
                    lib.printFail('Unexpected error')
                    exit()

                # if currency of json line is different from settings.json currency
                if line['currency'] != self.settings['currency']: 
                    rate = self.getForexRate(line)
                    if not rate:
                        lib.printFail(f'Currency not supported, check {self.settings["json_path"]} line: {i+1}')
                        exit()
                    total_value /= rate # convert value using current forex rate

                if firstI:
                    self.data['date'].append(temp_date)
                    self.data['total_value'].append(total_value)
                    firstI = False
                    continue
                
                # calculate the last date in list + 1 day
                lastDatePlus1d = lib.getNextDay(self.data['date'][-1])
                # check if temp_date (new date to add) is equal to lastDatePlus1d
                if temp_date == lastDatePlus1d:
                    self.data['total_value'].append(total_value)
                else:
                    self.data['total_value'].append(self.data['total_value'][-1])
                    f.insert(int(i)+1, line)
                    # add line again because we added the same amount of the last in list
                    # otherwise it didn't work properly

                self.data['date'].append(lastDatePlus1d)

    # create PLT
    def genPlt(self):
        lib.printWarn(f'Creating chart...')
        # set back ground [white, dark, whitegrid, darkgrid, ticks]
        sns.set_style('darkgrid') 
        # define size of the image
        plt.figure(figsize=(7, 6), tight_layout=True)
        plt.plot(self.data['date'], self.data['total_value'], color='red', marker='')
        plt.title(f'{self.type.capitalize()} Balance from {self.data["date"][0].strftime("%d %b %Y")} to {self.data["date"][-1].strftime("%d %b %Y")} \nCurrency: {self.settings["currency"]}', fontsize=14, weight='bold') # add title
        # changing the fontsize and rotation of x ticks
        plt.xticks(fontsize=6.5, rotation = 45)
        plt.show()

    def run(self) -> None:
        self.loadDatetime()
        self.genPlt()

# 
# See amount and fiat value of a single crypto over time
# based on previous saved data in walletValue.json
# a crypto ticker will be asked as user input
# 
class cryptoBalanceReport:
    # Initialization variable and general settings
    def __init__(self) -> None: 
        self.settings = lib.getSettings()
        self.version = 'CBR_1.0'
        lib.printWelcome(f'Welcome to Crypto Balance Report!')
        self.settings['json_path'] = self.settings['path']+ '\\walletValue.json'
        self.cryptos = set()
        self.ticker = ''
        self.data = {
            'date': [],
            'amount': [],
            'fiat': []
        }

    # retrieve all cryptos ever recorded in json file
    def retrieveCryptoList(self) -> None:
        with open(self.settings['json_path'], 'r') as f:
            for line in f:
                crypto_list = json.loads(line)['crypto'][1:] # skip the first element, it's ["COIN, QTA, VALUE IN CURRENCY"]
                for sublist in crypto_list:
                    if sublist[0].isupper():
                        self.cryptos.add(sublist[0])
        
        self.cryptos = sorted(list(self.cryptos))

    # ask a crypto from user input given a list
    def getTickerInput(self) -> None:
        for (i, r) in enumerate(self.cryptos):
            print(f"[{i}] {r}", end='\n')
        
        lib.printWarn('Type one number...')
        gotIndex = False

        while not gotIndex:
            try:
                index = int(input())
                if index >= 0 and index <= len(self.cryptos):
                    gotIndex = True
                else: lib.printFail('Insert an in range number...')
            except KeyboardInterrupt:
                exit()
            except:
                lib.printFail('Insert a valid number...')
        
        self.ticker = self.cryptos[index]

    # collect amount, fiat value and date
    # fill amounts of all empty day with the last available
    def retrieveDataFromJson(self) -> None:
        lib.printWarn(f'Loading value from {self.settings["json_path"]}...')
        with open(self.settings['json_path'], 'r') as file:
            firstI = True # first interaction
            file = list(file) # each element of file is a line
            for index, line in enumerate(file):
                temp = json.loads(line)
                temp['date'] = lib.parse_formatDate(temp['date'])
                crypto_list = temp['crypto'][1:] # skip the first element, it's ["COIN, QTA, VALUE IN CURRENCY"]
                isfound = False
                for item in crypto_list:
                    if item[0] == self.ticker: # filter using user's input ticker
                        isfound = True
                        if firstI: # first iteration of external loop
                            self.data['amount'].append(item[1])
                            self.data['fiat'].append(item[2])
                            self.data['date'].append(temp['date'])
                            firstI = False
                            continue
                        
                        # calculate the last date in self.data['date'] + 1 day
                        lastDatePlus1d = lib.getNextDay(self.data['date'][-1])
                        # check if the new date to add is equal to lastDatePlus1d
                        if temp['date'] == lastDatePlus1d:
                            self.data['amount'].append(item[1])
                            self.data['fiat'].append(item[2])
                        else:
                            self.data['amount'].append(self.data['amount'][-1])
                            self.data['fiat'].append(self.data['fiat'][-1])
                            file.insert( int(index)+1, line) 
                            # add line again because we added the same amount of the last in list
                            # otherwise it didn't work properly
                        self.data['date'].append(lastDatePlus1d)
                if isfound == False:
                    if firstI:
                        # begin to add values from when self.ticker exist in json file
                        continue

                    # if self.ticker is not found and it's not the first iteration
                    # it means that self.ticker is being sold so amount = 0 and value = 0
                    self.data['amount'].append(0)
                    self.data['fiat'].append(0)     
                    self.data['date'].append(temp['date'])
                    isfound = False

    def genPlt(self) -> None:
        lib.printWarn(f'Creating chart...')
        # set background [white, dark, whitegrid, darkgrid, ticks]
        sns.set_style('darkgrid') 

        # create 2 subplots for amount and value over time
        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        ax1.plot(self.data['date'], self.data['amount'], 'g-')
        ax2.plot(self.data['date'], self.data['fiat'], 'r-')
        ax1.set_xlabel('Dates')
        ax1.set_ylabel('Amount', color='g')
        ax2.set_ylabel('Fiat Value', color='r')
        # add title
        plt.title(f'Amount and fiat value of {self.ticker} in {self.settings["currency"]} from {self.data["date"][0].strftime("%d %b %Y")} to {self.data["date"][-1].strftime("%d %b %Y")}', fontsize=12, weight='bold')
        # changing the fontsize and rotation of x ticks
        plt.xticks(fontsize=6.5, rotation = 45)
        plt.show()

    def run(self) -> None:
        self.retrieveCryptoList()
        self.getTickerInput()
        self.retrieveDataFromJson()
        self.genPlt()

# parse arguments
def get_args(): 
    parser = argparse.ArgumentParser()
    parser.add_argument('--crypto', dest='crypto', action="store_true", help='view balance of crypto assets')
    parser.add_argument('--total', dest='total',action="store_true", help='view balance of fiat vs crypto assets')
    parser.add_argument('--calc', dest='calc',action="store_true", help='calculate wallet value')
    parser.add_argument('--report', dest='report',action="store_true", help='view wallet value over time')
    parser.add_argument('--privacy', dest='privacy', action='store_true', help='obscure total value when used combined with --calc')
    parser.add_argument('--load', dest='load', action='store_true', help='load one past date and view it')
    parser.add_argument('--singleCrypto', dest='singleCrypto', action='store_true', help='view balance of a crypto over time')
    parser.add_argument('--version', dest='version', action='store_true', help='')
    option = parser.parse_args()
    return option

if __name__ == '__main__':
    option = get_args()
    run = False
    if option.calc:
        if option.crypto:
            if option.privacy:
                if option.load:
                    main = calculateWalletValue('crypto', privacy=True, load=True)
                    run = True
                else:
                    main = calculateWalletValue('crypto', privacy=True, load=False)
                    run = True
            else:
                if option.load:
                    main = calculateWalletValue('crypto', privacy=False, load=True)
                    run = True
                else:
                    main = calculateWalletValue('crypto', privacy=False, load=False)
                    run = True
        elif option.total:
            if option.privacy:
                if option.load:
                    main = calculateWalletValue('total', privacy=True, load=True)
                    run = True
                else:
                    main = calculateWalletValue('total', privacy=True, load=False)
                    run = True
            else:
                if option.load:
                    main = calculateWalletValue('total', privacy=False, load=True)
                    run = True
                else:
                    main = calculateWalletValue('total', privacy=False, load=False)
                    run = True

    elif option.report:
        if option.crypto:
            main = walletBalanceReport('crypto')
            run = True
        elif option.total:
            main = walletBalanceReport('total')
            run = True
        elif option.singleCrypto:
            main = cryptoBalanceReport()
            run = True
    elif option.version:
        print(calculateWalletValue.version)
    if run:
        main.run()