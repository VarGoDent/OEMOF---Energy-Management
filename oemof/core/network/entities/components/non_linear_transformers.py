# -*- coding: utf-8 -*-
from .transformers import Storage
from .transformers import Simple
import logging
import numpy as np


class CustomizedSimple(Simple):
    """
    A customized Transformer with variable electrical efficiency
    Note: The model uses constraints which require binary variables, hence
    objects of this class will results in mixed-integer-linear-problems.
    Represents a diesel generator

    Parameters
    ----------
    eta_total : float
        total constant efficiency for the transformer
    eta_el : list
        list containing the minimial (first element) and maximal (second
        element) electrical efficiency (0 <= eta_el <= 1)
    """
    optimization_options = {}

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        self.min_load = kwargs.get('min_load', 0.1)

        self.eta_total = sum(self.eta)
        self.min_loading = np.array(self.min_load / 100 * self.out_max)
        #self.power

    def power_generation(self, residual_load, **kwargs):
        #power_output = np.maximum(self.min_loading, residual_load)
        power_output = max(self.min_loading, residual_load)
        if residual_load == 0:
            power_output = 0
        # if rm_residual >0, power_out = rm_residual
        power_surplus = power_output - residual_load
        return power_output, power_surplus

    def fuel_costs_and_volume_py(self, power_flow, **kwargs):
        peak_load = np.diff(np.concatenate((np.array([0]), power_flow)))
        peak_load = peak_load.clip(min=0, max=None)
        base_load = power_flow - peak_load
        fuel_volume = (base_load / self.eta_min * 100 + peak_load /
                       self.eta * 100)
        fuel_costs = fuel_volume.sum() * self._economics.fuel_costs()
        return fuel_costs, fuel_volume

    def maximum_output(self, t=None, year=None):
        return self.power


class CustomizedStorage(Storage):
    """
    Parameters
    ----------
    cycle_no : float
        number of cycles of the battery
    """
    optimization_options = {}

    def __init__(self, power=0, capacity=0, **kwargs):

        super().__init__(**kwargs)

        self.cycle_no = kwargs.get('cycle_no', 2000)
        self.capex_po = kwargs.get('capex_po', 0)
        self.capex_ca = kwargs.get('capex_ca', 0)
        self.dod_max = kwargs.get('dod_max', 0.80)

        self.__current_soc = self.cap_initial

        self.__power_ch = power / self.eta_in
        self.__power_dch = power
        self.__capacity = capacity

    def maximum_output(self, t=None):
        return self.maximum_discharge_el()

    #def maximum_discharge(self):
        #return np.maximum(0, np.minimum(self.__power_dch,
            #(self.__current_soc - (1 - self.dod_max)) *
            #self.__capacity) * self.eta_out)

    def maximum_discharge_el(self):
        return max(0, min(self.__power_dch, (
            self.__current_soc - 1 + self.dod_max) * (
                self.__capacity * self.eta_out)))

    #def maximum_charge(self):
        #return np.minimum(self.__power_ch, (1 - self.__current_soc) *
            #self.__capacity / self.eta_in)

    def maximum_charge_el(self):
        return min(self.__power_ch,
                  (1 - self.__current_soc) * self.__capacity / self.eta_in)

    def discharge(self, residual_load):
        power_dch = min(residual_load, self.maximum_discharge_el())
        #power_dch = np.minimum(residual_load, self.maximum_discharge())
        self.__current_soc = (self.__current_soc - power_dch /
            self.__capacity / self.eta_out)
        return power_dch, self.__current_soc

    def charge(self, residual_load):
        #power_ch = np.minimum(residual_load, self.maximum_charge())
        power_ch = min(residual_load, self.maximum_charge_el())
        energy_ch = min((self.__power_ch * self.eta_in), (1 - (
            self.__current_soc)) * self.__capacity)  # battery in
        #self.__current_soc = (self.__current_soc + power_ch /
            #self.__capacity * self.eta_in)
        self.__current_soc = (self.__current_soc + energy_ch /
            self.__capacity * self.eta_in)
        # in current_soc the time-changing variable of power has to be assigned
        # (named energy)
        return power_ch, self.__current_soc
