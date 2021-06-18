from plotnine import ggplot, aes, geom_line, geom_point, scale_x_continuous, scale_y_continuous,\
    labs, theme, theme_538, annotate, element_text

import numpy as np
import pandas as pd
import statistics
import textwrap
import os


def combine_data(directory, year_pattern):
    """
    Load all files in the provided directory as pandas DataFrames and join data into one large
    DataFrame for future analysis.

    :param directory: Local directory where financial data resides
    :param year_pattern: String indicating which files to pull. Example: '10Y', '5Y', '3Y', etc.
    :return: Master DataFrame containing all data from the listed directory
    :rtype: pandas.DataFrame
    """

    master = pd.DataFrame()

    for file in os.listdir(directory):

        if file.endswith(year_pattern, -7, -4):

            financial_data = pd.read_csv(directory + str(file))

            if master.empty:
                master = financial_data
            else:
                master = pd.merge(master, financial_data, on=['symbol', 'date'], how='inner',
                                  suffixes=('', '_x'))

        elif file == 'company-profiles.csv':

            company_profiles = pd.read_csv(directory + str(file))

            try:
                master = pd.merge(master, company_profiles, on='symbol', how='left',
                                  suffixes=('', '_x'))
            except KeyError:
                continue

    duplicate_cols = [x for x in master if x.endswith('_x')]
    master.drop(duplicate_cols, axis=1, inplace=True)

    return master


def calculate_stats(df, stat, report_year, eval_period, *args):
    """
    Calculate N year statistics for provided columns.

    :param df: DataFrame containing the columns specified in *args
    :param stat: Statistic to calculate: mean, median, or percent change
    :param report_year: Ending year of calculation
    :param eval_period: Number of years to include in the calculation
    :param args: Columns that require calculations
    :return: New DataFrame containing 'symbol', 'year', and 'stat X' columns
    :rtype: pandas.DataFrame
    """

    df.sort_values(by=['symbol', 'year'], inplace=True, ascending=False)

    company_stats = pd.DataFrame()

    for arg in list(args):

        metric = df[['symbol', 'year', arg]]
        metric = metric.pivot_table(values=arg, index='symbol', columns='year')

        if stat == 'percent change':
            column_name = str(eval_period) + 'Y ' + arg + ' % change'
            company_stats[column_name] = (metric.iloc[:, -1] / metric.iloc[:, 0]) - 1

        elif stat == 'mean':
            column_name = str(eval_period) + 'Y ' + arg + ' mean'
            company_stats[column_name] = metric.mean(axis=1)

        elif stat == 'median':
            column_name = str(eval_period) + 'Y ' + arg + ' median'
            company_stats[column_name] = metric.median(axis=1)

    company_stats['year'] = report_year

    return company_stats


def screen_stocks(df, **kwargs):
    """
    Subset DataFrame to stocks containing column values within the specified thresholds.

    :param df: DataFrame containing the columns specified in key values of **kwargs
    :param kwargs: Dictionary containing column names as keys and min/max threshold values
    :return: Subset of the DataFrame provided
    :rtype: pandas.DataFrame
    """

    for column, thresholds in kwargs.items():
        df = df[(df[column] > thresholds[0]) & (df[column] < thresholds[1]) | (df[column].isnull())]

    ticker_list = list(df.symbol)

    return ticker_list


