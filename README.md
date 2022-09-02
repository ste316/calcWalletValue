1. Prerequisites:
    * To get all dependencies run: pip install -r requirements.txt
    * Insert all assets in input.csv, you don't need to add any address, it's for future implementation
    * Fill settings.json with you preference
    * Note: the first time you run the program make sure to fill cgFetchSymb with true

    * CoinGecko api is free and you do NOT need any key, see [plan](https://www.coingecko.com/en/api/pricing) and
    [limits](https://www.coingecko.com/en/api/documentation)

2. Usage:
    * Calculate and see value of your crypto portfolio:
        * main.py --calc --crypto
    
    * Calculate and see value of your total portfolio(crypto+fiat):
        * main.py --calc --total
    
    * See value of your crypto portfolio in a spefic date:
        * main.py --calc --crypto --loadJson
        * NOTE: this function load data from walletValue.json
    
    * See value of your total portfolio in a spefic date:
        * main.py --calc --total --loadJson
        * NOTE: this function load data from walletGeneralOverview.json
    
    * See your crypto portfolio's value over time:
        * main.py --report --crypto
        * NOTE: this function load data from walletValue.json

    * See your crypto portfolio's value over time:
        * main.py --report --total
        * NOTE: this function load data from walletGeneralOverview.json

3. Examples

    ![crypto](https://github.com/ste316/calcWalletValue/blob/main/img/crypto.png)

    ![total](https://github.com/ste316/calcWalletValue/blob/main/img/total.png)

4. Donate
    * bitcoin: bc1q5fwga56vz79aa0rn9ha5q6xhvyrn2ugvhq57xx
    * ethereum: 0xD73AaC29901c1d89743466440759ab848b0DF6A2
    * solana: 8QDY6YkAyL4ybT8eQYczigFFGsXgbmJg6VX2ahut5Bbg
    * cosmos: cosmos13df86alvf7ppmjvt9wkdpc3pnwgk9eqfke7nla
