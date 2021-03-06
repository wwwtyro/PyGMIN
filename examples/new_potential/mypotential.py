"""
an example of how to create a new potential.
"""

from pygmin.potentials import BasePotential

class MyPot(BasePotential):
    """a Lennard Jones potential with altered expoenents
    
    V(r) = r**-24 - r**-12
    """
    def __init__(self, natoms):
        self.natoms = natoms #number of atoms
    
    def getEnergy(self, coords):
        coords = np.reshape(coords, [self.natoms,3])
        E = 0.
        for i in range(self.natoms):
            for j in range(i):
                r = np.sqrt(np.sum((coords[i,:] - coords[j,:])**2)) 
                E += r**-24 - r**-12
        return E
    
    def getEnergyGradient(self, coords):
        coords = np.reshape(coords, [self.natoms,3])
        E = 0.
        grad = np.zeros(coords.shape)
        for i in range(self.natoms):
            for j in range(i):
                dr = coords[i,:] - coords[j,:]
                r = np.sqrt(np.sum(dr**2)) 
                E += r**(-24) - r**(-12)
                g = 24. * r**(-25) - 12. * r**(-13)
                grad[i,:] += -g * dr/r
                grad[j,:] += g * dr/r
        return E, grad.reshape(-1)

from pygmin.systems import BaseSystem
from pygmin.mindist import minPermDistStochastic, MinDistWrapper, ExactMatchCluster
from pygmin.transition_states import orthogopt
class MySystem(BaseSystem):
    def __init__(self, natoms):
        super(MySystem, self).__init__()
        self.natoms = natoms
        self.params.database.accuracy =0.1

    def get_potential(self):
        return MyPot(self.natoms)
    
    def get_mindist(self):
        permlist = [range(self.natoms)]
        return MinDistWrapper(minPermDistStochastic, permlist=permlist, niter=10)

    def get_orthogonalize_to_zero_eigenvectors(self):
        return orthogopt
    
    def get_compare_exact(self, **kwargs):
        permlist = [range(self.natoms)]
        return ExactMatchCluster(permlist=permlist, **kwargs)
    

import numpy as np
def run_basinhopping():
    natoms = 8
    sys = MySystem(natoms)
    database = sys.create_database()
    x0 = np.random.uniform(-1,1,[natoms*3])
    bh = sys.get_basinhopping(database=database, coords=x0)
    bh.run(10)
    print "found", len(database.minima()), "minima"
    min0 = database.minima()[0]
    print "lowest minimum found has energy", min0.energy
    return sys, database

def run_double_ended_connect(sys, database):
    #connect the all minima to the lowest minimum
    minima = database.minima()
    min1 = minima[0]
    for min2 in minima[1:]:
        connect = sys.get_double_ended_connect(min1, min2, database)
        connect.connect()

from pygmin.utils.disconnectivity_graph import DisconnectivityGraph
from pygmin.landscape import Graph
import matplotlib.pyplot as plt

def make_disconnectivity_graph(database):
    graph = Graph(database).graph
    dg = DisconnectivityGraph(graph, nlevels=3, center_gmin=True)
    dg.calculate()
    dg.plot()
    plt.show()

def test_potential():
    import numpy as np
    natoms = 5
    pot = MyPot(natoms)
    coords = np.random.uniform(-1,1,natoms*3)
    e = pot.getEnergy(coords)
    print e
    e, g = pot.getEnergyGradient(coords)
    print e

    gnum = pot.NumericalDerivative(coords, eps=1e-6)
    print np.max(np.abs(gnum-g)), np.max(np.abs(gnum))
    print np.max(np.abs(gnum-g)) / np.max(np.abs(gnum))

if __name__ == "__main__":
    #test_potential()
    
    mysys, database = run_basinhopping()
    run_double_ended_connect(mysys, database)
    make_disconnectivity_graph(database)
    