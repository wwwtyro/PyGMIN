# -*- coding: iso-8859-1 -*-
import sys
from pygmin.mc import MonteCarlo
import pygmin.defaults as defaults

class BasinHopping(MonteCarlo):
    """
    A class to run the basin hopping algorithm

    Parameters
    ----------
    All required and optional parameters from base class MonteCarlo :
    quenchRoutine : callable, optional
        Use this non-default quench routine.
    quenchParameters : dict(), optional
        parameters passed to the quench routine
    insert_rejected : bool
        insert the rejected structure into the storage class
    
    See Also
    --------
    pygmin.mc.MonteCarlo : base class
    pygmin.potentials, pygmin.takestep, pygmin.storage, pygmin.accept_tests


    """

    def __init__(self, coords, potential, takeStep, storage=None, event_after_step=[], \
            acceptTest=None,  \
            temperature=1.0, \
            quenchRoutine = defaults.quenchRoutine, \
            quenchParameters = defaults.quenchParams, \
            confCheck = [], \
            outstream = sys.stdout,
            insert_rejected = False
            ):
        #########################################################################
        #initialize MonteCarlo base class
        #########################################################################
        MonteCarlo.__init__(self, coords, potential, takeStep, \
                            storage=storage, \
                            event_after_step=event_after_step, \
                            acceptTest=acceptTest,  \
                            temperature=temperature, \
                            confCheck = confCheck, \
                            outstream=outstream,store_initial=False)

        self.quenchRoutine = quenchRoutine
        self.quenchParameters = quenchParameters
        
        #########################################################################
        #do initial quench
        #########################################################################
        self.markovE_old = self.markovE
        res = \
            self.quenchRoutine(self.coords, self.potential.getEnergyGradient, **self.quenchParameters)
        newcoords, Equench, self.rms, self.funcalls = res[:4]
        self.coords = newcoords
        self.markovE = Equench

        self.insert_rejected = insert_rejected
        
        if(self.storage):
            self.storage(self.markovE, self.coords)
        
        #print the initial quench
        self.acceptstep = True
        self.trial_energy = self.markovE
        self.printStep()


    def _mcStep(self):
        """
        take one monte carlo basin hopping step

        overload the MonteCarlo base class step
        """
        self.coords_after_step = self.coords.copy() #make  a working copy
        #########################################################################
        #take step
        #########################################################################
        self.takeStep.takeStep(self.coords_after_step, driver=self)

        #########################################################################
        #quench
        #########################################################################
        ret = self.quenchRoutine(self.coords_after_step, \
                                 self.potential.getEnergyGradient, **self.quenchParameters)
        self.trial_coords = ret[0]
        self.trial_energy = ret[1] 
        self.rms = ret[2]
        self.funcalls = ret[3]

        #########################################################################
        # check if step is a valid configuration, otherwise reject
        #########################################################################
        self.acceptstep = True
        for check in self.confCheck:
            if not check(self.trial_energy, self.trial_coords, driver=self):
                self.acceptstep=False
        
        #########################################################################
        #check whether step is accepted with user defined tests.  If any returns
        #false then reject step.
        #########################################################################
        if self.acceptstep:
            self.acceptstep = self.acceptTest(self.markovE, self.trial_energy, self.coords, self.trial_coords)

        #########################################################################
        #return new coords and energy and whether or not they were accepted
        #########################################################################
        return self.acceptstep, self.trial_coords, self.trial_energy


    def printStep(self):
        if self.stepnum % self.printfrq == 0:
            if self.outstream != None:
                self.outstream.write( "Qu   " + str(self.stepnum) + " E= " + str(self.trial_energy) + " quench_steps= " + str(self.funcalls) + " RMS= " + str(self.rms) + " Markov E= " + str(self.markovE_old) + " accepted= " + str(self.acceptstep) + "\n" )
    
    def __getstate__(self):
        ddict = self.__dict__.copy();
        del ddict["outstream"]
        del ddict["potential"]
        return ddict #.items()
    
    def __setstate__(self, dct):
        self.__dict__.update(dct)
        self.outstream = sys.stdout


if __name__ == "__main__":
    from pygmin.systems import LJCluster
    natoms = 13
    sys = LJCluster(natoms)
    bh = sys.get_basinhopping()
    bh.run(100)

