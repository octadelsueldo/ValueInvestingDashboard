from binascii import Incomplete
from shiny import App, reactive, render, ui
import yfinance as yf
# import warnings filter
from warnings import simplefilter
# ignore all future warnings
simplefilter(action='ignore', category=FutureWarning)
simplefilter(action='ignore', category=RuntimeWarning)
simplefilter(action='ignore', category=UserWarning)
from cmath import log
import json
from statistics import mean
import pandas as pd
pd.options.mode.chained_assignment = None  # default='warn'
import numpy as np
from statistics import mean
from scipy.stats import linregress
import datetime as dt
from datetime import datetime
from datetime import timedelta
from functools import reduce
from matplotlib import dates as mpl_dates
import matplotlib.pyplot as plt
from asyncio import sleep
import time
import requests 
try:
    # For Python 3.0 and later
        from urllib.request import urlopen
except ImportError:
# Fall back to Python 2's urllib2
    from urllib3 import urlopen 


app_ui = ui.page_fluid(
    ui.h2("Value Investing Shiny App"),
    ui.layout_sidebar(
        ui.panel_sidebar(
            ui.input_text(
                "api_key", 
                "FMP API key:", 
                placeholder = "FMP API key"
            ),
            ui.input_text(
                "ticker", 
                "Select stock:", 
                placeholder = "Ticker"
            ),
            ui.input_radio_buttons(
                id="quarter",
                label="Quarters:",
                choices=["16", "32", "40"],
                selected="40"
            ),
            ui.input_action_button(
                "boton",
                "Update Analysis"
                , class_="btn-primary w-100"
                ),
            ui.output_text("compute")),
        ui.panel_main(            
            ui.row(ui.output_plot("historical_quotes")),
            ui.row(
                ui.column(6,ui.output_plot("margen_operativo_plot")),
                ui.column(6,ui.output_plot("deuda_plot")),
            ),
            ui.row(
                ui.column(6,ui.output_plot("ganancia_retenida_plot")),
                ui.column(6,ui.output_plot("eva_plot")),
            ),
            ui.row(
                ui.column(6,ui.output_plot("bancarrota_plot")),
                ui.column(6,ui.output_plot("beneish_plot"))
            )),
    )
)


