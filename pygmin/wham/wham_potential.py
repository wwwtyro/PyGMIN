import numpy as np
from pygmin.potentials.potential import potential

class WhamPotential(potential):
    """
    #############################################################################
    # the idea behind this minimization procedure is as follows: 
    #############################################################################
    
    from a simulation at temperature T you find the probability of finding energy
    E is P(E,T).  We know this can be compared to the density of states n(E) as
    
    P(E,T) = n(E) exp(-E/T)
    
    the density of states is independent of temperature, so we can use it to find
    P(E) at any other temperature, or Z(T), etc.  But our estimate of n(E) from
    one temperature is not very good.  So we combine P(E,T) multiple simulations
    at different temperatures to get a better estimate of n(E).  The true density
    of states, n_T(E) is the weighted average of n_i(E) at all temperatures T_i
    
    n_F(E) = sum_i w_i*n_i(E) = sum_i w_i*P(E,T_i)*exp(E/T_i)
    
    where w_i are unknown. The best estimate for n_F(E) will be when the equality
    is satisfied as much as possible term by term.  Define exp(R) the deviation from
    the term-by-term agreement
    
    R(E,T_i) = log(n_F(E)) - log(w_i) - log( P(E,T_i)*exp(E/T_i) )
    
    we want to make each R(E,T_i) as small as possible.  Define an "energy" function
    
    CHI2 = sum_E sum_i P(E,T_i)*|R(E,T_i)|^2
    
    Where each R(E,T_i) contributes weight proportional to P(E,T_i) to the sum to
    make sure those with better statistics are more heavily weighted.  To solve
    the problem we find the set of {n_F(E), w_i} which minimize CHI2
    """
    def __init__(self, logP, reduced_energy):
        """
        To make it fit withing existing minimization schemes, we need to view it as a linear problem

        nrep:  the number of replica variables, i.e. len(w_i)

        nbins: the number of bins in the histogram, e.g. len(n_F(E))

        logP: = log(P(E,T_i)) a.k.a. log(visits) a 2d array of shape( nreps, nbins).

        reduced_energy:  E/T_i  a 2d array of shape( nreps, nbins) giving the
            reduced energy of each bin

        note: this works perfectly well for 2d histograms as well.  In this case the 2d 
            histograms should be linearized
        
        warning: many bins will be completely unoccupied for all replicas.  This means there will be 
            a lot of extra work done trying to minimize irrelevant variables.  This is fine, just make sure
            logP == 0 for all bins with zero visits, not logP = -inf
        """
        self.nreps = len( logP[:,0] )
        self.nbins = len( logP[0,:] )
        self.logP = logP
        self.weight = self.logP + reduced_energy
        #self.reduced_energy = reduced_energy
        if ( np.isinf(self.logP).any() or np.isnan(self.logP).any() ):
            print "logP is NaN or infinite"
            exit(1)

        if True: #see how much effort is wasted
            nallzero = len( np.where(np.abs(self.logP.sum(1)) < 1e-10 )[0])
            print "WHAM: number of degrees of freedom", self.nreps + self.nbins
            print "WHAM: number of irrelevant d.o.f. ", nallzero

    def getEnergy(self, X):
        """
        X: is the array of unknowns of length nrep + nbins
            X[0:nrep] = {w_i}         : the replica unknowns
            X[nrep:] = {log(n_F(E))}  : the bin unknowns

        R(E,T_i) = log(n_F(E)) - log(w_i) - log( P(E,T_i)*exp(E/T_i) )
    
        energy = sum_E sum_i P(E,T_i)*|R(E,T_i)|^2
        """
        wi = X[:self.nreps]
        lognF = X[self.nreps:]
        """
        energy = 0.
        for irep in range(self.nreps):
            for ibin in range(self.nbins):
                R = lognF[ibin] - wi[irep] -( logP[irep, ibin]  + reduced_energy[irep, ibin])
                energy += logP[irep, ibin] * R**2
        """
        energy = np.sum( self.logP * (lognF[np.newaxis,:] - wi[:,np.newaxis] - self.weight)**2 )
        return energy

    def getEnergyGradient(self, X):
        """
        X: is the array of unknowns of length nrep + nbins
            X[0:nrep] = {w_i}         : the replica unknowns
            X[nrep:] = {log(n_F(E))}  : the bin unknowns

        R(E,T_i) = log(n_F(E)) - log(w_i) - log( P(E,T_i)*exp(E/T_i) )
    
        energy = sum_E sum_i P(E,T_i)*|R(E,T_i)|^2
        """
        wi = X[:self.nreps]
        lognF = X[self.nreps:]
        R = lognF[np.newaxis,:] - wi[:,np.newaxis] - self.weight
        
        energy = np.sum( self.logP * (R)**2 )
        
        gradient = np.zeros(len(X))
        gradient[:self.nreps] = -2. * np.sum( self.logP * R, axis=1 )
        gradient[self.nreps:] = 2. * np.sum( self.logP * R, axis=0 )
        #print np.shape(gradient)
        #print gradient
    
        return energy, gradient

    
