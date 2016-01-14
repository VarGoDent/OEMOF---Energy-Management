# -*- coding: utf-8 -*-

""" Example application that models Germany as one region for the year 2033.

Data
----

The application uses some data from BNetzA scenario 2033 B. Demand-series
are generated randomly.

Notes
-----
The energy system is build out of objects. It is solved and the results
are written back into the objects.

"""
import matplotlib.pyplot as plt


from oemof.core import energy_system as es
# solph imports
from oemof.solph.optimization_model import OptimizationModel
from oemof.solph import predefined_objectives as predefined_objectives
# base classes import
from oemof.core.network.entities import Bus
from oemof.core.network.entities.components import sinks as sink
from oemof.core.network.entities.components import sources as source
from oemof.core.network.entities.components import transformers as transformer
from oemof.outputlib import to_pandas as tpd
from oemof.tools import logger

import pandas as pd
import logging


logger.define_logging()

data = pd.read_csv("example_data.csv", sep=",")
timesteps = [t for t in range(168)]

# emission factors in t/MWh
em_lig = 0.111 * 3.6
em_coal = 0.0917 * 3.6
em_gas = 0.0556 * 3.6
em_oil = 0.0750 * 3.6

# resources
bcoal = Bus(uid="coal", type="coal", price=20, balanced=False, excess=False)
bgas = Bus(uid="gas", type="gas", price=35, balanced=False, excess=False)
boil = Bus(uid="oil", type="oil", price=40,  balanced=False, excess=False)
blig = Bus(uid="lignite", type="lignite", balanced=False, price=15,
           excess=False)

# electricity and heat
b_el = Bus(uid="b_el", type="el", excess=False, shortage=False)
b_th = Bus(uid="b_th", type="th", excess=True, shortage=False)

# renewable sources (only pv onshore)
wind_on = source.DispatchSource(uid="wind_on", outputs=[b_el],
                                val=data['wind'],
                                out_max=[66.300], dispatch_costs=0, opex_fix=0)
pv = source.DispatchSource(uid="pv", outputs=[b_el], val=data['pv'],
                           out_max=[65.300], opex_var=0)

# demands
demand_el = sink.Simple(uid="demand_el", inputs=[b_el],
                        val=data['demand_el']/1000)
demand_th = sink.Simple(uid="demand_th", inputs=[b_th],
                        val=data['demand_th']*50)

# Simple Transformer for b_el
pp_coal = transformer.Simple(uid='pp_coal', inputs=[bcoal], outputs=[b_el],
                             in_max={bcoal.uid: None},
                             out_max=[20.200], eta=[0.39],
                             opex_fix=2, opex_var=25, co2_var=em_coal)
pp_lig = transformer.Simple(uid='pp_lig', inputs=[blig], outputs=[b_el],
                            in_max=[None],
                            out_max=[11.800], eta=[0.41],
                            opex_fix=2, opex_var=19, co2_var=em_lig)
pp_gas = transformer.Simple(uid='pp_gas', inputs=[bgas], outputs=[b_el],
                            in_max=[None], out_max=[41.000], eta=[0.45],
                            opex_fix=2, opex_var=40, co2_var=em_gas)

pp_oil = transformer.Simple(uid='pp_oil', inputs=[boil], outputs=[b_el],
                            in_max=[None],
                            out_max=[0.1000], eta=[0.3],
                            opex_fix=2, opex_var=50, co2_var=em_oil)
# chp (not from BNetzA) eta_el=0.3, eta_th=0.3
pp_chp = transformer.CHP(uid='pp_chp', inputs=[bgas], outputs=[b_el, b_th],
                         in_max=[100],
                         out_max=[40, 30],
                         eta=[0.4, 0.3], opex_fix=0, opex_var=50,
                         co2_var=em_gas)
stor = transformer.Storage(uid='storage', inputs=[b_el], outputs=[b_el],
                           cap_max=100, cap_initial=0, opex_var=0,
                           out_max=[2], in_max=[2])
# group busses
buses = [bcoal, bgas, boil, blig, b_el, b_th]

# group components
transformers = [pp_coal, pp_lig, pp_gas, pp_oil, pp_chp, stor]
renew_sources = [pv, wind_on]
sinks = [demand_th, demand_el]

components = transformers + renew_sources + sinks
entities = components + buses

logging.info('Create simulation object')
# first standard solving
simulation = es.Simulation(
    solver='glpk', timesteps=timesteps, stream_solver_output=True,
    objective_options={'function': predefined_objectives.minimize_cost})
energysystem = es.EnergySystem(entities=entities, simulation=simulation)

if False:
    logging.info('Create optimization model')
    om_validation = OptimizationModel(energysystem=energysystem)
    om_validation.solve(solver='gurobi', debug=False, tee=True, duals=True)
    results_validation = om_validation.results()

    # visualization
    time_index = pd.date_range('1/1/2012', periods=len(timesteps), freq='H')
    es_df = tpd.EnergySystemDataFrame(result_object=results_validation,
                                      time_slice=time_index)

    es_df.plot_bus('b_el', bus_type='el', type='input', kind='bar',
                   df_plot_kwargs={'width':1, 'lw':0, 'stacked':True})

if True:
    logging.info('Using rolling optimization')
    simulation.rolling = True
    from oemof.solph import rolling_optimization as roll_opt
    results = roll_opt.solve_rolling(energysystem, 24, 10)

    # compare dual variables of rolling and standard optimization
    df = pd.DataFrame({'duals_rolling': results[b_el][b_el]})
    df.plot(drawstyle='steps', ylim=(0, 60))
