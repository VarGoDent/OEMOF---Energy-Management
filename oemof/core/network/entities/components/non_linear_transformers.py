# -*- coding: utf-8 -*-
from .transformers import Storage
from .transformers import Simple
import numpy as np
from scipy.interpolate import interp1d


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

        self.eta_total = self.eta
        self.min_loading = self.min_load * self.out_max

    def power_generation(self, residual_load, **kwargs):
        """
        Define power generation value of generator while considering the
        case that the generator can be switched off (power = 0).
        """
        power_output = 0.0
        power_surplus = 0.0
        if residual_load == 0:
            power_output = 0.0
            power_surplus = 0.0
        else:
            power_output = np.maximum(self.min_loading, residual_load)
            power_surplus = power_output - residual_load

        return power_output, power_surplus

    def fuel_and_volume(self, power_flow, diesel_price, **kwargs):
        """
        Calculate fuel costs and fuel volume according to power flow
        and technical and financial input parameters.

        Parameters
        ----------
        power_flow : pd.DataFrame or pd.Series
            holds results of the power flow loop for the generator
        diesel_price: float
            price of diesel at specific location
        """
        eff = np.array([0, self.eta_min, self.eta_total])
        load = np.array([0, self.out_max * self.eta_min, self.out_max])
        interp = interp1d(load, eff)
        load_values = np.linspace(0, 100, num=100)
        # linear interpolation, should change for higher accuracy
        eff_curve = interp(load_values)

        #TODO
        # compare with Matlab simulation and complete calculations
        fuel_volume = 0
        fuel_costs = 0

        #try:
            #fuel_volume = power_flow / eff_curve[power_flow] * 100
        #except KeyError:
            #if eff_curve[power_flow] <= 0:
                #fuel_volume = 0.0
            #else:
                #raise ValueError('Value is not in efficiancy curve.')
        ## crosscheck (from Matlab file)
        #fuel_costs = fuel_volume.sum() * diesel_price / 10

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

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        self.capacity = kwargs.get('capacity', 0)
        self.crate = kwargs.get('c_rate_in', 1)
        self.power = kwargs.get('power', 0)
        self.power = self.capacity * self.crate  # kW

        self.cycle_no = kwargs.get('cycle_no', 2000)
        self.capex_po = kwargs.get('capex_po', 0)
        self.capex_ca = kwargs.get('capex_ca', 0)
        self.dod_max = kwargs.get('dod_max', 0.80)

        self.__current_soc = self.cap_initial

        self.__power_ch = self.power / self.eta_in
        self.__power_dch = self.power
        self.__capacity = self.capacity

    def maximum_output(self):
        return self.maximum_discharge_el()

    def maximum_discharge_el(self):
        return np.maximum(0.0, np.minimum(self.__power_dch, (
            self.__current_soc - 1 + self.dod_max) * (
                self.__capacity * self.eta_out)))

    def maximum_charge_el(self):
        return np.minimum(self.__power_ch,
                  (1.0 - self.__current_soc) * self.__capacity / self.eta_in)

    def discharge(self, residual_load):
        power_dch = np.minimum(residual_load, self.maximum_discharge_el())
        energy_dch = np.minimum((power_dch / self.eta_out), (
            self.__current_soc - 1 + self.dod_max) * self.__capacity)

        # in current_soc the time-changing variable of power is assigned
        # (named energy)
        self.__current_soc = (self.__current_soc - energy_dch /
            self.__capacity)

        return power_dch, self.__current_soc

    def charge(self, residual_load):
        power_ch = np.minimum(residual_load, self.maximum_charge_el())
        energy_ch = np.minimum((power_ch * self.eta_in), (1 - (
            self.__current_soc)) * self.__capacity)

        # in current_soc the time-changing variable of power is assigned
        # (named energy)
        self.__current_soc = (self.__current_soc + energy_ch /
            self.__capacity)

        return power_ch, self.__current_soc
