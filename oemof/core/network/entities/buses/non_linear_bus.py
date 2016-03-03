# -*- coding: utf-8 -*-
from .. import Bus


class CustomizedBus(Bus):
    r"""
    A bus containing the parameter rotating mass.

    Parameters
    ----------
    rot_mass : float
        Rotating mass of the system [% of total load]

    """

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        self.rot_mass = kwargs.get('rot_mass', 0.4)