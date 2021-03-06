import numpy as np
import copy
from pygmin.optimize import Result

from pygmin.potentials.potential import potential as basepot
import pygmin.defaults as defaults
from pygmin.transition_states import findLowestEigenVector


__all__ = ["findTransitionState", "FindTransitionState"]


class TSRefinementPotential(basepot):
    """
    this is a potential wrapper for use in an optimization package.  The intent
    is to try to locate the nearest transition state of the system.
    
    Usage:

    getEnergyGradient():
        will return the gradient with the component along the eigenvector
        removed.  This is for energy minimization in the space tangent to the
        gradient    
    """
    def __init__(self, pot, eigenvec):
        """
        Parameters
        ----------
        
        orthogZeroEigs : callable
            The function which makes a vector orthogonal to known zero
            eigenvectors.  The default value is 0, which means use the default
            function orthogopt which assumes rotational and translational
            invariance.  If None is pass then no function will be used
        """
        self.pot = pot
        self.eigenvec = eigenvec

    def getEnergyGradient(self, coords):
        """
        return the energy and the gradient with the component along the
        eigenvec removed.  For use in energy minimization in the space
        perpendicular to eigenvec
        """
        e, grad = self.pot.getEnergyGradient(coords)
        #norm = np.sum(self.eigenvec)
        grad -= np.dot(grad, self.eigenvec) * self.eigenvec
        return e, grad



