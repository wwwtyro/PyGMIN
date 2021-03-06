"""
.. currentmodule:: pygmin.potentials

Potentials
==========

This module contains all the potentials that are included in pygmin.
The list is not very long because we have made it very easy for you
to write your own.

Base Potential
--------------

All potentials are derived from the base class

.. autosummary::
   :toctree: generated/

    BasePotential

When creating your own potential, only member function which must absolutely
be overloaded is getEnergy().  Many routines in pygmin 
also use gradient information, so it is highly recommended to also
implement getEnergyGradient().  Otherwise the gradients will be calculated
numerically and your system will run a lot slower.

pygmin potentials
-----------------
these are potentials that exist completely within the pygmin package

.. autosummary::
    :toctree: generated/

    LJ
    LJCut
    LJpshift
    ATLJ
    XYModel
    HeisenbergModel
    HeisenbergModelRA

GMIN potentials
---------------
.. autosummary::
   :toctree: generated/

    GMINPotential

other external potentials
-------------------------
to be written

""" 


from potential import *
from lj import *
from ATLJ import *
from coldfusioncheck import *
from gminpotential import *
from heisenberg_spin import *
from heisenberg_spin_RA import *
from ljpshiftfast import *
from ljcut import *
#from potential import *
#from salt import *
from soft_sphere import *
#from stockmeyer import *
from xyspin import *
