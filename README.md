1. Prerequisites:
    * Download all dependencies
      * move to the folder of the project
      * run: `pip install -r requirements.txt`
    * Insert all assets in input.csv
    * Fill settings.json with your preferences
        * currency supported: "EUR" and "USD", needs to be uppercase 
        * provider can be "cg" for CoinGecko or "cmc" for CoinMarketCap
        * Note: the first time you run the program make sure to fill fetchSymb with true
        * You can choose between CoinGecko and CoinMarketCap api
            * CoinGecko api is free and you do NOT need any key, see [plan](https://www.coingecko.com/en/api/pricing) and
            [limits](https://www.coingecko.com/en/api/documentation)
            * [FASTER] CoinMarketCap it's free too and you need to [sign in](https://pro.coinmarketcap.com/login/) and get an api key

            CoinGecko is slower but you don't have to create any account or fill your information anywhere, yet more privacy

2. Usage:
    There are 2 main group of command, to produce data and to analyse data

    * To produce data:
        * Calculate your wallet value, show crypto portfolio, without fiat
            * `--calc --crypto`
            * you may want to obscure total value showed in the graphic, add `--privacy`
            * you may want to see your portfolio in a past date(needs to be calculated in that date), add `--load`
        ![crypto](https://github.com/ste316/calcWalletValue/blob/main/img/crypto.png)

        * Calculate your wallet value, show crypto vs fiat value
            * `--calc --total`
            * you may want to obscure total value showed in the graphic, add `--privacy`
            * you may want to see your portfolio in a past date(needs to be calculated in that date), add `--load`
        ![total](https://github.com/ste316/calcWalletValue/blob/main/img/total.png)

    * To analyse data
        * Show your crypto wallet(including stablecoins) over time
            * `--report --crypto`
        * Show your total wallet over time
            * `--report --total`
        * Show fiat value and amout of a selected crypto over time
            * `--report --singleCrypto`