class FindTransitionState(object):
    """
    This class implements the routine for finding the nearest transition state
    
    ***orthogZeroEigs is system dependent, don't forget to set it***
    
    Parameters
    ----------
    coords : 
        the starting coordinates
    pot : 
        the potential class
    tol : 
        the tolerance for the rms gradient
    event : callable
        This will be called after each step
    nsteps : 
        number of iterations
    nfail_max :
        if the lowest eigenvector search fails this many times in a row
        than the algorithm ends
    eigenvec0 : 
        a guess for the initial lowest eigenvector
    iprint :
        the interval at which to print status messages
    orthogZeroEigs : callable
        this function makes a vector orthogonal to the known zero
        eigenvectors

            orthogZeroEigs=0  : default behavior, assume translational and
                                rotational symmetry
            orthogZeroEigs=None : the vector is unchanged

    lowestEigenvectorQuenchParams : dict 
        these parameters are passed to the quench routine for he lowest
        eigenvector search 
    tangentSpaceQuenchParams : dict 
        these parameters are passed quench routine for the minimization in
        the space tabgent to the lowest eigenvector 
    max_uphill_step : 
        the maximum step uphill along the direction of the lowest
        eigenvector
    demand_initial_negative_vec : bool
        if True, abort if the initial lowest eigenvalue is positive
    nsteps_tangent1, nsteps_tangent2 : int
        the number of iterations for tangent space minimization before and after
        the eigenvalue is deemed to be converged
        
    
    Notes
    -----
    
    It is composed of the following steps
        1) Find eigenvector corresponding to the lowest *nonzero*
        eigenvector.  
        
        2) Step uphill in the direction of the lowest eigenvector
        
        3) minimize in the space tangent to the lowest eigenvector
    
    See Also
    --------
    findTransitionState : function wrapper for this class
    findLowestEigenVector : a core algorithm
    pygmin.landscape.LocalConnect : the class which most often calls this routine
     
    """
    """
    implementation notes: this class needs to deal with
    
    params for stepUphill : 
        probably only maxstep
    
    params for lowest eigenvector search : 
        should be passable and loaded from defaults.
        important params : 
            max steps 
            what to do if a negative eigenvector is found
            what to do if small overlap with previous eigenvector
    
    params for tangent space search : 
        should be passable and loaded from defaults.
        

    todo:
        if the eigenvalue sign goes from positive to negative,
        go back to where it was negative and take a smaller step
        
        The tolerances for the various steps of this algorithm must be correlated.
        if the tol for tangent space search is lower than the total tol, then it will never finish
    
    """
    def __init__(self, coords, pot, tol=1e-4, event=None, nsteps=100, 
                 nfail_max=5, eigenvec0=None, iprint=-1, orthogZeroEigs=0,
                 lowestEigenvectorQuenchParams=dict(),
                 tangentSpaceQuenchParams=dict(), 
                 max_uphill_step=0.1,
                 demand_initial_negative_vec=True,
                 nsteps_tangent1=10,
                 nsteps_tangent2=100,
                 ):
        self.pot = pot
        self.coords = np.copy(coords)
        self.tol = tol
        self.nsteps = nsteps
        self.event = event
        self.nfail_max = nfail_max
        self.nfail = 0
        self.eigenvec = eigenvec0
        self.orthogZeroEigs = orthogZeroEigs
        self.iprint = iprint
        self.lowestEigenvectorQuenchParams = lowestEigenvectorQuenchParams
        self.max_uphill_step = max_uphill_step
        self.tangent_space_quencher = defaults.tangentSpaceQuenchRoutine
        self.tangent_space_quench_params = dict(defaults.tangentSpaceQuenchParams.items() +
                                                tangentSpaceQuenchParams.items())
        self.demand_initial_negative_vec = demand_initial_negative_vec    
        self.nnegative_max = max(10, self.nsteps / 5)
        
        self.rmsnorm = 1./np.sqrt(float(len(coords))/3.)
        self.oldeigenvec = None

        #set tolerance for the tangent space minimization.  
        #Be sure it is tighter tolerance than self.tol
        self.tol_tangent = self.tol * 0.2
        if self.tangent_space_quench_params.has_key("tol"):
            self.tol_tangent = min(self.tol_tangent, 
                                   self.tangent_space_quench_params["tol"])
            del self.tangent_space_quench_params["tol"]
        self.nsteps_tangent1 = nsteps_tangent1
        self.nsteps_tangent2 = nsteps_tangent2
        if self.tangent_space_quench_params.has_key("maxstep"):
            self.maxstep_tangent = self.tangent_space_quench_params["maxstep"]
            del self.tangent_space_quench_params["maxstep"]
        else:            
            self.maxstep_tangent = 0.1 #this should be determined in a better way


        #set some parameters used in finding lowest eigenvector
        #initial guess for Hermitian
        self.H0_leig = None 
        
        self.H0_transverse = None
        
        self.reduce_step = 0
        self.step_factor = .1
        self.nnegative = 0
        
        self.verbosity = 1
        
    def _saveState(self, coords):
        self.saved_coords = np.copy(coords)
        self.saved_eigenvec = np.copy(self.eigenvec)
        self.saved_eigenval = self.eigenval
        self.saved_overlap = self.overlap
        self.saved_H0_leig = self.H0_leig
        self.saved_H0_transverse = self.H0_transverse
        #self.saved_oldeigenvec = np.copy(self.oldeigenvec)

    def _resetState(self, coords):
        coords = np.copy(self.saved_coords)
        self.eigenvec = np.copy(self.saved_eigenvec)
        self.eigenval = self.saved_eigenval
        self.oldeigenvec = np.copy(self.eigenvec)
        self.overlap = self.saved_overlap
        self.H0_leig = self.saved_H0_leig
        self.H0_transverse = self.saved_H0_transverse
        return coords

    def run(self):
        """The main loop of the algorithm"""
        coords = np.copy(self.coords)
        res = Result() #  return object
        res.message = []
        for i in xrange(self.nsteps):
            
            #get the lowest eigenvalue and eigenvector
            self.overlap = self._getLowestEigenVector(coords, i)
            overlap = self.overlap
            
            #check to make sure the eigenvector is ok
            if i == 0 or self.eigenval <= 0:
                self._saveState(coords)
                self.reduce_step = 0
            else:
                self.nnegative += 1
                if self.nnegative > self.nnegative_max:
                    print "warning: negative eigenvalue found too many times. ending", self.nnegative
                    res.message.append( "negative eigenvalue found too many times %d" % self.nnegative )
                    break
                if self.verbosity > 2:
                    print "the eigenvalue turned positive.", self.eigenval, "Resetting last good values and taking smaller steps"
                coords = self._resetState(coords)
                self.reduce_step += 1
            
            #step uphill along the direction of the lowest eigenvector
            coords = self._stepUphill(coords)

            if False:
                #maybe we want to update the lowest eigenvector now that we've moved?
                #david thinks this is a bad idea
                overlap = self._getLowestEigenVector(coords, i)

            #minimize the coordinates in the space perpendicular to the lowest eigenvector
            coords, tangentrms = self._minimizeTangentSpace(coords)


            #check if we are done and print some stuff
            E, grad = self.pot.getEnergyGradient(coords)
            rms = np.linalg.norm(grad) * self.rmsnorm
            gradpar = np.dot(grad, self.eigenvec) / np.linalg.norm(self.eigenvec)
            
            if self.iprint > 0:
                if (i+1) % self.iprint == 0:
                    ostring = "findTransitionState: %3d E %g rms %g eigenvalue %g rms perp %g grad par %g overlap %g" % (
                                    i, E, rms, self.eigenval, tangentrms, gradpar, overlap)
                    extra = "  Evec search: %d rms %g" % (self.leig_result.nfev, self.leig_result.rms)
                    extra += "  Tverse search: %d step %g" % (self.tangent_result.nfev, 
                                                                    self.tangent_move_step)
                    extra += "  Uphill step:%g" % (self.uphill_step_size,)
                    print ostring, extra
            
            if callable(self.event):
                self.event(E, coords, rms)
            if rms < self.tol:
                break
            if self.nfail >= self.nfail_max:
                print "stopping findTransitionState.  too many failures in eigenvector search", self.nfail
                res.message.append( "too many failures in eigenvector search %d" % self.nfail )
                break

            if i == 0 and self.eigenval > 0.:
                print "WARNING *** initial eigenvalue is positive - increase NEB spring constant?"
                if self.demand_initial_negative_vec:
                    print "            aborting transition state search"
                    res.message.append( "initial eigenvalue is positive %f" % self.eigenval )
                    break

        #done.  do one last eigenvector search because coords may have changed
        self._getLowestEigenVector(coords, i)

        #done, print some data
        print "findTransitionState done:", i, E, rms, "eigenvalue", self.eigenval
    
        success = True
        #check if results make sense
        if self.eigenval >= 0.:
            if self.verbosity > 2:
                print "warning: transition state is ending with positive eigenvalue", self.eigenval
            success = False
        if rms > self.tol:
            if self.verbosity > 2:
                print "warning: transition state search appears to have failed: rms", rms
            success = False
        if i >= self.nsteps:
            res.message.append( "maximum iterations reached %d" % i )
            

        #return results
        res.coords = coords
        res.energy = E
        res.eigenval = self.eigenval
        res.eigenvec = self.eigenvec
        res.grad = grad
        res.rms = rms
        res.nsteps = i
        res.success = success
        return res


        
    def _getLowestEigenVector(self, coords, i):
        res = findLowestEigenVector(coords, self.pot, H0=self.H0_leig, eigenvec0=self.eigenvec, 
                                    orthogZeroEigs=self.orthogZeroEigs,
                                    **self.lowestEigenvectorQuenchParams)
        self.leig_result = res
        
