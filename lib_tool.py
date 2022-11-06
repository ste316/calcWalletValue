from json import load
from datetime import datetime, timedelta

class lib:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    WELCOME_BLUE = '\033[94m'

    @staticmethod
    def logConsole(text: str, color: str):
        print(f'{color}{text} {lib.ENDC}')

    @staticmethod
    def printOk(text: str):
        lib.logConsole(f'[+] {text}', lib.OKGREEN)

    @staticmethod
    def printWarn(text: str):
        lib.logConsole(f'[+] {text}', lib.WARNING)

    @staticmethod
    def printFail(text: str):
        lib.logConsole(f'[-] {text}', lib.FAIL)

    @staticmethod
    def printWelcome(text: str):
        lib.logConsole(f'[*] {text} [*]', lib.WELCOME_BLUE)

    @staticmethod
    def getSettings() -> dict:
        return lib.loadJsonFile('settings.json')

    @staticmethod
    def loadJsonFile(file: str) -> dict:
        with open(file,'r') as f:
            if(f.readable):
                return load(f) # json.load settings in a dict
            else: 
                lib.printFail('Error on reading settings')
                exit()

    @staticmethod
    def getNextDay(day: str) -> datetime: 
        return lib.parse_formatDate(day) + timedelta(days=1)
    
    @staticmethod
    def parse_formatDate(day: str) -> datetime:
        if type(day) == datetime:
            return day
        return datetime.strptime(day.split(' ')[0], '%d/%m/%Y')