Readme
================================

This is an enhancement to the current version of High Frequency Trading Model with IB @ https://github.com/jamesmawm/High-Frequency-Trading-Model-with-IB.

Again, these files are for evaluation purposes only and do not constitute real profitable trading models.

Features
===============
- Use multiple strategies on the same IB framework. See src/Strat-Empty.py for a template.
- src/Backtester/* contains custom backtester which reads in a CSV file. Supports limit orders-based strategies with bid ask price simulation.

Strategies
=============
- Strat-Pairs.py: Pairs trading through cointegration, using OLS and Pandas.
- Strat-LmtOrdrs.py: Limit-order based strategy with GUI dashboard. Works with backtester.
- Strat-CorrelRptr.py: Stores ticks in a dataframe and reports the correlations.





