from json import load, loads, decoder, dumps
from datetime import datetime, timedelta
from os import environ, path, getcwd, mkdir
from platform import system
from pandas import DataFrame
from numpy import log
from numpy import sqrt

class lib:
    # this color below works only on unixlike shell
    # unsupported OS will use plain text without color
    OKGREEN = '\033[92m'
    WARNING_YELLOW = '\033[93m'
    FAIL_RED = '\033[91m'
    ENDC = '\033[0m'
    WELCOME_BLUE = '\033[94m'
    ASK_USER_INPUT_PURPLE = '\033[95m'

    @staticmethod
    def logConsole(text: str, color: str, end: str):
        if 'TERM_PROGRAM' in environ.keys():
            print(f'{color}{text} {lib.ENDC}', end=end)
        else:
            print(text, end=end)

    @staticmethod
    def printOk(text: str, end = "\n"):
        lib.handlePrint(text, color=lib.OKGREEN, symbol="[+]", end=end)

    @staticmethod
    def printWarn(text: str, end = "\n"):
        lib.handlePrint(text, color=lib.WARNING_YELLOW, symbol="[+]", end=end)

    @staticmethod
    def printFail(text: str, end = "\n"):
        lib.handlePrint(text, color=lib.FAIL_RED, symbol="[-]", end=end)

    @staticmethod
    def printWelcome(text: str, end = "\n"):
        lib.handlePrint(text, color=lib.WELCOME_BLUE, symbol="[*]", end=end, doubleSymbol=True)

    @staticmethod
    def printAskUserInput(text: str, end= "\n"):
        lib.handlePrint(text, color=lib.ASK_USER_INPUT_PURPLE, symbol="[!]", end=end)

    @staticmethod
    def handlePrint(text: str, color: str, symbol: str, end = "\n", doubleSymbol = False):
        temp = lib.formatInput(text)
        for item in temp[0]:
            if lib.ENDC in item:
                item = item.replace(lib.ENDC, lib.ENDC+color)
            lib.logConsole(f'{symbol} {item} {symbol if doubleSymbol else ""}', color=color, end=end)

    @staticmethod
    def formatInput(text: str):
        if "\n" in text:
            text = text.split('\n') 
            return text, True
        return [text], False

    @staticmethod
    def getSettings() -> dict:
        return lib.loadJsonFile('settings.json')

    @staticmethod
    def getConfig() -> dict:
        return lib.loadJsonFile('config.json')

    @staticmethod
    def loadJsonFile(file: str) -> dict:
        with open(file,'r') as f:
            if(f.readable):
                return load(f) # json.load settings in a dict
            else: 
                lib.printFail(f'Error while reading {file}')
                exit()

    @staticmethod
    def getNextDay(day: str, format = '%d/%m/%Y') -> datetime: 
        return lib.parse_formatDate(day, format) + timedelta(days=1)
    
    @staticmethod
    def getNextHour(day: str, format = '%d/%m/%Y') -> datetime: 
        return lib.parse_formatDate(day, format) + timedelta(hours=1)
    
    @staticmethod
    def getPreviousDay(day: str, format = '%d/%m/%Y') -> datetime: 
        return lib.parse_formatDate(day, format) - timedelta(days=1)
    
    @staticmethod
    def getCurrentDay(format = '%d/%m/%Y') -> str:
        return datetime.today().date().strftime(format)
    
    @staticmethod
    def parse_formatDate(day: str, format = '%d/%m/%Y', splitBy = ' ') -> datetime:
        if type(day) == datetime:
            return day
        return datetime.strptime(day.split(splitBy)[0], format)

    @staticmethod
    # given a list of float return avarage volatility
    # be carefull of which number you pass as avg_period
    # avg_period = 1 doesn't have no meaning
    # avg_period > len(total_value) doesn't have no meaning either 
    def calcAvgVolatility(total_value: list, avg_period: int = 30):
        if avg_period == 1 or avg_period > len(total_value): 
            lib.printFail(f"Specify a correct avg_period when calling {lib.calcAvgVolatility.__name__}")
            return None

        dataset = DataFrame(total_value) # pandas DF
        dataset = log(dataset/dataset.shift(1)) # numpy.log()
        dataset.fillna(0, inplace = True)

        # window/avg_period tells us how many days out you want
        # ddof in variance formula is x parameter .../(N - x)
        # ddof = 0 means you CALCULATE variance, any other number means you are ESTIMATE it.
        # you want to estimate it when you don't have all the necessary data to calc it.
        #
        # 365 in np.sqrt(365) is the number of trading day in a year, 
        # specifically in crypto market, trading days = year-round
        volatility = dataset.rolling(window=avg_period).std(ddof=0)*sqrt(365) # numpy.sqrt()

        # avarage volatily
        avg_volatility = volatility.mean(axis=0).get(0)
        
        return avg_volatility

    @staticmethod
    def isValidDate(date: str, format = '%d/%m/%Y'):
        try:
            lib.parse_formatDate(date, format)
        except:
            return False
        return True

    @staticmethod
    def getIndexOfDate(dateToFind: str, list: list):
        found = False
        index = 0
        for (i, item) in enumerate(list):
            if lib.parse_formatDate(item) == lib.parse_formatDate(dateToFind):
                found = True; index = i
                break
        return index, found

    @staticmethod
    def getUserInputDate(listOfDate):
        while True:
            try:
                temp = lib.getUserInput().replace(' ', '')
                if len(temp) == 0:
                    return 'default'
                if lib.isValidDate(temp):
                    index, found = lib.getIndexOfDate(temp, listOfDate)
                    if found == False:
                        raise ValueError
                    return index
                else: raise ValueError
            except ValueError:
                lib.printFail('Invalid date, enter a valid date to continue or press ^C')

    @staticmethod
    def getUserInput() -> str:
        while True:
            try:
                return input()
            except KeyboardInterrupt:
                lib.printWarn('^C detected, aborting...')
                exit()

    @staticmethod
    # read json file, update
    def updateJson(file_path: str, date_to_update: str, new_record: str) -> tuple[bool, str]:
        new_file = ''
        date_to_update = date_to_update.split(':')[0]
        formated_date_to_update = datetime.strptime(date_to_update,  '%d/%m/%Y %H')
        date_file_line = datetime(1970, 1, 1)
        isFirst = True

        with open(file_path, 'r') as f:
            for (_, line) in enumerate(f):
                try:
                    date = loads(line)
                except decoder.JSONDecodeError as e: # sometimes it throw error on line 2
                    lib.printFail(f'Json error, {file_path=} {e}')
                    pass

                # parse date and convert to dd/mm/yyyy
                date_file_line = datetime.strptime(date['date'].split(':')[0], '%d/%m/%Y %H')
                if isFirst: 
                    if formated_date_to_update < date_file_line: 
                        # if date_to_update is before the first line's date
                        # add new_record at the beginning of file_path
                        new_file = new_record + str(open(file_path, 'r').read())
                        isFirst = False
                        break

                if date_file_line == formated_date_to_update:
                    new_file += new_record+'\n' # insert new_record instead of old record(line variable)
                else:
                    new_file += line # add line without modifing it

            if formated_date_to_update > date_file_line:
                # if date_to_update is newer of last file's date 
                # add new record at the end of file
                new_file += new_record+'\n'
            
        with open(file_path, 'w') as f:
            if f.writable: f.write(new_file)
            else: return False, new_file # return new_file to eventually retry later
        return True, ''

    # create /cached_id_CG.json and /cached_id_CMC.json
    # in current working directory (where you run main.py)
    # return a list of full path of created files if succesfully
    # False otherwise
    @staticmethod
    def createCacheFile():
        cwd = getcwd() # current working directory
        joiner = '\\' if system() == 'Windows' else '/'
        cg = cwd+joiner+'cached_id_CG.json'
        cmc = cwd+joiner+'cached_id_CMC.json'

        lib.createFile(cg, dumps({"fixed": [], "used": {}}, indent=4), False)
        lib.createFile(cmc, '{}', False)
        
        return cg, cmc

    # create /grafico , /walletValue.json and /report.json
    # in dirPath passed as argument
    # return a list of full path of created files/dir if succesfully
    # False otherwise
    @staticmethod
    def createWorkingFile(dirPath: str):
        try:
            if not path.isdir(dirPath): mkdir(dirPath) 
        except FileExistsError: pass
        except FileNotFoundError: lib.printFail('Error on init, check path in settings.json'); return False
        
        joiner = '\\' if system() == 'Windows' else '/'
        dirPath = dirPath+joiner
        graficoPath = dirPath+'grafico'
        walletJsonPath = dirPath+'walletValue.json'
        reportJsonPath = dirPath+'report.json'

        try:
            if not path.isdir(graficoPath): mkdir(graficoPath) 
        except FileExistsError: pass
        except FileNotFoundError: lib.printFail('Error on init, check path in settings.json'); return False
        
        lib.createFile(walletJsonPath)
        lib.createFile(reportJsonPath)

        return graficoPath, walletJsonPath, reportJsonPath

    # If filepath do not exist on filesystem, create file and write content
    # If filepath exist on filesystem, 
    #   write content on filepath created if filepath doesn't contain anything or overide == True  
    #       
    @staticmethod
    def createFile(filepath: str, content: str = '', overide: bool = False):
        try:
            if not path.exists(filepath):
                with open(filepath, 'w') as f:
                    f.write(content)
                return
            else:
                f = open(filepath, 'r')
                if len(f.read()) == 0 or overide:
                    f.close()
                    f = open(filepath, 'w')
                    f.write(content)
                return
        except Exception as e:
            lib.printFail(f'Failed to create file: {filepath}')
            lib.printFail(str(e))
            exit()


if __name__ == '__main__':
    pass