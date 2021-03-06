# -*- coding: iso-8859-1 -*-
############################################################
#Example 5: Adding a custom takestep routine.  This example
#takes 100 monte carlo steps as one basin hopping step
############################################################
import numpy as np
import pygmin.potentials.lj as lj
import pygmin.basinhopping as bh
from pygmin.takestep import displace
from pygmin.takestep import group
from pygmin.mc import MonteCarlo

class TakeStepMonteCarlo:
    def __init__(self, pot, T = 10., nsteps = 100, stepsize=0.1):
        self.potential = pot
        self.T =  T
        self.nsteps = nsteps
        
        self.mcstep = displace.RandomDisplacement(stepsize=stepsize)
    
    def takeStep(self, coords, **kwargs):
        #make a new monte carlo class
        mc = MonteCarlo(coords, self.potential, self.mcstep, 
                        temperature = self.T, outstream=None)
        mc.run( self.nsteps )
        coords[:] = mc.coords[:]
    
    def updateStep(self, acc, **kwargs):
        pass
        


natoms = 12

# random initial coordinates
coords=np.random.random(3*natoms)
potential = lj.LJ()

reseed = TakeStepMonteCarlo(potential, T=100, nsteps=1000)
takestep = displace.RandomDisplacement(stepsize=0.5)

stepGroup = group.Reseeding(takestep, reseed, maxnoimprove=20)

opt = bh.BasinHopping(coords, potential, takeStep=stepGroup)
opt.run(100)

# some visualization
try: 
    import pygmin.utils.pymolwrapper as pym
    pym.start()
    pym.draw_spheres(opt.coords, "A", 1)
except:
    print "Could not draw using pymol, skipping this step"