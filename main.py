from api import cg_api, yahooGetPriceOf
from lib_tool import lib
import json
from pandas import read_csv
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from numpy import array
import argparse
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
        self.supportedStablecoin = ['usdt', 'usdc']
        self.load = load # option to load data from json, see genPltFromJson()
        lib.printWelcome(f'Welcome to Calculate Wallet Value!')
        lib.printWarn(f'Currency: {self.settings["currency"]}')

        # read price provider specified in settings.json
        if self.settings['api_provider']['provider'] == 'cg':
            lib.printWarn('Api Provider: CoinGecko')
            self.provider = 'cg'
            self.cg = cg_api(self.settings['currency'])

            # fetch all crypto symbol and name from CoinGecko
            # run once or if there is any new crypto that is needed
            if self.settings['api_provider']['cgFetchSymb'] == True: 
                self.cg.fetchID()
                lib.printOk('Coin list successfully fetched and saved')
        else:
            lib.printFail("Specify a correct price provider")
            exit

        # if path is not specified in settings.json
        if not len(self.settings['path'] ) > 0:
            basePath = f'{os.environ["USERPROFILE"]}\\Desktop\\crypto' # default path
        else: basePath = self.settings['path']

        # set type of grafic visualization and json file
        # N.B. <type> is passed in arguments when you execute the script
        # if type == 'crypto' or type == 'total': 
        if type in ['crypto', 'total']: 
            self.type = type
            lib.printWarn(f'Report type: {self.type} wallet')
        else:
            lib.printFail('Unexpected error, pass the correct argument, run again with option --help')
            exit

        if os.path.isdir(basePath):
            # create the needed folder and json file
            try:
                os.mkdir(basePath)
            except FileExistsError:
                pass
            except FileNotFoundError:
                lib.printFail('Error on init, check path in settings.json')
                exit()
            
            try:
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
            if self.type == 'total': # set total wallet is reported in a different json file
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

    # retrieve price of a crypto vs currency
    def getPriceOf(self, symbol) -> float: 
        if self.provider == 'cg': # coingecko
            if symbol.upper() == self.settings['currency']: # if symbol is the currency
                return 1

            price = self.cg.getPriceOf(symbol) # retrieve price
            if price == False: # if api wasn't able to retrieve price it return false
                self.invalid_sym.append(symbol)
                lib.printFail(f'Error getting price of {symbol}-{self.settings["currency"]}')
                return False
            return price
        
        # in case where there isn't a correct provider (should not happen)
        lib.printFail('Unexpected error, provider error')
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
            # _addy is refering to a certain address of a certain crypto (future use)
            try:
                qta = float(qta) # convert str to float
            except ValueError:
                lib.printFail(f'Error parsing value of {symbol}')
                continue
            
            # if input.csv contain a symbol multiple time
            if symbol in list(data.keys()): 
                data[symbol] += qta
            else:
                data[symbol] = qta
        return data

    # calculate the value of crypto and format data to be used in handleDataPlt()
    def calcValue(self, crypto: dict) -> dict:
        data = list()
        tot = 0.0

        lib.printWarn('Retriving current price...')
        for (symbol, qta) in crypto.items():

            # since input.csv file serves both crypto and total
            # when you calc crypto you DO NOT want eur or usd included
            if self.type == 'crypto' and symbol.lower() in self.supportedCurrency: 
                continue
            
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
    #   if value of a certain crypto is <= 5%
    #   add special symbol OTHER and sum all crypto whose value is <= 5%
    # 
    # for total:
    #   there are only 2 symbols: crypto and fiat
    #   crypto value is the total sum of cryptos
    #   fiat value is the total sum of fiat converted in self.settings['currency']
    def handleDataPlt(self, dict: dict) -> dict:
        newdict = {
            'total': dict['total'],
            'currency': dict['currency'],
            'symbol': [], # symbolo[0] = [symbol, value]
            'date': dict['date']
        }

        lib.printWarn('Preparing data...')
        if self.type.lower() == 'crypto':

            for (symb, _, value) in dict['symbol']:
                if symb in ['other', 'EUR', 'USD']: continue

                # group together all elements in the dictionary whose value is less than 5%
                if value / dict['total'] <= 0.05:
                    if newdict['symbol'][0][0] != 'other': 
                        # create 'other' only once
                        newdict['symbol'] = [['other', 0.0], *newdict['symbol']] # add 'other' as first element

                    newdict['symbol'][0][1] += value # increment value of symbol 'other'
                    # symbolo[0] = [symbol, value]

                else:
                    newdict['symbol'].append([symb, value]) # add symbol to PLT if its value is greater than 5%

            return newdict

        elif self.type.lower() == 'total':
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
        sns.color_palette('pastel')
        # define size of the image
        plt.figure(figsize=(6, 5), tight_layout=True)
        # create a pie chart with value in xx.x% format
        plt.pie(y, labels = mylabels, autopct='%1.1f%%', startangle=90, shadow=False)
        # add legend and title to pie chart
        plt.legend(title = "Symbols:") 
        plt.title(f'{self.type.capitalize()} Balance: {dict["total"]} {dict["currency"]} | {dict["date"]}', fontsize=13, weight='bold')

        # format filename using current date
        filename = dict['date'].replace("/",'_').replace(':','_').replace(' ',' T')+'.png'

        if not self.load: 
            # when you specify --loadJson you already have json data in walletValue/walletGeneralOverview and image saved
            # so only if --loadJson isn't specified save img and json file
            plt.savefig(f'{self.settings["grafico_path"]}\\{filename}') #save image
            lib.printOk(f'Pie chart image successfully saved in {self.settings["grafico_path"]}\{filename}')
            self.updateWL(rawcrypto, filename) # update walletValue.json

        plt.show() 

    # write data to self.settings['json_path']
    def updateWL(self, crypto: dict, filename: str):
        new_file = ''
        temp = json.dumps({
            'date': crypto['date'],
            'total_value': crypto['total'],
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

                if new_date != file_date: # if file dates aren't equal to today date
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
        
        for (i, r) in enumerate(record):
            print(f"[{i}] {r['date']}", end='\n')
        
        lib.printWarn('Type one number...')
        gotIndex = False

        while not gotIndex:
            try:
                index = int(input())
                gotIndex = True
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
        self.genPlt(newdict)

    # main 
    def calculateValue(self) -> dict: 
        if self.load:
            self.genPltFromJson(self.settings['json_path'])
        else:
            rawCrypto = self.loadCSV()
            rawCrypto = self.checkInput(rawCrypto)
            rawCrypto = self.calcValue(rawCrypto)
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
            exit
        lib.printWarn(f'Currency: {self.settings["currency"]}')
        lib.printWarn(f'Report type: {self.type} wallet')

    # parse and format data to create PLT
    def genPlt(self):
        data = {
            'date': [],
            'total_value': [],
            'currency': self.settings['currency']
        }

        # load all DATETIME 
        right_index = set()
        lib.printWarn(f'Loading value from {self.settings["json_path"]}...')
        with open(self.settings['json_path'], 'r') as f:
            for (i, line) in enumerate(f):
                try:
                    line = json.loads(line)
                except json.decoder.JSONDecodeError:
                    lib.printFail(f'Errore decoding {self.settings["json_path"]} line: {i+1}, empty line or invalid json')
                    continue
                temp_date = line['date'].split(' ')[0] # parse date format: dd/mm/yyyy
                if temp_date not in data['date']: # add date once
                    data['date'].append(temp_date)
                    right_index.add(i)

        # convert all value to the currency specified in settings.json value
        lib.printWarn('Validating data...')
        with open(self.settings['json_path'], 'r') as f:
            for (i, line) in enumerate(f):
                if i in right_index:
                    line = json.loads(line)
                    total_value = line['total_value']
                    # if currency of json line is different from settings.json currency
                    if line['currency'] != self.settings['currency']: 

                        if line['currency'] == 'USD' and self.settings["currency"] == 'EUR':
                            # get forex rate using yahoo api
                            rate = yahooGetPriceOf(f'{self.settings["currency"]}{line["currency"]}=X', '', True)
                        elif line['currency'] == 'EUR' and self.settings["currency"] == 'USD':
                            rate = yahooGetPriceOf(f'{line["currency"]}{self.settings["currency"]}=X', '', True)
                        else:
                            lib.printFail('Currency not supported')
                            exit()
                        
                        total_value /= rate # convert value using current forex rate
                    
                    # add total_value to have total value over time
                    data['total_value'].append(total_value)

        # create line chart
        lib.printWarn(f'Creating chart...')
        # set back ground [white, dark, whitegrid, darkgrid, ticks]
        sns.set_style('darkgrid') 
        # define size of the image
        plt.figure(figsize=(7, 6), tight_layout=True)
        plt.plot(data['date'], data['total_value'], color='red', marker='o')
        plt.title(f'{self.type.capitalize()} Balance from {data["date"][0]} to {data["date"][-1]} \nCurrency: {self.settings["currency"]}', fontsize=14, weight='bold') # add title
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
    option = parser.parse_args()
    if (not option.calcV and not option.report) or (not option.crypto and not option.total):
        parser.error("[-] Specify value or report and crypto or total balance")
    return option

if __name__ == '__main__':
    option = get_args()

    if (option.report or option.calcV or option.load) and (option.crypto or option.total):
        if option.report:
            if option.crypto:
                main = walletBalanceReport('crypto')
            elif option.total:
                main = walletBalanceReport('total')
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