#        if res.eigenval > 0.:
#            print "warning transition state search found positive lowest eigenvalue", res.eigenval, \
#                "step", i
        
        self.H0_leig = res.H0
        self.eigenvec = res.eigenvec
        self.eigenval = res.eigenval
        self.oldeigenvec = self.eigenvec.copy()
        
        if i > 0:
            overlap = np.dot(self.oldeigenvec, res.eigenvec)
            if overlap < 0.5 and self.verbosity > 2:
                print "warning: the new eigenvector has low overlap with previous", overlap, self.eigenval
        else:
            overlap = 0.

        if res.success:
            self.nfail = 0
        else:
            self.nfail += 1
        
        return overlap
    
    def _minimizeTangentSpace(self, coords):
        """
        now minimize the energy in the space perpendicular to eigenvec.
        There's no point in spending much effort on this until 
        we've gotten close to the transition state.  So limit the number of steps
        to 10 until we get close.
        """
        #determine the number of steps
        #i.e. if the eigenvector is deemed to have converged
        use_gradpar = False
        if use_gradpar:
            E, grad = self.pot.getEnergyGradient(coords)
            gradpar = np.dot(grad, self.eigenvec) / np.linalg.norm(self.eigenvec)
            eigenvec_converged = np.abs(gradpar) <= self.tol*2.
        else:
            eigenvec_converged = self.overlap > .999 
        
        nstepsperp = self.nsteps_tangent1
        if eigenvec_converged:
            nstepsperp = self.nsteps_tangent2

        maxstep = self.maxstep_tangent
        if self.reduce_step > 0:
            maxstep *= (self.step_factor)**self.reduce_step



        tspot = TSRefinementPotential(self.pot, self.eigenvec)
        coords1 = np.copy(coords)
        ret = self.tangent_space_quencher(coords, tspot.getEnergyGradient, 
                                          nsteps=nstepsperp, tol=self.tol_tangent,
                                          maxstep=maxstep,
                                          H0 = self.H0_transverse,
                                          **self.tangent_space_quench_params)
        coords = ret[0]
        self.tangent_move_step = np.linalg.norm(coords - coords1)
        rms = ret[2]
        self.tangent_result = ret[4]
        self.H0_transverse = self.tangent_result.H0
        return coords, rms

    def _stepUphill(self, coords):
        """
        step uphill in the direction of self.eigenvec.  self.eigenval is used
        to determine the best stepsize
        """
        e, grad = self.pot.getEnergyGradient(coords)
        F = np.dot(grad, self.eigenvec) 
        h = 2.*F/ np.abs(self.eigenval) / (1. + np.sqrt(1.+4.*F**2/self.eigenval**2 ))

        maxstep = self.max_uphill_step
        if self.reduce_step > 0:
            maxstep *= (self.step_factor)**self.reduce_step


        if np.abs(h) > maxstep:
            h *= maxstep / abs(h)
        self.uphill_step_size = h
        coords += h * self.eigenvec

        return coords