def plot_performance(df, report_year, eval_period):
    """
    Plot metric-specific performance for a set of stocks over time. Reference:
    https://www.buffettsbooks.com/how-to-invest-in-stocks/intermediate-course/lesson-20/

    :param df: DataFrame containing stock tickers and the columns specified below
    :param report_year: Year of most recent financial report
    :param eval_period: Number of years prior to most recent report to be analyzed
    :return: A list of ggplot objects
    :rtype: List
    """

    start_year = report_year - eval_period
    df = df.loc[df['year'] >= start_year]

    df = df[['symbol', 'year', 'eps', 'bookValuePerShare', 'roe', 'currentRatio', 'debtToEquity']]

    df['roe'] = df['roe'].apply(lambda x: x * 100.0)

    df = df.rename({'eps': 'Earnings per Share', 'roe': 'Return on Equity',
                    'currentRatio': 'Current Ratio', 'debtToEquity': 'Debt to Equity Ratio',
                    'bookValuePerShare': 'Book Value per Share'}, axis='columns')

    df.sort_values(by=['symbol', 'year'], inplace=True, ascending=True)
    df.dropna(inplace=True)

    # Commenting out for now, API no longer returning this col in income-statement response
    label_dict = {'Earnings per Share': 'The EPS shows the company\'s profit per share. This chart '
                                        'should have a positive slope over time. Stable results '
                                        'here are extremely important for forecasting future cash '
                                        'flows. Note: if the company\'s book value has increased '
                                        'over time, the EPS should demonstrate similar growth.',

                  # 'Dividend per Share': 'This chart shows the dividend history of the company. '
                  #                       'This should have a flat to positive slope over time. If '
                  #                       'you see a drastic drop, it may represent a stock split '
                  #                       'for the company. Note: the dividend is taken from a '
                  #                       'portion of the EPS, the remainder goes to the book value.',

                  'Book Value per Share': 'The book value represents the liquidation value of the '
                                          'entire company (per share). It\'s important to see '
                                          'this number increasing over time. If the company pays a'
                                          ' high dividend, the book value may grow at a slower '
                                          'rate. If the company pays no dividend, the book value '
                                          'should grow with the EPS each year.',

                  'Return on Equity': 'Return on equity is very important because it show the '
                                      'return that management has received for reinvesting the '
                                      'profits of the company. If using an intrinsic value '
                                      'calculator, it\'s very important that this number is flat or'
                                      ' increasing for accurate results. Find companies with a '
                                      'consistent ROE above 8%.',

                  'Current Ratio': 'The current ratio helps measure the health of the company in '
                                   'the short term. As a rule of thumb, the current ratio should be'
                                   ' above 1.0. A safe current ratio is typically above 1.5. Look '
                                   'for stability trends within the current ratio to see how the '
                                   'company manages their short term risk.',

                  'Debt to Equity Ratio': 'The debt to equity ratio helps measure the health of '
                                          'the company in the long term. As a rule of thumb, the '
                                          'debt to equity ratio should be lower than 0.5. Look for '
                                          'stability trends within the debt/equity ratio to see how'
                                          ' the company manages their long term risk.'}

    wrapper = textwrap.TextWrapper(width=120)

    for key, value in label_dict.items():
        label_dict[key] = wrapper.fill(text=value)

    plots = []

    cols = df.columns[2:].tolist()

    for metric in cols:
        p = (ggplot(df, aes('year', metric, color='symbol'))
             + geom_line(size=1, alpha=0.8) + geom_point(size=3, alpha=0.8)
             + labs(title=metric, x='Report Year', y='', color='Ticker')
             + theme_538() + theme(legend_position='left', plot_title=element_text(weight='bold'))
             + scale_x_continuous(breaks=range(min(df['year']), max(df['year']) + 1, 1))
             + scale_y_continuous(breaks=range(min(df[metric].astype(int)),
                                               max(round(df[metric]).astype(int)) + 2, 1))
             + annotate(geom='label', x=statistics.mean((df['year'])),
                        y=max(round(df[metric]).astype(int) + 1), label=label_dict[metric],
                        size=8, label_padding=0.8, fill='#F7F7F7'))

        plots.append(p)

    return plots


def prepare_valuation_inputs(df, report_year, eval_period, *args):
    """
    Subset DataFrame to data required for Discounted Cash Flow model.

    :param df: Dataframe containing the columns specified below
    :param report_year: Year of most recent financial report
    :param eval_period: Number of years prior to most recent report to be analyzed
    :param args: Stocks to retain for analysis
    :return: Subset of the DataFrame provided
    :rtype: pandas.DataFrame
    """

    symbol_filter = list(args)
    df = df[df['symbol'].isin(symbol_filter)]

    start_year = report_year - eval_period
    df = df.loc[df['year'] >= start_year]

    df['interestRate'] = round((df['interestExpense'] / df['totalDebt']), 2)

    df = df.replace([np.inf, -np.inf, np.nan], 0)

    max_tax_rate = df.groupby('symbol')['effectiveTaxRate'].max().reset_index()
    max_interest_rate = df.groupby('symbol')['interestRate'].max().reset_index()

    df = df[['symbol', 'year', 'freeCashFlow', 'marketCap', 'shortTermDebt', 'longTermDebt',
             'profile.beta', 'cashAndCashEquivalents', 'totalLiabilities', 'numberOfShares',
             'stockPrice']]

    df = df.loc[df['year'] == report_year]

    valuation_data = df.merge(max_tax_rate, on='symbol').merge(max_interest_rate, on='symbol')

    valuation_data.rename(columns={'effectiveTaxRate': 'Max Tax Rate',
                                   'interestRate': 'Max Interest Rate'}, inplace=True)

    valuation_data['Max Tax Rate'] = round(valuation_data['Max Tax Rate'], 2)

    return valuation_data


def calculate_discount_rate(df, risk_free_rate=0.0069, market_risk_premium=0.06):
    """
    Calculate the Weighted Average Cost of Capital (WACC) for each ticker in the provided DataFrame.

    :param df: DataFrame containing a single row of valuation inputs for each stock ticker
    :param risk_free_rate: The minimum rate of return investors expect to earn from an
           investment without risk (use 10-Year Government’s Bond as a Risk Free Rate)
    :param market_risk_premium: The rate of return over the risk free rate required by investors
    :return: Original DataFrame with the addition of a new 'Discount Rate' (WACC) column
    :rtype: pandas.DataFrame
    """

    market_value_equity = df['marketCap']
    market_value_debt = (df['shortTermDebt'] + df['longTermDebt']) * 1.20
    total_market_value_debt_equity = market_value_equity + market_value_debt

    cost_of_debt = df['Max Interest Rate'] * (1 - df['Max Tax Rate'])
    cost_of_equity = risk_free_rate + df['profile.beta'] * market_risk_premium

    df['Discount Rate'] = round((market_value_equity / total_market_value_debt_equity) * cost_of_equity \
                                + (market_value_debt / total_market_value_debt_equity) * cost_of_debt, 2)

    return df


