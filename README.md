# Calculate Wallet Value is a program to instantly see how your cryptocurrency portfolio is performing.

1. ## Prerequisites:
    * [Download a python interpreter](https://www.python.org/downloads/), suggested python version >= 3.9
    * Download all dependencies
      * move to the folder of the project
      * run: `pip install -r requirements.txt`
    * Insert all your assets and their amount in input.csv
    * Fill settings.json with your preferences
        * currency supported: "EUR" and "USD", needs to be uppercase 
            * other currencies may be supported, have not been tested
        * <span style="color:red">NOTE: the first time you run the program make sure to fill fetchSymb with true</span>
        * provider can be "cg" for CoinGecko or "cmc" for CoinMarketCap
        * You can choose between CoinGecko and CoinMarketCap api
            * CoinGecko api is free and you do NOT need any api key, see [plan](https://www.coingecko.com/en/api/pricing) and
            [limits](https://www.coingecko.com/en/api/documentation)
            * [FASTER] CoinMarketCap it's free too, but you need to [sign in](https://pro.coinmarketcap.com/login/) and get an api key

            #### CoinMarketCap is lightning faster and easy to use, but you have less privacy.
            #### CoinGecko is slower and a bit more complicated to use, but you don't have to create any account or fill your information anywhere, yet more privacy.
            #### Both solutions are supported, make your choice.

2. ## Usage:
    * ### Preliminary step:
        * `cd <folderOfProject>`

    * ### You can run this command to:
        * <span style="color:red">NOTE: both command execute the same code, the only difference is the graphical output. So you will get your wallet data saved in your walletValue.json file anyway.</span>

        * #### instantly see your CRYPTO wallet:
            * `python main.py --calc --crypto`
            * you may want to obscure total value showed in the graphic, run `python main.py --calc --crypto --privacy` 
            * you may want to see your portfolio in a past date(must have been calculated on that date), run `python main.py --calc --crypto --load`
        ![crypto](https://github.com/ste316/calcWalletValue/blob/main/img/crypto.png)

        * #### instantly see your wallet splitted in CRYPTO and FIAT:
            * `--calc --total`
            * you may want to obscure total value showed in the graphic, run `python main.py --calc --crypto --privacy` 
            * you may want to see your portfolio in a past date(must have been calculated on that date), run `python main.py --calc --crypto --load`
        ![total](https://github.com/ste316/calcWalletValue/blob/main/img/total.png)

    * ### You can analyse your portfolio over time, using these commands:
        * <span style="color:red">NOTE: to run all this commands you need at least 2 records in walletValue.json</span>

        * #### Show your crypto wallet over time
            * `python main.py --report --crypto`
            * include stablecoins
        * #### Show your total wallet over time
            * `python main.py --report --total`
            * include all assets
        * #### Show fiat value and amout of an asset over time
            * `python main.py --report --singleCrypto`