def findTransitionState(*args, **kwargs):
    """
    simply a wrapper for initializing and running FindTransitionState
    
    See Also
    --------
    FindTransitionState : for all documentation
    """
    finder = FindTransitionState(*args, **kwargs)
    return finder.run()



###################################################################
#below here only stuff for testing
###################################################################


def testgetcoordsLJ():
    a = 1.12 #2.**(1./6.)
    theta = 60./360*np.pi
    coords = [ 0., 0., 0., \
              -a, 0., 0., \
              -a/2, a*np.cos(theta), 0., \
              -a/2, -a*np.cos(theta), 0.3 \
              ]
    coords = np.array(coords)
    return coords


def guesstsATLJ():
    from pygmin.potentials.ATLJ import ATLJ
    pot = ATLJ(Z = 2.)
    a = 1.12 #2.**(1./6.)
    theta = 60./360*np.pi
    coords1 = np.array([ 0., 0., 0., \
              -a, 0., 0., \
              -a/2, -a*np.cos(theta), 0. ])
    coords2 = np.array([ 0., 0., 0., \
              -a, 0., 0., \
              a, 0., 0. ])
    from pygmin.optimize import lbfgs_py as quench
    from pygmin.transition_states import InterpolatedPath
    ret1 = quench(coords1, pot.getEnergyGradient)
    ret2 = quench(coords2, pot.getEnergyGradient)
    coords1 = ret1[0]
    coords2 = ret2[0]
    from pygmin.transition_states import NEB
    neb = NEB(InterpolatedPath(coords1, coords2, 30), pot)
    neb.optimize()
    neb.MakeAllMaximaClimbing()
    #neb.optimize()
    for i in xrange(len(neb.energies)):
        if(neb.isclimbing[i]):
            coords = neb.coords[i,:]
    return pot, coords

def guessts(coords1, coords2, pot):
    from pygmin.optimize import lbfgs_py as quench
    from pygmin.mindist.minpermdist_stochastic import minPermDistStochastic as mindist
    from pygmin.transition_states import NEB
    ret1 = quench(coords1, pot.getEnergyGradient)
    ret2 = quench(coords2, pot.getEnergyGradient)
    coords1 = ret1[0]
    coords2 = ret2[0]
    natoms = len(coords1)/3
    dist, coords1, coords2 = mindist(coords1, coords2, permlist=[range(natoms)])
    print "dist", dist
    print "energy coords1", pot.getEnergy(coords1)
    print "energy coords2", pot.getEnergy(coords2)
    from pygmin.transition_states import InterpolatedPath
    neb = NEB(InterpolatedPath(coords1, coords2, 20), pot)
    #neb.optimize(quenchParams={"iprint" : 1})
    neb.optimize(iprint=-30, nsteps=100)
    neb.MakeAllMaximaClimbing()
    #neb.optimize(quenchParams={"iprint": 30, "nsteps":100})
    for i in xrange(len(neb.energies)):
        if(neb.isclimbing[i]):
            coords = neb.coords[i,:]
    return pot, coords, neb.coords[0,:], neb.coords[-1,:]