def server(input, output, session):
    # Stores all the values the user has submitted so far
    income = reactive.Value([])
    balance = reactive.Value([])
    return_anal = reactive.Value([])
    bancarrota = reactive.Value([])
    beneish = reactive.Value([])
    quotes = reactive.Value([])
    
    mean_EVA = reactive.Value([])

    @output
    @render.text
    @reactive.event(input.boton)
    async def compute():
        with ui.Progress(min=1, max=25) as p:
            p.set(message="Calculation in progress", detail="This may take a while...")

            for i in range(1, 25):
                p.set(i, message="Computing")
                await sleep(0.1)

        return "Done computing!"

    @reactive.Effect
    @reactive.event(input.boton)
    def add_value_to_dataframe():
        print(input.ticker())
        tickers = input.ticker() 

        r= requests.get("https://financialmodelingprep.com/api/v3/historical-price-full/{}?apikey={}".format(tickers, input.api_key()))
        quotes_prices =  pd.DataFrame.from_dict(r.json())
        r = requests.get("https://financialmodelingprep.com/api/v3/income-statement/{}?period=quarter&limit={}&apikey={}".format(tickers, input.quarter(), input.api_key()))
        income_statement =  pd.DataFrame.from_dict(r.json()) 
        r = requests.get("https://financialmodelingprep.com/api/v3/balance-sheet-statement/{}?period=quarter&limit={}&apikey={}".format(tickers, input.quarter(), input.api_key()))
        balance_sheet =  pd.DataFrame.from_dict(r.json()) 
        r = requests.get("https://financialmodelingprep.com/api/v3/cash-flow-statement/{}?period=quarter&limit={}&apikey={}".format(tickers, input.quarter(), input.api_key()))
        cash_flow_statement =  pd.DataFrame.from_dict(r.json()) 
        r = requests.get("https://financialmodelingprep.com/api/v3/ratios/{}?period=quarter&limit={}&apikey={}".format(tickers, input.quarter(), input.api_key()))
        financial_ratios =  pd.DataFrame.from_dict(r.json()) 
        r = requests.get("https://financialmodelingprep.com/api/v3/enterprise-values/{}?period=quarter&limit={}&apikey={}".format(tickers, input.quarter(), input.api_key()))
        enterprise_values =  pd.DataFrame.from_dict(r.json()) 
        r= requests.get("https://financialmodelingprep.com/api/v3/key-metrics/{}?period=quarter&limit={}&apikey={}".format(tickers, input.quarter(), input.api_key()))
        key_metrics =  pd.DataFrame.from_dict(r.json())
        #### Limpieza y normalizacion de los dataframes
        ###############################################################
        quotes_df = pd.DataFrame(quotes_prices, columns=["symbol", "historical"])
        quotes_df["date"] = quotes_prices["historical"].map(lambda x: x['date'])
        quotes_df["quote"] = quotes_prices["historical"].map(lambda x: x["adjClose"])
        quotes_df = quotes_df.sort_values(by="date")
        today = datetime.today()
        today = today.strftime("%Y-%m-%d")
        quotes_df = quotes_df[(quotes_df['date'] > '2022-09-01') & (quotes_df['date'] < today)]

        balance_sheet['date'] = pd.to_datetime(balance_sheet['date'], errors='coerce')
        income_statement['date'] = pd.to_datetime(income_statement['date'], errors='coerce')
        cash_flow_statement['date'] = pd.to_datetime(cash_flow_statement['date'], errors='coerce')
        financial_ratios['date'] = pd.to_datetime(financial_ratios['date'], errors='coerce')
        enterprise_values['date'] = pd.to_datetime(enterprise_values['date'], errors='coerce')
        key_metrics['date'] = pd.to_datetime(key_metrics['date'], errors='coerce')
        # compile the list of dataframes you want to merge
        data_frames = [balance_sheet, income_statement, cash_flow_statement, financial_ratios, enterprise_values, key_metrics]
        df_merged = reduce(lambda  left,right: pd.merge(left,right,on=['date'],
                                                how='inner', suffixes=('', '_drop')), data_frames)
        #Drop the duplicate columns
        df_merged.drop([col for col in df_merged.columns if 'drop' in col], axis=1, inplace=True)
        df_merged.fillna(0, inplace=True)

        balance_sheet = df_merged[balance_sheet.columns]
        income_statement = df_merged[income_statement.columns]
        cash_flow_statement = df_merged[cash_flow_statement.columns]
        financial_ratios = df_merged[financial_ratios.columns]
        enterprise_values = df_merged[enterprise_values.columns]
        key_metrics = df_merged[key_metrics.columns]

        ########################################################################
        ##### Analisis del income statement
        ########################################################################
        income_analysis = pd.DataFrame(income_statement, columns=["symbol", "date", "period"])
        income_analysis["crecimiento_ventas"] = np.log(income_statement["revenue"])
        income_analysis["crecimiento_ventas"] = income_analysis["crecimiento_ventas"].replace([np.inf, -np.inf], 0)
        income_analysis["crecimiento_ventas"] = income_analysis["crecimiento_ventas"].fillna(0)
        income_analysis["margen_bruto"] = financial_ratios["grossProfitMargin"]
        income_analysis["margen_operativo"] = financial_ratios["operatingProfitMargin"]
        
        ########################################################################
        #### Analisis del balance sheet
        ########################################################################
        balance_analysis = pd.DataFrame(balance_sheet, columns=["symbol", "date", "period"])
        balance_analysis["Liquidez_Corriente"] = financial_ratios["currentRatio"]
        balance_analysis["Ratio_Endeudamiento"] = financial_ratios["debtEquityRatio"]
        balance_analysis["PasivoLP/Ganancia_neta"] = balance_sheet["totalNonCurrentLiabilities"] / mean(income_statement["netIncome"])
        balance_analysis["Creci_gan_retenida"] = np.log(balance_sheet["retainedEarnings"])
        balance_analysis["Creci_gan_retenida"] = balance_analysis["Creci_gan_retenida"].replace([np.inf, -np.inf], 0)
        balance_analysis["Creci_gan_retenida"] = balance_analysis["Creci_gan_retenida"].fillna(0)
        
        ########################################################################
        #### Analisis de la rentabilidad
        ########################################################################
        return_analysis = pd.DataFrame(balance_sheet, columns=["symbol", "date", "period", "totalAssets", "cashAndShortTermInvestments", "longTermInvestments", "goodwillAndIntangibleAssets", "accountPayables"])
        return_analysis["Capital"] = balance_sheet["totalAssets"] - (balance_analysis["exceso_de_caja"] + balance_sheet["longTermInvestments"] + balance_sheet["goodwillAndIntangibleAssets"] + balance_sheet["accountPayables"]) 
        return_analysis["Inversion_neta"] = return_analysis["Capital"].shift(1) - return_analysis["Capital"]
        return_analysis["NOPAT"] = income_statement["operatingIncome"] * (1 - (income_statement["incomeTaxExpense"] / income_statement["incomeBeforeTax"]))
        return_analysis["ROIC"] = (return_analysis["NOPAT"] / return_analysis["Capital"]) 
        return_analysis["EVA"] = return_analysis["Capital"] * (return_analysis["ROIC"] - 0.15)
        return_analysis["FCFF"] = return_analysis["NOPAT"] - return_analysis["Inversion_neta"]
        return_analysis["EVA/Revenue"] = return_analysis["EVA"] / income_statement["revenue"]
        return_analysis["Facor_Capitalizacion"] = (1 + 0.15/4) ** return_analysis.index
        return_analysis["PV_EVA"] = return_analysis["Facor_Capitalizacion"] * return_analysis["EVA"]
        
        ########################################################################
        #### Analisis de bancarrota
        ########################################################################
        bancarrota_analysis = pd.DataFrame(key_metrics, columns=["symbol", "date", "period"])
        bancarrota_analysis["WD/Total_Assets"] = key_metrics["workingCapital"] / balance_sheet["totalAssets"]
        bancarrota_analysis["Retained_Earnings/Total_Assets"] = balance_sheet["retainedEarnings"] / balance_sheet["totalAssets"]
        bancarrota_analysis["EBIT/Total_Assets"] = income_statement["operatingIncome"] / balance_sheet["totalAssets"]
        bancarrota_analysis["Market_Cap/Total_Liabilities"] = key_metrics["marketCap"] / balance_sheet["totalLiabilities"]
        bancarrota_analysis["Ventas/Total_Assets"] = financial_ratios["assetTurnover"]
        bancarrota_analysis["Altman_z-Score"] = 1.2 * bancarrota_analysis["WD/Total_Assets"] + 1.4 * bancarrota_analysis["Retained_Earnings/Total_Assets"] + 3.3 * bancarrota_analysis["EBIT/Total_Assets"] + 0.6 * bancarrota_analysis["Market_Cap/Total_Liabilities"] + 1*bancarrota_analysis["Ventas/Total_Assets"]
        bancarrota_analysis["Altman_results"] = np.where(bancarrota_analysis["Altman_z-Score"] > 2.99, "Green zone", 
                                             np.where(bancarrota_analysis["Altman_z-Score"].between(1.81, 2.99, inclusive = True), "Grey Zone",  
                                             np.where(bancarrota_analysis["Altman_z-Score"] < 1.81, "Distress Zone", "None")))
        
        ########################################################################
        #### Analisis de Beneish (Contabilidad Creativa)
        ########################################################################
        beneish_analysis = pd.DataFrame(balance_sheet, columns = ["symbol", "date", "period"])
        beneish_analysis["totalAssets_current_asset_PPE"] = balance_sheet["totalAssets"] - (balance_sheet["totalCurrentAssets"] + balance_sheet["propertyPlantEquipmentNet"])
        beneish_analysis["DaysSalesReceibablesIndex"] = (balance_sheet["netReceivables"].shift(1) / income_statement["revenue"].shift(1)) / (balance_sheet["netReceivables"] / income_statement["revenue"])
        beneish_analysis["GrossMarginIndex"] = (income_statement["grossProfit"].shift(1) / income_statement["revenue"].shift(1)) / (income_statement["grossProfit"] / income_statement["revenue"])
        beneish_analysis["AssetQualityIndex"] = ((beneish_analysis["totalAssets_current_asset_PPE"]).shift(1) / balance_sheet["totalAssets"].shift(1)) / (balance_sheet["totalAssets"] - (balance_sheet["totalCurrentAssets"] + balance_sheet["propertyPlantEquipmentNet"]) / balance_sheet["totalAssets"])
        beneish_analysis["SalesGrowthIndex"] = income_statement["revenue"].shift(1) / income_statement["revenue"]
        beneish_analysis["DepreciationIndex"] = (cash_flow_statement["depreciationAndAmortization"].shift(1) / balance_sheet["propertyPlantEquipmentNet"].shift(1)) / (cash_flow_statement["depreciationAndAmortization"] / balance_sheet["propertyPlantEquipmentNet"])
        beneish_analysis["beneish_m_score"] = -6.065+(0.823* beneish_analysis["DaysSalesReceibablesIndex"]) + (0.906*beneish_analysis["GrossMarginIndex"]) + (0.593*beneish_analysis["AssetQualityIndex"]) + (0.717*beneish_analysis["SalesGrowthIndex"]) + (0.107*beneish_analysis["DepreciationIndex"])
        beneish_analysis["beneish_resulta"] = np.where(beneish_analysis["beneish_m_score"] < -2.22, "OK Test", "Manipulator")
       
        ##################################################################################
    

        ##actualizamos el dataset
        income.set(income_analysis)
        balance.set(balance_analysis)
        return_anal.set(return_analysis)
        bancarrota.set(bancarrota_analysis)
        beneish.set(beneish_analysis)
        quotes.set(quotes_df)
        
        return income() , balance(), return_anal(), bancarrota(), beneish(), quotes()
        

    # Chart logic
    @output
    @render.plot(alt="Stock price")
    @reactive.event(input.boton)
    def historical_quotes():
        # Take a reactive dependency on the action button...
        input.boton()
        fig, ax = plt.subplots()
        x = quotes()["date"]
        y = quotes()["quote"]
        plt.plot(x,y) 
        plt.xticks(rotation=45)
        ax.set_title(f"{input.ticker()} - Stock price over time")
        return fig

    # Chart logic
    @output
    @render.plot(alt="Stock price over time")
    @reactive.event(input.boton)
    def margen_operativo_plot():
        # Take a reactive dependency on the action button...
        input.boton()
        xp = np.arange(income()['date'].size)
        fit = np.polyfit(xp,income()["margen_operativo"], deg=1)
        #Fit function : y = mx + c [linear regression ]
        fit_function = np.poly1d(fit)
        fig, ax = plt.subplots()
        x = income()["date"]
        y = income()["margen_operativo"]
        #Linear regression plot
        plt.plot(x, fit_function(xp))
        plt.plot(x,y)
        plt.xticks(rotation=45) 
        ax.set_title(f"{input.ticker()} - Operative Margin")
        return fig

    # Chart logic
    @output
    @render.plot(alt="Stock price over time")
    @reactive.event(input.boton)
    def deuda_plot():
        # Take a reactive dependency on the action button...
        input.boton()
        fig, ax = plt.subplots()
        x = balance()["date"]
        y = balance()["Ratio_Endeudamiento"]  
        plt.plot(x,y)
        plt.xticks(rotation=45)
        ax.set_title(f"{input.ticker()} - Debt rate")
        
        return fig

    # Chart logic
    @output
    @render.plot(alt="Stock price over time")
    @reactive.event(input.boton)
    def ganancia_retenida_plot():
        # Take a reactive dependency on the action button...
        input.boton()
        fig, ax = plt.subplots()
        x = balance()["date"]
        y = balance()["Creci_gan_retenida"] 
        plt.plot(x,y)
        plt.xticks(rotation=45)
        ax.set_title(f"{input.ticker()} - Growth of retaining Earnings")
        
        return fig


    # Chart logic
    @output
    @render.plot(alt="Stock price over time")
    @reactive.event(input.boton)
    def eva_plot():
        # Take a reactive dependency on the action button...
        input.boton()
        fig, ax = plt.subplots()
        x = return_anal()["date"]
        y = return_anal()["PV_EVA"] 
        plt.plot(x,y)
        plt.xticks(rotation=45)
        ax.set_title(f"{input.ticker()} - EVA history")
        
        return fig
        
    # Chart logic
    @output
    @render.plot(alt="Stock price over time")
    @reactive.event(input.boton)
    def bancarrota_plot():
        # Take a reactive dependency on the action button...
        input.boton()
        fig, ax = plt.subplots()
        x = bancarrota()["date"]
        y = bancarrota()["Altman_z-Score"] 
        plt.plot(x,y)
        plt.xticks(rotation=45)
        ax.set_title(f"{input.ticker()} - Altman Z-Score history")
        
        return fig

    # Chart logic
    @output
    @render.plot(alt="Stock price over time")
    @reactive.event(input.boton)
    def beneish_plot():
        # Take a reactive dependency on the action button...
        input.boton()
        fig, ax = plt.subplots()
        x = beneish()["date"]
        y = beneish()["beneish_m_score"] 
        plt.plot(x,y)
        plt.xticks(rotation=45)
        ax.set_title(f"{input.ticker()} - Beneish M-Score history")
        
        return fig
        
     #Table logic
    @output
    @render.table()
    def table_data():
        return income()
    


app = App(app_ui, server)