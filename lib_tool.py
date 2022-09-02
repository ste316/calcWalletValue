from json import load

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
        with open('settings.json','r') as f:
            if(f.readable):
                return load(f) # load settings in a dict
            else: 
                lib.printFail('Error on reading settings')
                exit()