def guesstsLJ():
    from pygmin.potentials.lj import LJ
    pot = LJ()
    natoms = 9
    coords = np.random.uniform(-1,1,natoms*3)
    from pygmin.basinhopping import BasinHopping
    from pygmin.takestep.displace import RandomDisplacement
    from pygmin.takestep.adaptive import AdaptiveStepsize
    from pygmin.storage.savenlowest import SaveN
    saveit = SaveN(10)
    takestep1 = RandomDisplacement()
    takestep = AdaptiveStepsize(takestep1, frequency=15)
    bh = BasinHopping(coords, pot, takestep, storage=saveit, outstream=None)
    bh.run(100)
    coords1 = saveit.data[0].coords
    coords2 = saveit.data[1].coords
    
    return guessts(coords1, coords2, pot)




    

def testgetcoordsATLJ():
    a = 1.12 #2.**(1./6.)
    theta = 40./360*np.pi
    coords = [ 0., 0., 0., \
              -a, 0., 0., \
              a*np.cos(theta), a*np.sin(theta), 0. ]
    return np.array(coords)

def testpot1():
    import itertools
    from pygmin.printing.print_atoms_xyz import printAtomsXYZ as printxyz
    pot, coords, coords1, coords2 = guesstsLJ()
    coordsinit = np.copy(coords)
    natoms = len(coords)/3
    c = np.reshape(coords, [-1,3])
    for i, j in itertools.combinations(range(natoms), 2):
        r = np.linalg.norm(c[i,:] - c[j,:])
        print i, j, r 
    
    e, g = pot.getEnergyGradient(coords)
    print "initial E", e
    print "initial G", g, np.linalg.norm(g)
    print ""
    

    
    
    from pygmin.printing.print_atoms_xyz import PrintEvent

    #print ret
    
    with open("out.xyz", "w") as fout:
        e = pot.getEnergy(coords1)
        print "energy of minima 1", e
        printxyz(fout, coords1, line2=str(e))
        e, grad = pot.getEnergyGradient(coordsinit)
        print "energy of NEB guess for the transition state", e, "rms grad", \
            np.linalg.norm(grad) / np.sqrt(float(len(coords))/3.)
        printxyz(fout, coordsinit, line2=str(e))
        e = pot.getEnergy(coords2)
        print "energy of minima 2", e
        printxyz(fout, coords2, line2=str(e))
        
        #mess up coords a bit
        coords += np.random.uniform(-1,1,len(coords))*0.05
        e = pot.getEnergy(coords)
        printxyz(fout, coords, line2=str(e))

        defaults.quenchParams["iprint"] = 1
        #defaults.lowestEigenvectorQuenchParams["iprint"] = 1
        defaults.tsSearchParams["iprint"] = 1
        
        printevent = PrintEvent(fout)
        print ""
        print "starting the transition state search"
        ret = findTransitionState(coords, pot, event=printevent, iprint=-1)
        print ret
        #coords, eval, evec, e, grad, rms = ret
        e = pot.getEnergy(ret.coords)
        printxyz(fout, coords2, line2=str(e))

    print "finished searching for transition state"
    print "energy", e
    print "rms grad", ret.rms
    print "eigenvalue", ret.eigenval
    
    if False:
        print "now try the same search with the dimer method"
        from pygmin.NEB.dimer import findTransitionState as dimerfindTS
        coords = coordsinit.copy()
        tau = np.random.uniform(-1,1,len(coords))
        tau /= np.linalg.norm(tau)
        ret = dimerfindTS(coords, pot, tau )
        enew, grad = pot.getEnergyGradient(ret.coords)
        print "energy", enew
        print "rms grad", np.linalg.norm(grad) / np.sqrt(float(len(ret.coords))/3.)



if __name__ == "__main__":
    testpot1()
