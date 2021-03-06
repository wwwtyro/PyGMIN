import tempfile
import numpy as np

from pygmin.systems import AtomicCluster
from pygmin.potentials.ljpshiftfast import LJpshift
from pygmin.utils.xyz import write_xyz
from pygmin.mindist import CoMToOrigin

__all__ = ["BLJCluster"]

class BLJCluster(AtomicCluster):
    """
    define the System class for a binary Lennard-Jones cluster
    
    Parameters
    ----------
    natoms : int
    ntypeA : int
        number of type-A, big particles
    **kwargs : other keyword parameters
        these are passed on to the potential
    
    See Also
    --------
    BaseSystem, AtomicCluster

    """
    def __init__(self, natoms, ntypeA="default", **potential_kwargs):
        super(BLJCluster, self).__init__()
        self.natoms = natoms
        if ntypeA == "default":
            self.ntypeA = int(self.natoms * 0.8)
        else:
            self.ntypeA = ntypeA
        self.potential_kwargs = potential_kwargs
        

        self.params["database"]["accuracy"] = 1e-3

    
    def get_potential(self):
        return LJpshift(self.natoms, self.ntypeA, **self.potential_kwargs)
    
    def get_permlist(self):
        return [range(self.ntypeA), range(self.ntypeA, self.natoms)]

    #
    # stuff for the gui below here
    #

    def draw(self, coordslinear, index):
        """
        tell the gui how to represent your system using openGL objects
        
        Parameters
        ----------
        coords : array
        index : int
            we can have more than one molecule on the screen at one time.  index tells
            which one to draw.  They are viewed at the same time, so they should be
            visually distinct, e.g. different colors.  accepted values are 1 or 2        
        """
        # index = 1 or 2
        from OpenGL import GL,GLUT
        coords = coordslinear.reshape(coordslinear.size/3, 3)
        com=np.mean(coords, axis=0)                  
        size = 0.5
        if index == 1:
            color = [0.65, 0.0, 0.0, 1.]
        else:
            color = [0.00, 0.65, 0., 1.]
        GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, color)
        for i,xx in enumerate(coords):
            if i == self.ntypeA: 
                size *= 0.88 #this should be dependent on lj parameters
                if index == 1:
                    color = [0.25, 0.00, 0., 1.]
                else:
                    color = [0.00, 0.25, 0., 1.]
                GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, color)
            x=xx-com
            GL.glPushMatrix()            
            GL.glTranslate(x[0],x[1],x[2])
            GLUT.glutSolidSphere(size,30,30)
            GL.glPopMatrix()

    def load_coords_pymol(self, coordslist, oname, index=1):
        """load the coords into pymol
        
        the new object must be named oname so we can manipulate it later
                        
        Parameters
        ----------
        coordslist : list of arrays
        oname : str
            the new pymol object must be named oname so it can be manipulated
            later
        index : int
            we can have more than one molecule on the screen at one time.  index tells
            which one to draw.  They are viewed at the same time, so should be
            visually distinct, e.g. different colors.  accepted values are 1 or 2
        
        Notes
        -----
        the implementation here is a bit hacky.  we create a temporary xyz file from coords
        and load the molecule in pymol from this file.  
        """
        #pymol is imported here so you can do, e.g. basinhopping without installing pymol
        import pymol 

        #create the temporary file
        suffix = ".xyz"
        f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix)
        fname = f.name
                
        #write the coords into the xyz file
        from pygmin.mindist import CoMToOrigin
        labels = ["LA" for i in range(self.ntypeA)] + \
                 ["LB" for i in range(self.natoms - self.ntypeA)]
        for coords in coordslist:
            coords = CoMToOrigin(coords.copy())
            write_xyz(f, coords, title=oname, atomtypes=labels)
        f.flush()
#        self.f = f # so the file is not deleted
#        print fname
                
        #load the molecule from the temporary file
        pymol.cmd.load(fname)
        
        #get name of the object just create and change it to oname
        objects = pymol.cmd.get_object_list()
        objectname = objects[-1]
        pymol.cmd.set_name(objectname, oname)
        
        #set the representation
        pymol.cmd.hide("everything", oname)
        pymol.cmd.show("spheres", oname)

        #make the B atoms smaller
        seleA = "%s and name LA" % (oname)
        seleB = "%s and name LB" % (oname)
        pymol.cmd.set("sphere_scale", value=1.0, selection=seleA)
        pymol.cmd.set("sphere_scale", value=0.8, selection=seleB)

        
        #set the color according to index
        if index == 1:
            pymol.cmd.color("red", selection=seleA)
            pymol.cmd.color("firebrick", selection=seleB)
        else:
            pymol.cmd.color("deepolive", selection=seleA)
            pymol.cmd.color("smudge", selection=seleB)


#
#only for testing below here
#


def run():
    #create the system object
    sys = BLJCluster(15)
    
    #create a database
    db = sys.create_database()
    
    #do a short basinhopping run
    bh = sys.get_basinhopping(database=db, outstream=None)
    while len(db.minima()) < 2:
        bh.run(100)
    
    #try to connect the lowest two minima
    min1, min2 = db.minima()[:2]
    connect = sys.get_double_ended_connect(min1, min2, db)
    connect.connect()
    

if __name__ == "__main__":
    run()