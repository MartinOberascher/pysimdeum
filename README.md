# pySIMDEUM
Repository to share demand generator Python software with Mirjam Blokker and KWR

Uses Python 3.x

Used Python packages:

* numpy
* pandas
* matplotlib
* seaborn (only used to make plots look nicer)
* xarray
* traits (for strict type definitions of classes, could be replaced by Python's type annotations)
* toml
* pymc3 (is at the moment only in the computation of user presence time, planned to be replaced in future)


It is recommended to install Python Anaconda distribution from https://www.anaconda.com/distribution/

All packages can be installed either with `conda install <packagename>` or `pip install <packagename>` in a terminal. 

The Python script `sim_water_use.py` shows how the pySIMDEUM can be used.
