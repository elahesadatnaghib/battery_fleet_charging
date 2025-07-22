
# EV fleet Optimization modeling
An optimization framework for scheduling fleet charging under dynamic electricity pricing and capacity fees. The model guarantees SoC (State of Charge) requirements while minimizing combined energy and demand costs.

## The Math
### The objective function has five terms:
The first three terms formulate the cost of demand charge and energy in dollars. The fourth term μ gives preference to the earlier time periods for scheduling the charging. Parameter ε1 is chosen such that this preference is applied only if it makes no difference in the cost (If there is degeneracy, μ resolves it). The last term λ enforces all the free variables to be zero, for example when the EV is not in the depot. Solvers usually do this automatically. Many of the terms in μ and λ are proper scaling to ensure that numerical errors would not interfere with the goals of μ and λ terms.


### Constraints
first, second, and the third constraints set the boundaries and the definition of the state of charge (SoC) for each battery. The fourth constraint, introduces a new variable to identify whether the SoC is below or above the required threshold. The fifth constraint, uses this identifier to set upper-bound on the charging rate of the battery. The sixth constraint, enforces the definition of max demand, being the maximum of the cumulative charging of the EV batteries across time. The last two constraints are the definition of μ and λ, that are explained in the Objective Function section.


## project structure
```
./
    pyproject.toml
    README.md
    utils.py
    poetry.lock
    main.py
    core/
        __init__.py
        optimization_model.py
        optimizers.py
    data/
        load_data.csv
        outputs/
            battery_plan.csv
    src/
        battery.py
        __init__.py
        strategy_type.py
        data_prep.py
```

## Run Project
1. Place the input data in `data` folder.

The data should be named `load_data` and be of the following structure:

datetime,                   actual_kwh
2012-11-01 01:00:00-07:00   45.6

2. The `main.py` is the user interface. First, specify the desired configurations in configs dictionary, then run main.py.

3. Find the output in `data/outputs` folder.

## Initial Set up
To set up the environment, you need to install the dependancies via either of the two methods:

method 1 - Poetry
* install poetry (https://python-poetry.org/docs/)
* set up virtual environment by running 
`poetry config virtualenvs.in-project true`
then 
`poetry env use python3.9`
* then 
`poetry install`

method 2 - Pip
* take the package names and versions from the [tool.poetry.dependencies] section in pyproject.toml
* manually run `pip install <package_name>==<version>`

Once the dependencies are installed, run the following command in the terminal:
`poetry run python main.py`

