from urllib.request import urlopen

import json
import pandas as pd


def get_company_data(api_key):
    """
    Retrieve all available company stocks from FinancialModelingPrep API.

    :param api_key: FinancialModelingPrep API key
    :return: DataFrame containing 'symbol', 'name', 'price', and 'exchange' columns
    :rtype: pandas.DataFrame
    """
    print('Retrieving stock data from FinancialModelingPrep...')

    response = urlopen("https://financialmodelingprep.com/api/v3/stock/list?apikey=" + api_key)
    data = response.read().decode("utf-8")
    data_json = json.loads(data)
    flattened_data = pd.json_normalize(data_json)

    print('Found stock data on ' + str(flattened_data.symbol.nunique()) + ' companies! \n')

    return flattened_data


def select_stock_exchanges(df):
    """
    Subset DataFrame to companies listed on major stock exchanges.

    :param df: DataFrame containing stock exchange info on N companies
    :return: Subset of the DataFrame provided
    :rtype: pandas.DataFrame
    """
    print('Searching for stocks listed on major stock exchanges among ' + str(df.symbol.nunique()) +
          ' companies...')

    major_stock_exchanges = ['Nasdaq Global Select', 'NasdaqGS', 'Nasdaq',
                             'New York Stock Exchange', 'NYSE', 'NYSE American']

    df = df[df['exchange'].isin(major_stock_exchanges)]

    print('Found ' + str(df.symbol.nunique()) + ' companies listed on major stock exchanges! \n')

    return df


def select_minimum_price(df, min_price=5.00):
    """
    Subset DataFrame to companies with a stock price greater than or equal to the minimum provided.

    :param df: DataFrame containing recent stock price info on N companies
    :param min_price: The minimum stock price a user is willing to consider
    :return: Subset of the DataFrame provided
    :rtype: pandas.DataFrame
    """
    print('Searching for stocks with a price greater than or equal to $' + str(int(min_price)) +
          ' among ' + str(df.symbol.nunique()) + ' companies')

    df = df[df['price'] >= min_price]

    print('Found ' + str(df.symbol.nunique()) + ' companies that meet your price requirement! \n')

    return df


def create_company_profile(df, dir_path, api_key):
    """
    Map stock tickers to company information needed for screening stocks (industry, sector, etc.).

    :param df: DataFrame containing stock tickers (symbol) for N companies
    :param dir_path: Specifies name of directory that csv files should be written to
    :param api_key: FinancialModelingPrep API key
    :return: New DataFrame that maps the symbol column to additional company information
    :rtype: pandas.DataFrame
    """

    print('Searching for profile data on ' + str(df.symbol.nunique()) + ' companies...')

    profile_data = pd.DataFrame()

    for ticker in df['symbol']:
        response = urlopen("https://financialmodelingprep.com/api/v3/company/profile/" + ticker
                           + "?apikey=" + api_key)

        data = response.read().decode("utf-8")
        data_json = json.loads(data)
        flattened_data = pd.json_normalize(data_json)
        profile_data = pd.concat([profile_data, flattened_data], ignore_index=True)

    profile_data.to_csv(dir_path + 'company-profiles.csv', index=False, header=True)

    print('Found ' + str(profile_data.symbol.nunique()) + ' company profiles! \n')

    return profile_data
