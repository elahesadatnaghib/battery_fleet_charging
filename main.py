# python basics
import logging
logging.basicConfig(level=logging.DEBUG)

# repo dependencies
import pandas as pd
pd.set_option('display.max_rows', 300)
pd.set_option('display.max_columns', 300)
#pd.set_option('display.width', 500)

#internal packages
from src import (
    Battery,
    DataPrep
)
# from core.optimization_model import DCMOptimizer
from core import (
    DCMOptimizer,
    OptimizationStrategy
)


if __name__ == '__main__':

    # user defines configurations
    configs = {
        'input_data_path': 'data/load_data.csv',

        # battery config
        'capacity_kwh': 200,
        'max_charge_rate_kw': 100,
        'max_discharge_rate_kw': 100,
        'charge_efficiency_pct': 97,
        'discharge_efficiency_pct': 97,
        'initial_state_of_energy': 0,

        # optimization config
        'optimization_strategy': OptimizationStrategy.OPT1, # OPT1 or  OPT2

        # viewing config
        'print_results': True,
        'save_battery_plan': True,
        'save_file_path': 'data/outputs/battery_plan.csv',
        
    }

    # read data
    logging.info("starting to read data ...")
    gross_load_kw_df = pd.read_csv(configs['input_data_path'])
    logging.info("finished reading data.")

    # create a pydantic instance for timeseries and validation
    input_data_container = DataPrep(
        gross_load_kw_df=gross_load_kw_df
        )
    
    input_data_container.clean_data()

    # create a pydantic instance for battery and validate
    battery = Battery(
            capacity_kwh=configs['capacity_kwh'],
            max_charge_rate_kw=configs['max_charge_rate_kw'],
            max_discharge_rate_kw=configs['max_discharge_rate_kw'],
            charge_efficiency_pct=configs['charge_efficiency_pct'],
            discharge_efficiency_pct=configs['discharge_efficiency_pct'],
            initial_state_of_energy=configs['initial_state_of_energy']
    )

    # instantiate the optimization model
    model = DCMOptimizer(
        input_data=input_data_container,
        battery=battery
        )

    logging.info("starting to optimize ...")
    battery_plan_df = \
        model.optimize(
        time_increaments_minutes= model.get_granularity(),
        optimization_strategy=configs['optimization_strategy']
        )
    logging.info("optimization is done.")

    if configs['save_battery_plan']:
        battery_plan_df.to_csv(configs['save_file_path'])
    if configs['print_results']:

        logging.critical(battery_plan_df.head(10))

        logging.critical(
            f"the time granularity of the results is "
            f"{model.get_granularity()} minutes.")
        
        logging.critical(
            f"the peak load (kwh) by month is "
            f"{model.get_peak_by_month()}.")
        
        logging.critical(
            f"the time reduction percentage by month is "
            f"{model.get_reduction_by_month()}.")
        