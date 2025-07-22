
# python basics
from dataclasses import dataclass, field
from enum import Enum, auto
from enum import Enum
from typing import Dict, List
import logging
logging.basicConfig(level=logging.DEBUG)


# repo dependencies
import pandas as pd
import numpy as np

# internal packages
from src import OptimizationStrategy

@dataclass
class Optimizers():
    strategy: OptimizationStrategy
    gross_load_kw_df: pd.DataFrame
    data_timezone: pd.DatetimeTZDtype
    battery_spec_dict: Dict[str, float]
    time_increaments_minutes: float

    def __post_init__(self):
        pass

    def solve(self) -> pd.DataFrame:
        if self.strategy == OptimizationStrategy.OPT1:
            return \
            self.top_bottom_smoothing_optimization()
        if self.strategy == OptimizationStrategy.OPT2:
            return \
            self.some_other_optimization()
        
    def top_bottom_smoothing_optimization(self) -> pd.DataFrame:
        """
        In the interest of time I am going to make some simplifying
        assumptions (it's gross, I hate it too :D)
        First I assume that every day the battery starts 
        with full soc and cycles once and ends the day with zero
        full. In the worst case the solution is infeasible for 
        the first day of the operations if soc is not full.
        This restriction smoothes peaks on a daily basis. (which 
        also smoothes the peak on the peakiest day of the month.)
        This is not too restrictive in the real world, because usually a 
        large battery cannot be economically justified to smooth on a 
        monthly level. If we had a large battery,
        then we could accumulate a whole lot of charge day after day for 
        the "doomsday" of the month to have a super smoothing discharge. 
        Even when the battery is large, 
        the stored energy disipates over time, which is also not economical.
        In most cases, we need to settle with daily smoothing anyways.

        Second assumption, to make sure I schedule discharge 
        only if the soc is positive, I require the battery to discharge
        before noon and then charge after noon.

        Third assumption, there is no lower or upper limit on the net load

        Returns:
            a dataframe containing the battery schedule.
        """
        minutes_to_fully_charge = \
            (
            self.battery_spec_dict['capacity_kwh']
            /
            # additional charge to account for the losses:
            (self.battery_spec_dict['charge_efficiency_pct']/100)
            /
            self.battery_spec_dict['max_charge_rate_kw']
            ) * 60 # hour to minutes
        
        minutes_to_fully_discharge = \
            (
            self.battery_spec_dict['capacity_kwh']
            *
            # reduced discharge to account for the losses
            self.battery_spec_dict['discharge_efficiency_pct']/100
            /
            self.battery_spec_dict['max_discharge_rate_kw']
            ) * 60 # hour to minutes
        
        cnt_blocks_of_time_to_charge = \
            minutes_to_fully_charge / self.time_increaments_minutes
        
        cnt_blocks_of_time_to_discharge = \
            minutes_to_fully_discharge / self.time_increaments_minutes

        # now I choose the blocks of time based on the gross load.
        # I choose the n highest loads of the hours before noon
        # to charge (n = cnt_blocks_of_time_to_charge)
        # and m lowest loads of the hours after noon
        # to discharge (m = cnt_blocks_of_time_to_discharge)

        # to schedule the battery for a day, date needs to be localized
        self.gross_load_kw_df.loc[:, 'date'] = \
            self.gross_load_kw_df.loc[:, 'datetime'].dt.\
                tz_convert(self.data_timezone).dt.date

        self.gross_load_kw_df.loc[:, 'hour_local'] = \
            self.gross_load_kw_df.loc[:, 'datetime'].dt.\
                tz_convert(self.data_timezone).dt.hour
        
        after_noon_loads_df = \
            self.gross_load_kw_df[
                self.gross_load_kw_df.loc[:, 'hour_local'] >= 13
                ].copy() # we had to convert the datetime to local timezone to identify "noon"
        morning_loads_df = \
            self.gross_load_kw_df[
                self.gross_load_kw_df.loc[:, 'hour_local'] < 13
                ].copy()
        

        after_noon_loads_df.loc[:, 'rank'] = \
            after_noon_loads_df.groupby('date')['actual_kwh']\
                .rank(ascending=False, method='first')
        
        morning_loads_df.loc[:, 'rank'] = \
            morning_loads_df.groupby('date')['actual_kwh']\
                .rank(ascending=True, method='first')
        
        charge_df = \
            after_noon_loads_df.loc[after_noon_loads_df.loc[:, 'rank'] 
                             <= np.ceil(cnt_blocks_of_time_to_charge)]\
                                .copy()
        discharge_df = \
            morning_loads_df.loc[morning_loads_df.loc[:, 'rank'] 
                               <= np.ceil(cnt_blocks_of_time_to_discharge)]\
                                .copy()
        
        charge_df.loc[:, 'charge_kw'] = \
            -self.battery_spec_dict['max_charge_rate_kw']
        discharge_df.loc[:, 'discharge_kw'] = \
            self.battery_spec_dict['max_discharge_rate_kw']

        # overwrite the last ranked time periods to account for fractional amount of
        # periods that implies that we do not require full charge over the full period
        reduced_charge_rate = \
            np.ceil(cnt_blocks_of_time_to_charge) - cnt_blocks_of_time_to_charge
        charge_df.loc[:, 'charge_kw'] = \
            charge_df.apply(
            lambda x: x['charge_kw'] * reduced_charge_rate
            if x['rank'] == np.ceil(cnt_blocks_of_time_to_charge) 
            else x['charge_kw'], axis=1)
        
        reduced_discharge_rate = \
            np.ceil(cnt_blocks_of_time_to_discharge) - cnt_blocks_of_time_to_discharge
        discharge_df.loc[:, 'discharge_kw'] = \
            discharge_df.apply(
            lambda x: x['discharge_kw'] * reduced_discharge_rate
            if x['rank'] == np.ceil(cnt_blocks_of_time_to_discharge) 
            else x['discharge_kw'], axis=1)
        
        # add energy columns
        charge_df.loc[:, 'charge_kwh'] = \
            charge_df.loc[:, 'charge_kw'] * \
            self.time_increaments_minutes / 60
        discharge_df.loc[:, 'discharge_kwh'] = \
            discharge_df.loc[:, 'discharge_kw'] * \
            self.time_increaments_minutes / 60

        battery_plan = \
            pd.concat([charge_df, discharge_df]).sort_values(by='datetime')
        
        # cosmetic changes:
        battery_plan = battery_plan.fillna(0)\
            .drop(columns=['rank', 'date', 'time_utc'])
        battery_plan.rename(columns={'datetime': 'datetime_utc'}, inplace=True)
        
        return battery_plan

    def some_other_optimization(self) -> pd.DataFrame:
        
        return NotImplementedError
    

        
