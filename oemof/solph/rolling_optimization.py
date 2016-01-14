# -*- coding: utf-8 -*-
"""

@author: Simon Hilpert (simon.hilpert@fh-flensburg.de)
"""
from ..solph.optimization_model import OptimizationModel as OM
from ..core.network.entities import components as cp

def solve_rolling(energysystem=None, period_length=24, overlapp=24):
    r"""

    Parameters
    ----------
    energysystem : energysystem object
    period_length : int
        length of the periods (without overlapp)
    overlapp :
        overlapp of additional 'forecast'
    """
    if not energysystem.simulation.rolling:
        raise ValueError('Can not solve problem rolling. Please set ' +
                         'energysystem.simulation.rolling attribute to True.')

    total_timesteps = energysystem.simulation.timesteps

    period_length = period_length
    overlapp = overlapp
    periods = range(int(len(total_timesteps) / period_length)-1)


    storages = [s for s in energysystem.entities
                if isinstance(s, cp.transformers.Storage)]
    dispatch_sources = [ds for ds in energysystem.entities
                        if isinstance(ds, cp.sources.DispatchSource)]

    for period in periods:
        # start timestep
        start = period*period_length
        # end timestep
        end = start+period_length+overlapp
        # for the last period the total length of result are taken. simulation
        # timesteps are only the rest from start to max. length of timesteps
        if period == 0:
            energysystem.simulation.timesteps = range(0,
                                                      min(end,
                                                          len(total_timesteps)))
            result_slice = range(start, start+period_length)
            #print(energysystem.simulation.timesteps, result_slice, period)
            om = OM(energysystem=energysystem)
            om.solve(solver='gurobi', debug=False, tee=False, duals=True)
            results=om.results(timesteps=result_slice)
        # for last period
        elif period == periods[-1]:
            energysystem.simulation.timesteps = range(start-1,
                                                      max(end,
                                                          len(total_timesteps)))
            result_slice = range(start, max(end, len(total_timesteps)))
            #print(energysystem.simulation.timesteps, result_slice, period)
            om, results = roll(energysystem, om, results, start, end, storages,
                               dispatch_sources, result_slice)
        # for all other periods 'normal' behaviour
        else:
            energysystem.simulation.timesteps = range(start-1,
                                                      min(end,
                                                          len(total_timesteps)))
            result_slice = range(start, start+period_length)
            #print(energysystem.simulation.timesteps, result_slice, period)
            om, results = roll(energysystem, om, results, start, end, storages,
                               dispatch_sources, result_slice)

        #energysystem.results = results
    return results


def roll(energysystem, om_last, results, start, end, storages,
         dispatch_sources, result_slice=None):
    r"""
    """
    #om_last = om
    om = OM(energysystem=energysystem)
    for edge in om_last.all_edges:
        om.w[edge, start-1].value = om_last.w[edge, (start-1)].value
        om.w[edge, start-1].fix()
    if storages:
        for s in storages:
            getattr(om, str(s.__class__)).cap[s.uid, (start-1)].value = \
                getattr(om_last, str(s.__class__)).cap[s.uid, (start-1)].value
            getattr(om, str(s.__class__)).cap[s.uid, (start-1)].fix()
    if dispatch_sources:
        for ds in dispatch_sources:
            getattr(om, str(cp.sources.DispatchSource)).curtailment_var[ds.uid, (start-1)].value = \
               getattr(om_last, str(cp.sources.DispatchSource)).curtailment_var[ds.uid, (start-1)].value
            getattr(om, str(cp.sources.DispatchSource)).curtailment_var[ds.uid, (start-1)].fix()
    om.solve(solver='gurobi', debug=False, tee=False, duals=True)
    results = om.results(result=results, timesteps=result_slice)
    return (om, results)
