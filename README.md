Readme
================================

This is an enhancement to the current version of High Frequency Trading Model with IB @ https://github.com/jamesmawm/High-Frequency-Trading-Model-with-IB.

In this version, I've decoupled modules, used functional programming styles, made things simpler and enable switching between different strategies. Oh, and a custom backtester too with bid/ask price simulated events (Zipline gave my code cancer).

Again, these files are for evaluation purposes only and do not constitute real profitable trading models.

Features
===============
- Reuse multiple strategies on the same IB framework. See src/Strat-Empty.py for a template.
- src/Backtester/* contains custom backtester which reads in a CSV file. Supports limit orders-based strategies with bid ask price simulation.

Strategies
=============
- Strat-Pairs.py: Pairs trading through cointegration, using OLS and Pandas.
- Strat-LmtOrdrs.py: Limit-order based strategy with GUI dashboard. Works with backtester.
- Strat-CorrelRptr.py: Stores ticks in a dataframe and reports the correlations.

How To
=============
- Connecting to IB and getting live ticks in 3 simple steps:
``` 
self.ibhft = ibHFT.IbHFT()
self.ibhft.set_connection_with_api_gateway(False)
self.ibhft.start_data_stream(self.on_started
                                 , self.on_tick
                                 , STOCKS_TO_STREAM
                                 , self.on_position_changed)

```

- Same 3 simple steps in getting historical data:
```
self.ibhft = ibHFT.IbHFT()
self.ibhft.set_connection_with_api_gateway(False)
self.ibhft.start_historical_data_stream(self.stocks_to_stream
                                  , self.duration
                                  , self.interval
                                  , self.process_historical_data)
```

- For backtesting, same 3 simple steps:
```
self.ibhft = bt.Backtester()
self.ibhft.set_csv_file("ticks 10 mins - Jun 25 2014.csv")
self.ibhft.start_data_stream(self.on_started
                                 , self.on_tick
                                 , STOCKS_TO_STREAM
                                 , self.on_position_changed)
```                                 






