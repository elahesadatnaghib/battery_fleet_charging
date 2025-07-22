# python basics
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List
import logging
logging.basicConfig(level=logging.DEBUG)

# repo dependencies
import pandas as pd
import numpy as np

# internal packages
from src import (
    DataPrep,
    Battery,
    OptimizationStrategy
    )
from .optimizers import Optimizers

@dataclass
class DCMOptimizer():
    # contains all the required data for this algorithm
    input_data: DataPrep
    battery: Battery

    # is extracted from input_data and set in post_init function
    gross_load_kw_df: pd.DataFrame = field(init=False)
    # is extracted from battery and set in post_init function
    battery_spec_dict: Dict[str, float] = field(init=False)
    initial_state_of_charge: float = field(init=False)

    # intermediate objects
    optimizer: Optimizers = field(init=False)
    # calculated values
    battery_plan_df: pd.DataFrame = field(init=False)


    def __post_init__(self):

        self.set_load_data()
        self.input_data.evaluate_granularity()
        self.set_battery_specs()
        self.set_initial_state_of_energy()

    def set_load_data(self) -> None:
        """
        extracts the timeseries from input_data. The data
        is already validated and cleaned in the DataPrep
        pydantic class whcih input_data is an instance of
        """
        self.gross_load_kw_df = \
            self.input_data.gross_load_kw_df
        
    def set_battery_specs(self) -> None:
        """
        user specified battery specifications are set and 
        validated via Battery class. This function calls another
        function of the class that extracts the data and massages
        them into dictionary as required by the instructions.
        """
        self.battery_spec_dict = \
            self.convert_battery_spec_to_dict()
        
    def set_initial_state_of_energy(self, **kwargs):
        """
        If this function is called with a state of energy,
        Then it sets that value, otherwise it uses the value that
        we specified when we created the battery object in main.py via
        user configurations.

        Raises:
            ValueError: If the keyword is not valid
        """
        if len(kwargs):
            for key in kwargs:
                if key not in {'initial_state_of_charge'}:
                    raise ValueError(f"Invalid argument: {key}")
            
            soc_value_kw = kwargs['initial_state_of_charge']
            assert 0 <= soc_value_kw <= self.battery.capacity_kwh, \
            "invalid state of charge"
            self.battery_spec_dict['initial_state_of_charge'] = \
                kwargs['initial_state_of_charge']
        
        
    def optimize(self, 
                 time_increaments_minutes: float, 
                 optimization_strategy: OptimizationStrategy) -> float:
        """
        creates an instance of the optimizer object using user-configurations
        such as the optimization method name. Then trigers the requested algorithm 
        to solve the problem with the input data.

        Args:
            optimization_strategy: user specified optimization sgtrategy

        Returns:
            a timeseries to optimally schedule the battery
        """
        assert optimization_strategy in OptimizationStrategy, \
            "the requested optimization strategy does not exist"
        
        # create an instance of optimizer, only when
        # the optimize() is triggered. 
        self.optimizer = Optimizers(
            strategy=optimization_strategy,
            gross_load_kw_df=self.gross_load_kw_df,
            data_timezone=self.input_data.data_timezone,
            battery_spec_dict=self.battery_spec_dict,
            time_increaments_minutes=time_increaments_minutes
        )
        # trigger the requested optimizer
        if optimization_strategy == OptimizationStrategy.OPT1:
            self.battery_plan_df = \
                self.optimizer.top_bottom_smoothing_optimization()
        elif optimization_strategy == OptimizationStrategy.OPT2:
            self.battery_plan_df = \
                self.optimizer.some_other_optimization()
        
        # massage battery plan and add net load
        self.battery_plan_df = self.calculate_net_load()
        return self.battery_plan_df
    
    def get_battery_plan(self) -> Dict[str, float]:
        """
        if the user has ran the optimize() function it returns 
        the battery plan, otherwise errors out and asks the user to 
        run optimize()

        Returns:
            a dataframe with timestamps, battery plan and netload
        """
        assert len(self.battery_plan_df), \
            "the battery plan is not calculated yet, run optimize()"

        return self.battery_plan_df
    
    def get_peak_by_month(self) -> Dict[str, float]:
        """
        Groups by month only. Note that when the data
        has multiple years worth of entries, then
        for example the January statistics would include
        the data of januaries of all years in one pot

        Returns:
            peak load of the month as dictionary
        """

        peak_by_month_df =  self.battery_plan_df.copy()
        # calculate month from datetime
        peak_by_month_df.loc[:, 'month'] = \
            peak_by_month_df.loc[:, 'datetime'].dt.month
        
        # group
        peak_by_month_df = \
        peak_by_month_df.groupby('month').agg(
            netload_max_kwh = ('net_load_kwh', 'max'),
        )
        
        # to dict
        peak_by_month_dict = \
        peak_by_month_df['netload_max_kwh'].round(1).to_dict()

        # cosmetic: change month number to month date
        return \
            {pd.to_datetime(f'2021-{k}-01').strftime('%B'): v 
             for k, v in peak_by_month_dict.items()}

    
    def get_reduction_by_month(self) -> Dict[str, float]:
        """
        Groups by month only. Note that when the data
        has multiple years worth of entries, then
        for example the January statistics would include
        the data of januaries of all years in one pot

        Returns:
            reduction of the month in dictionary
        """
        reduction_by_month_df =  self.battery_plan_df.copy()
        # calculate month from datetime
        reduction_by_month_df.loc[:, 'month'] = \
            reduction_by_month_df.loc[:, 'datetime'].dt.month
        
        # group 
        reduction_by_month_df = \
        reduction_by_month_df.groupby('month').agg(
            gross_load_max_kwh = ('actual_kwh', 'max'),
            netload_max_kwh = ('net_load_kwh', 'max'),
        )
        # calculate percentage
        reduction_by_month_df.loc[:, 'peak_reduction_pct'] = (
        reduction_by_month_df.loc[:, 'gross_load_max_kwh'] -
        reduction_by_month_df.loc[:, 'netload_max_kwh']) / \
        reduction_by_month_df.loc[:, 'gross_load_max_kwh'] * \
        100 # fraction to pct
        
        # to dictionary
        reduction_by_month_dict = \
        reduction_by_month_df['peak_reduction_pct'].round(1).to_dict()

        # cosmetic: change month number to month date
        return \
            {pd.to_datetime(f'2021-{k}-01').strftime('%B'): v 
             for k, v in reduction_by_month_dict.items()}
    
    
    def get_granularity(self) -> float:
        """
        The granularity is calculated at the stage of the
        data cleanup. It basically calculates the most common
        data increament in the original data, and uses that throughout
        the calculations

        Returns:
            float, in minutes
        """
        
        return self.input_data.time_increaments_minutes
    
    def convert_battery_spec_to_dict(self) -> Dict[str, float]:
        battery_spec_dict = {}
        battery_spec_dict['capacity_kwh'] = \
            self.battery.capacity_kwh
        battery_spec_dict['max_charge_rate_kw'] = \
            self.battery.max_charge_rate_kw
        battery_spec_dict['max_discharge_rate_kw'] = \
            self.battery.max_discharge_rate_kw
        battery_spec_dict['charge_efficiency_pct'] = \
            self.battery.charge_efficiency_pct
        battery_spec_dict['discharge_efficiency_pct'] = \
            self.battery.discharge_efficiency_pct
        battery_spec_dict['initial_state_of_energy'] = \
            self.battery.initial_state_of_energy
        
        return battery_spec_dict
    
    def calculate_net_load(self):
        assert len(self.battery_plan_df), \
            "the battery plan is not calculated yet, run optimize()"
        
        joined_data_with_battery_plan_df = \
            self.input_data.gross_load_kw_df.merge(
            self.battery_plan_df[[
                'datetime_utc', 'charge_kwh', 'discharge_kwh'
                ]],
            left_on='datetime', #also utc when we read it via pd.read_csv()
            right_on='datetime_utc',
            how='left'
            ).fillna(0)\
                [['datetime', 'hour_local', 
                  'actual_kwh', 'charge_kwh', 'discharge_kwh']]
        
        joined_data_with_battery_plan_df.loc[:, 'net_load_kwh'] = \
        joined_data_with_battery_plan_df.loc[:, 'actual_kwh'] + \
        joined_data_with_battery_plan_df.loc[:, 'charge_kwh']  + \
        joined_data_with_battery_plan_df.loc[:, 'discharge_kwh']
        
        return joined_data_with_battery_plan_df




