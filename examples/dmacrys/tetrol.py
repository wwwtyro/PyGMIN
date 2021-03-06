import dmagmin_ as GMIN
import pygmin.potentials.gminpotential as gminpot
import pygmin.basinhopping as bh
from pygmin.takestep import generic,group
from pygmin.utils.rbtools import *
from pygmin.potentials.coldfusioncheck import addColdFusionCheck
from pygmin.storage import savenlowest
from pygmin.utils import dmagmin

import pickle

nsave = 1000
nsteps = 1000
dump_frequency=10
temperature=0.4
maxnoimprove=20

quenchParameters={}
quenchParameters["tol"]=1e-4
quenchParameters["nsteps"]=1000
quenchParameters["maxErise"]=2e-2
quenchParameters["maxstep"]=0.1
quenchParameters["M"]=100
     
class MyStep(generic.TakestepInterface):
    def takeStep(self, coords, **kwargs):
        from pygmin.takestep import buildingblocks as bb
        ca = CoordsAdapter(nrigid=GMIN.getNRigidBody(), nlattice=6, coords=coords)
        bb.rotate(1.6, ca.rotRigid)
        #from pygmin.utils import lattice
        #bb.reduced_coordinates_displace(0.0, lattice.lowerTriangular(ca.lattice), ca.posRigid)
        ca.lattice*=1.2              
    
GMIN.initialize()
pot = gminpot.GMINPotential(GMIN)

coords = pot.getCoords()
print "initial energy ", pot.getEnergy(coords)

step1 = MyStep()
reseed = dmagmin.GenRandomCrystal(CoordsAdapter(nrigid=GMIN.getNRigidBody(), nlattice=6, coords=coords))
step = group.Reseeding(step1, reseed, maxnoimprove=maxnoimprove)

#save = pickle.load(open("storage"))
#save.nsave = 1000
save = savenlowest.SaveN(nsave=100, accuracy=1e-3)
save.compareMinima = dmagmin.compareMinima

opt = bh.BasinHopping(coords, pot, takeStep=step, 
                      quenchRoutine=dmagmin.quenchCrystal,
                      temperature=temperature, storage=save,
                      quenchParameters=quenchParameters)
addColdFusionCheck(opt)

# create cif directory if it does not exist
import os, errno
try:
    os.makedirs('cif')
except OSError, e:
    if e.errno != errno.EEXIST:
        raise


for i in xrange(1,nsteps/dump_frequency):
    opt.run(dump_frequency)
    #pickle.dump(save, open("storage."+str(i), "w"))
    pickle.dump(save, open("storage", "w"))
    i=0
    for m in save.data:
        i+=1
        GMIN.writeCIF("cif/lowest%03d.cif"%(i), m.coords, "E"+str(m.energy))
