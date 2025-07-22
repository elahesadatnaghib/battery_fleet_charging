from enum import Enum, auto

class OptimizationStrategy(Enum):
    OPT1 = auto()
    OPT2 = auto()
    
    @classmethod
    def __contains__(cls, item): 
        return isinstance(item, cls)