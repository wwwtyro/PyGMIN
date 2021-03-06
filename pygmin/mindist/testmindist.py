import numpy as np
import unittest

#from pygmin.mindist import findBestPermutation
#from pygmin.mindist.permutational_alignment import permuteArray, findBestPermutationList, findBestPermutationListOPTIM

def randomCoordsAA(nmol):
    import pygmin.utils.rotations as rot
    coords = np.zeros(2*3*nmol, np.float64)
    coords[0:3*nmol] = np.random.uniform(-1,1,[nmol*3]) * 1.3*(3*nmol)**(1./3)
    for i in range(nmol):
        k = 3*nmol + 3*i
        coords[k : k + 3] = rot.random_aa()
    return coords


class TestMinDist(unittest.TestCase):
    """
    a base class for mindist unit tests
    """
    def runtest(self, X1, X2, mindist, **kwargs):
        X1i = np.copy(X1)
        X2i = np.copy(X2)
        
        if len(kwargs.items()) == 0:
            kwargs["permlist"] = self.permlist
        
        (distreturned, X1, X2) = mindist(X1, X2, **kwargs)

        distinit = np.linalg.norm(self.X1 - X2i)
        distfinal = np.linalg.norm(X1 - X2)
        self.assertAlmostEqual( distfinal, distreturned, 5, "returned distance is wrong: %g != %g, difference %g" % (distfinal, distreturned, distfinal-distreturned) )
        self.assertLessEqual(distfinal, distinit)
        
        #test if the energies have changed
        Ei = self.pot.getEnergy(X1i)        
        Ef = self.pot.getEnergy(X1)
        self.assertAlmostEqual( Ei, Ef, 10, "Energy of X1 changed: %g - %g = %g" % (Ei, Ef, Ei - Ef) )
        Ei = self.pot.getEnergy(X2i)        
        Ef = self.pot.getEnergy(X2)
        self.assertAlmostEqual( Ei, Ef, 10, "Energy of X2 changed: %g - %g = %g" % (Ei, Ef, Ei - Ef) )

        return distreturned, X1, X2

    
    