def calculate_discounted_free_cash_flow(df, projection_window, **kwargs):
    """
    Calculate the present value of discounted future cash flows for each stock ticker in the
    provided Dataframe.

    :param df: DataFrame containing a single row of valuation inputs for each stock ticker
    :param projection_window: Number of years into the future we should generate projections for
    :param kwargs: Dictionary containing stock tickers as keys and long term growth rate
           estimates as values
    :return: Original DataFrame with the addition of new columns: 'Present Value of Discounted
    FCF', 'Last Projected FCF', 'Last Projected Discount Factor'
    :rtype: pandas.DataFrame
    """

    estimated_growth = pd.DataFrame(kwargs.items(), columns=['symbol', 'Long Term Growth Rate'])
    df = df.merge(estimated_growth, on='symbol')

    dfcf = pd.DataFrame(columns=['year', 'symbol', 'Last Projected FCF',
                                 'Last Projected Discount Factor',
                                 'Present Value of Discounted FCF'])

    for row in df.itertuples(index=False):

        for year in range(projection_window + 1):
            projected_free_cash_flow = row[df.columns.get_loc('freeCashFlow')] * \
                                       (1 + row[df.columns.get_loc('Long Term Growth Rate')]) ** \
                                       year

            discount_factor = 1 / (1 + row[df.columns.get_loc('Discount Rate')]) ** year

            discounted_free_cash_flow = projected_free_cash_flow * discount_factor

            dfcf = dfcf.append({'year': year, 'symbol': row[df.columns.get_loc('symbol')],
                                'Last Projected FCF': round(projected_free_cash_flow, 2),
                                'Last Projected Discount Factor': round(discount_factor, 2),
                                'Present Value of Discounted FCF': round(discounted_free_cash_flow, 2)},
                               ignore_index=True)

    dfcf = dfcf.loc[dfcf['year'] != 0]

    pv_dfcf = dfcf.groupby('symbol')['Present Value of Discounted FCF'].sum().reset_index()
    last_fcf = dfcf.loc[dfcf['year'] == max(dfcf['year'])][['symbol', 'Last Projected FCF']]
    last_df = dfcf.loc[dfcf['year'] == max(dfcf['year'])][['symbol', 'Last Projected Discount '
                                                                     'Factor']]

    df = df.merge(pv_dfcf, on='symbol').merge(last_fcf, on='symbol').merge(last_df, on='symbol')

    return df


def calculate_terminal_value(df, gdp_growth_rate=0.029):
    """
    Calculate the terminal value for each stock ticker in the provided DataFrame.

    :param df: DataFrame containing a single row of valuation inputs for each stock ticker
    :param gdp_growth_rate: https://data.worldbank.org/indicator/NY.GDP.MKTP.KD.ZG?locations=US
    :return: Original DataFrame with the addition of a new 'Terminal Value' column
    :rtype: pandas.DataFrame
    """

    df['Terminal Value'] = (df['Last Projected FCF'] * (1 + gdp_growth_rate)) \
                           / df['Discount Rate'] - gdp_growth_rate

    return df


def calculate_intrinsic_value(df):
    """
    Calculate the intrinsic value of each stock ticker in the provided DataFrame.

    :param df: DataFrame containing a single row of valuation inputs for each stock ticker
    :return: Original DataFrame with the addition of a new 'Intrinsic Value' column
    :rtype: pandas.DataFrame
    """

    df['Intrinsic Value'] = (df['Present Value of Discounted FCF'] + df['Terminal Value']
                             + df['cashAndCashEquivalents'] - df['totalLiabilities']) \
                            / df['numberOfShares']

    return df


def calculate_margin_of_safety(df, margin_of_safety=0.25):
    """
    Calculate the margin of safety value of each stock ticker in the provided DataFrame.

    :param df: DataFrame containing a single row of valuation inputs for each stock ticker
    :param margin_of_safety: Value by which to discount our original intrinsic value calculation
    :return: Original DataFrame with the addition of new columns: 'Margin of Safety Value', 'Buy'
    :rtype: pandas.DataFrame
    """

    multiplier = 1 - margin_of_safety
    df['Margin of Safety Value'] = df['Intrinsic Value'] * multiplier

    df['Buy Decision'] = np.where(df['Margin of Safety Value'] > df['stockPrice'], 'Yes', 'No')

    return df
