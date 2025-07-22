# python basics
from pydantic import BaseModel, validator, ValidationError
from dataclasses import dataclass, field
from typing import Dict, List
import logging
logging.basicConfig(level=logging.DEBUG)

# repo dependencies
import pandas as pd
import numpy as np

class Battery(BaseModel):
    capacity_kwh: float
    max_charge_rate_kw: float
    max_discharge_rate_kw: float
    charge_efficiency_pct: float
    discharge_efficiency_pct: float
    initial_state_of_energy: float
        

    @validator('charge_efficiency_pct')
    def charge_efficiency_pct_range(cls, value):
        if value < 0 or value > 100:
            return ValidationError(
                "charge_efficiency_pct not within the range")
        return value
    
    @validator('discharge_efficiency_pct')
    def discharge_efficiency_pct_range(cls, value):
        if value < 0 or value > 100:
            return ValidationError(
                "discharge_efficiency_pct not within the range")
        return value
    

    

