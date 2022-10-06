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
'''
r= requests.get("https://financialmodelingprep.com/api/v3/historical-price-full/{}?apikey={}".format('AAPL'))
quotes =  pd.DataFrame.from_dict(r.json())
quotes["date"] = quotes["historical"].map(lambda x: x['date'])
quotes["quote"] = quotes["historical"].map(lambda x: x["adjClose"])
'''


style="border: 1px solid #999;"

app_ui = ui.page_fluid(
    ui.row(
        ui.column(12, ui.h3("Value investing Shiny App"), style=style)),
    ui.row(
        ui.column(4, 
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
            ui.input_text(
                "quarter", 
                "Quarters", 
                placeholder = "Quarters"
            ),
            ui.input_action_button(
                "boton",
                "Update Analysis"
                , class_="btn-primary w-100"
                ),
            ui.output_text("compute")), style=style),
        ui.column(8, ui.output_plot("historical_quotes"), style=style),
    ),
    ui.row(
        ui.column(6,ui.output_plot("margen_operativo_plot"), style=style),
        ui.column(6,ui.output_plot("deuda_plot"), style=style),
    ),
    ui.row(
        ui.column(6,ui.output_plot("ganancia_retenida_plot"), style=style),
        ui.column(6,ui.output_plot("eva_plot"), style=style),
    ),
    ui.row(
        ui.column(6,ui.output_plot("bancarrota_plot"), style=style),
        ui.column(6,ui.output_plot("beneish_plot"), style=style)
    ),
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
        quotes_df = quotes_df[(quotes_df['date'] > '2013-01-01') & (quotes_df['date'] < today)]

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
        income_analysis["margen_neto"]= financial_ratios["netProfitMargin"]
        income_analysis["investigacion_desarrollo"] = income_statement["researchAndDevelopmentExpenses"] / income_statement["operatingIncome"]
        income_analysis["tasa_impositiva"] = np.where(income_statement["incomeBeforeTax"] >= 0,(income_statement["incomeTaxExpense"] / income_statement["incomeBeforeTax"]), -(income_statement["incomeTaxExpense"] / income_statement["incomeBeforeTax"]))
        income_analysis["intereses/EBIT"] = income_statement["interestExpense"] / income_statement["operatingIncome"]
        income_analysis["Consistencia_EPS"] = income_statement["epsdiluted"]
        ### Crecimiento de ventas
        # working with datetime...
        income_analysis['date_int'] = pd.to_datetime(income_analysis['date']).dt.strftime('%Y%m%d').astype(int)
        sales_growth_slope = np.polyfit(income_analysis["date_int"],income_analysis["crecimiento_ventas"], 1)
        slope = sales_growth_slope[0]
        sales_growth= pow(10, slope - 1)
        sales_growth_target = np.where(sales_growth > 0, 1,0)
        ### Margen Bruto
        margen_bruto = mean(income_analysis["margen_bruto"])
        margen_bruto_target = np.where(margen_bruto >= 0.40, 1, 0)
        ### Margen Operativo
        margen_operativo_slope = np.polyfit(income_analysis["date_int"],income_analysis["margen_operativo"], 1)[0]
        margen_operativo_target = np.where(margen_operativo_slope > 0, 1, 0)
        ### Margen Neto
        margen_neto = mean(income_analysis["margen_neto"])
        margen_neto_target = np.where(margen_neto >= 0.20, 1, 0)
        ### Investigación y desarrollo
        investigacion_desarrollo = mean(income_analysis["investigacion_desarrollo"])
        investigacion_desarrollo_target = np.where(investigacion_desarrollo < 0.33, 1, 0) 
        ### intereses/EBIT
        intereses_EBIT = mean(income_analysis["intereses/EBIT"])
        intereses_EBIT_target = np.where(intereses_EBIT < 0.15, 1, 0)
        ### Consistencia_EPS
        consistencia_EPS_slope = np.polyfit(income_analysis["date_int"],income_analysis["Consistencia_EPS"], 1)[0]
        consistencia_EPS_min = min(income_analysis["Consistencia_EPS"])
        consistencia_EPS_target = np.where(consistencia_EPS_slope >= 0 and consistencia_EPS_min >= 0, 1, 0)
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
        balance_analysis["rotacion_inventarios"] = income_statement["revenue"] / balance_sheet["inventory"]
        balance_analysis["rotacion_inventarios"] = balance_analysis["rotacion_inventarios"].replace([np.inf, -np.inf], 0)
        balance_analysis["rotacion_inventarios"] = balance_analysis["rotacion_inventarios"].fillna(0)
        balance_analysis["exceso_de_caja"] = np.where(balance_sheet["cashAndShortTermInvestments"]>income_statement["revenue"]*0.05,balance_sheet["cashAndShortTermInvestments"] - income_statement["revenue"]*0.05,0 )
        balance_analysis["rotacion_working_capital"] = income_statement["revenue"] / (balance_sheet["totalCurrentAssets"] - balance_analysis["exceso_de_caja"] - balance_sheet["accountPayables"])
        balance_analysis["rotacion_working_capital"] = balance_analysis["rotacion_working_capital"].replace([np.inf, -np.inf], 0)
        balance_analysis["rotacion_working_capital"] = balance_analysis["rotacion_working_capital"].fillna(0)
        balance_analysis["rotacion_planta_equipos"] = income_statement["revenue"] / balance_sheet["propertyPlantEquipmentNet"]
        balance_analysis["rotacion_planta_equipos"] = balance_analysis["rotacion_planta_equipos"].replace([np.inf, -np.inf], 0)
        balance_analysis["rotacion_planta_equipos"] = balance_analysis["rotacion_planta_equipos"].fillna(0)
        balance_analysis["rotacion_activo_total"] = financial_ratios["assetTurnover"]
        balance_analysis["rotacion_activo_total"] = balance_analysis["rotacion_activo_total"].replace([np.inf, -np.inf], 0)
        balance_analysis["rotacion_activo_total"] = balance_analysis["rotacion_activo_total"].fillna(0)
        balance_analysis["rotacion_capital_total"] = income_statement["revenue"] / (balance_sheet["totalAssets"] - (balance_sheet["longTermInvestments"] + balance_sheet["goodwillAndIntangibleAssets"] + balance_sheet["accountPayables"]))
        balance_analysis["net-net"] = key_metrics["netCurrentAssetValue"]
        ### Liquidez Corriente
        liquidez_corriente_final = balance_analysis["Liquidez_Corriente"].iloc[0]
        liquidez_corriente_target = np.where(liquidez_corriente_final >= 1, 1, 0)
        ### Endeudamiento D/E
        ratio_endeudamiento_final = balance_analysis["Ratio_Endeudamiento"].iloc[0]
        ratio_endeudamiento_target = np.where(ratio_endeudamiento_final <= 0.5, 1, 0)
        ### PasivoLP/Ganancia_neta
        pasivoLP_ganancia_neta_final = balance_analysis["PasivoLP/Ganancia_neta"].iloc[0]
        pasivoLP_ganancia_neta_target = np.where(pasivoLP_ganancia_neta_final <= 5, 1, 0)
        ### Creci_gan_retenida
        creci_gan_retenida_growth_slope = np.polyfit(income_analysis["date_int"],balance_analysis["Creci_gan_retenida"], 1)[0]
        creci_gan_retenida_growth= pow(10, creci_gan_retenida_growth_slope - 1)
        creci_gan_retenida_growth_target = np.where(creci_gan_retenida_growth > 0, 1,0)
        ### Rotacion de Inventarios
        rotacion_inventarios_slope = np.polyfit(income_analysis["date_int"],balance_analysis["rotacion_inventarios"], 1)[0]
        rotacion_inventarios_growth_target = np.where(rotacion_inventarios_slope > 0, 1,0)
        ### Rotacion de Working Capital
        rotacion_working_capital_slope = np.polyfit(income_analysis["date_int"],balance_analysis["rotacion_working_capital"], 1)[0]
        rotacion_working_capital_growth_target = np.where(rotacion_working_capital_slope > 0, 1,0)
        ### Rotacion planta y equipos
        rotacion_planta_equipos_slope = np.polyfit(income_analysis["date_int"],balance_analysis["rotacion_planta_equipos"], 1)[0]
        rotacion_planta_equipos_growth_target = np.where(rotacion_planta_equipos_slope > 0, 1,0)
        ### Rotacion del activo total
        rotacion_activo_total_slope = np.polyfit(income_analysis["date_int"],balance_analysis["rotacion_activo_total"], 1)[0]
        rotacion_activo_total_growth_target = np.where(rotacion_activo_total_slope > 0, 1,0)
        ### Net/Net
        net_net_final = balance_analysis["net-net"].iloc[0]
        net_net_target = np.where(net_net_final >0, 1, 0)
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
        return_analysis["PV_FCFF"] = return_analysis["Facor_Capitalizacion"] * return_analysis["FCFF"]
        ### ROIC
        roic_average = mean(return_analysis["ROIC"])
        roic_target = np.where(roic_average > 0.15, 1, 0)
        ### EVA
        eva_average = mean(return_analysis["PV_EVA"])
        eva_target = np.where(eva_average > 0, 1, 0)
        ### FCFF
        fcff_average = mean(return_analysis["PV_FCFF"].iloc[1:-1])
        fcff_target = np.where(fcff_average > 0, 1, 0)
        ### EVA/Revenue
        eva_revenue_average = mean(return_analysis["EVA/Revenue"])
        eva_revenue_target = np.where(eva_revenue_average >= 0.05, 1, 0)
        ########################################################################
        #### Analisis del cashflow
        ########################################################################
        cash_flow_analysis = pd.DataFrame(cash_flow_statement, columns=["symbol", "date", "period"])
        cash_flow_analysis["Bajas_adquisiciones"] = (cash_flow_statement["acquisitionsNet"] / income_statement["operatingIncome"]) 
        cash_flow_analysis["Bajo_CAPEX"] = (cash_flow_statement["capitalExpenditure"] / income_statement["operatingIncome"]) 
        cash_flow_analysis["Recompra_acciones"] = cash_flow_statement["commonStockRepurchased"]
        cash_flow_analysis["Baja_depresiacion"] = (cash_flow_statement["depreciationAndAmortization"] / income_statement["grossProfit"]) 
        cash_flow_analysis["OperationgCF/Operating_income"] = (cash_flow_statement["operatingCashFlow"] / income_statement["operatingIncome"]) 
        ### Bajas adquisiciones
        adquisiciones_average = mean(cash_flow_analysis["Bajas_adquisiciones"])
        adquisiciones_target = np.where(adquisiciones_average <= 0.3333, 1, 0)
        ### CAPEX
        CAPEX_average = mean(cash_flow_analysis["Bajo_CAPEX"])
        CAPEX_target = np.where(CAPEX_average <= 0.3333, 1, 0)
        ### Recompra de acciones
        recompra_acciones = sum(cash_flow_analysis["Recompra_acciones"])
        recompra_acciones_target = np.where(recompra_acciones < 0, 1, 0)
        ### Baja depresiacion
        depresiacion_acciones_average = mean(cash_flow_analysis["Baja_depresiacion"])
        depresiacion_acciones_target = np.where(depresiacion_acciones_average <= 7, 1, 0)
        ### Operating CF/Operating Income
        operatingCF_operatingIncome_average = mean(cash_flow_analysis["OperationgCF/Operating_income"])
        operatingCF_operatingIncome_target = np.where(operatingCF_operatingIncome_average >= 50, 1, 0)
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
        ### Bancarrota Altman Z-Score
        bancarrota_last = np.where(bancarrota_analysis["Altman_z-Score"] > 2.99, "Green zone", 
                                             np.where(bancarrota_analysis["Altman_z-Score"].between(1.81, 2.99, inclusive = True), "Grey Zone",  
                                             np.where(bancarrota_analysis["Altman_z-Score"] < 1.81, "Distress Zone", "None")))[0]
        bancarrota_target = np.where(bancarrota_last == "Green zone", 1, 0)
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
        ### Beneish Score contabilidad creativa
        beneish_last = np.where(beneish_analysis["beneish_resulta"].iloc[0] == "OK Test", 1, 0)
        ##################################################################################
        # Analisis Global de los principales indicadores
        suma_de_KPIS = sales_growth_target + margen_bruto_target  + margen_operativo_target   + margen_neto_target + investigacion_desarrollo_target + intereses_EBIT_target + consistencia_EPS_target + liquidez_corriente_target + ratio_endeudamiento_target \
         + pasivoLP_ganancia_neta_target + creci_gan_retenida_growth_target  + rotacion_inventarios_growth_target + rotacion_working_capital_growth_target + rotacion_planta_equipos_growth_target \
         + rotacion_activo_total_growth_target  + net_net_target + roic_target + eva_target + fcff_target+ eva_revenue_target+ adquisiciones_target+ CAPEX_target  + recompra_acciones_target \
         + depresiacion_acciones_target  + operatingCF_operatingIncome_target + bancarrota_target + beneish_last   
        suma_de_principales_KPIS = margen_operativo_target + ratio_endeudamiento_target + creci_gan_retenida_growth_target +  eva_target + bancarrota_target + beneish_last 

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
        ax.set_title(f"{input.ticker()} - Margen Operativo history")
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
        ax.set_title(f"{input.ticker()} - Ratio de Endeudamiento history")
        
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
        ax.set_title(f"{input.ticker()} - Crecimiento de ganancia retenida history")
        
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
        ax.set_title(f"{input.ticker()} - Beneish M-Score history")
        
        return fig
        
     #Table logic
    @output
    @render.table()
    def table_data():
        return income()
    


app = App(app_ui, server)