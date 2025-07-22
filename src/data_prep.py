# python basics
from pydantic import BaseModel, validator, ValidationError
from typing import Dict, List
import logging
logging.basicConfig(level=logging.DEBUG)

# repo dependencies
import pandas as pd
import numpy as np



class DataPrep(BaseModel):
    """
    imports and validates data
    """
    gross_load_kw_df: pd.DataFrame
    time_increaments_minutes: float = 5.0
    data_timezone: pd.DatetimeTZDtype = \
        pd.DatetimeTZDtype(tz='UTC')

    # @validator('gross_load_kw_df')
    # def time_increaments_should_be_even(cls, value):
    #     time_increaments = value['date'].dt.diff().dropna()
    #     if time_increaments.nunique() >= 1:
    #         raise ValidationError(
    #             "the time increaments of the timeseries are uneven")
    #     return value
    
    @validator('gross_load_kw_df')
    def all_required_columns_should_exist(cls, value):
        if not {'datetime', 'actual_kwh'}.issubset(set(value.columns)):
            raise ValidationError(
                "all the required columns should be available")
        return value

    def clean_data(self) -> None:

        # remember data timezone
        self.data_timezone = \
        pd.Timestamp(self.gross_load_kw_df.loc[0, 'datetime']).tzinfo
        # convert timestamps to datetime at utc
        self.gross_load_kw_df['datetime'] = \
            pd.to_datetime(self.gross_load_kw_df['datetime'], utc=True)
        
        # add additional columns that help with the cleaning
        self.gross_load_kw_df['time_utc'] = \
            self.gross_load_kw_df['datetime'].dt.time
        
        #self.gross_load_kw_df.set_index('datetime', inplace=True)
        # sort values by timestamp in case they are not
        self.gross_load_kw_df.sort_values(by='datetime', inplace=True)

        # fill in missing data
        # I take the avg of the prices over all the data
        # at the same hours and fill the nulls with
        # those values

        avg_period_prices = \
            self.gross_load_kw_df.groupby('time_utc')['actual_kwh']\
                .transform('mean')
        
        self.gross_load_kw_df['actual_kwh'] = \
            self.gross_load_kw_df['actual_kwh'].\
                fillna(value = avg_period_prices)
        
        self.gross_load_kw_df.reset_index(inplace=True)

    def evaluate_granularity(self) -> float:
        """
        most common time increament in minutes

        """
        self.time_increaments_minutes = \
            self.gross_load_kw_df['datetime']\
                .diff()\
                    .dropna()\
                        .mode().iloc[0]\
                            .seconds/60
        
    class Config:
        arbitrary_types_allowed = True
    