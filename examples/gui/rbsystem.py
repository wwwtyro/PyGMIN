from PyQt4 import QtGui
import NewLJ
import numpy as np
from pygmin.storage import savenlowest
from pygmin.NEB import NEB
        
class RBSystem:
    def __init__(self):
        dlg = NewLJDialog()
        dlg.exec_()
        self.nmol = dlg.natoms()
        self.mysys = self.createSystem()
        self.nsave = dlg.nsave()
        if dlg.result() == QtGui.QDialog.Rejected:
            raise BaseException("Aborted parameter dialog")
        self.storage = savenlowest.SaveN(self.nsave)

    def createSystem(self):
        import pygmin.potentials.lj as lj
        from pygmin.potentials.rigid_bodies.molecule import setupLWOTP
        from pygmin.potentials.rigid_bodies.sandbox import RBSandbox
        #setup otp molecule
        otp = setupLWOTP()
        #set up interactions between sites
        potential = lj.LJ()
        interaction_matrix = [[potential]]
        #set up system
        mols = [otp for i in range(self.nmol)]
        mysys = RBSandbox(mols, interaction_matrix)
        return mysys
        
        
    def createBasinHopping(self):
        import pygmin.basinhopping as bh
        import pygmin.utils.rotations as rot
        mysys = self.createSystem()
        nsites = mysys.nsites
        nmol = self.nmol
        #set up initial coords
        coords = np.zeros(2*3*nmol)
        coords[0:nmol*3] = np.random.uniform(-1,1,[nmol*3]) * 1.0*(nsites)**(1./3)
        for i in range(nmol):
            k = nmol*3 + 3*i
            coords[k : k + 3] = rot.random_aa()
        #set up take step routine
        from pygmin.potentials.rigid_bodies.take_step import RBTakeStep
        step = RBTakeStep()
        opt = bh.BasinHopping(coords,mysys,
                          temperature=1., takeStep=step, outstream=None)
        return opt
    
    def draw(self, coordslinear, index):
        from OpenGL import GL,GLUT
        xyzlinear = self.mysys.getxyz(coordslinear)
        xyz = xyzlinear.reshape(xyzlinear.size/3, 3)
        com=np.mean(xyz, axis=0)                  
        if index == 1:
            color1 = [0.65, 0.0, 0.0, 1.]
            color2 = [0.35, 0.0, 0.0, 1.]
        else:
            color1 = [0.00, 0.65, 0., 1.]
            color2 = [0.00, 0.35, 0., 1.]
        GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, color2)
        for i, xx in enumerate(xyz):
            if i % 3 == 0:
                GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, color1)
            else:
                GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_DIFFUSE, color2)
            x=xx-com
            GL.glPushMatrix()            
            GL.glTranslate(x[0],x[1],x[2])
            GLUT.glutSolidSphere(0.4,30,30)
            GL.glPopMatrix()

        #now try to draw cylinders connecting atoms in a molecule
        nsites = len(xyz[:,0])
        z = np.array([0.,0.,1.]) #default cylinder orientation
        for j1 in range(0,nsites,3):
            X1 = xyz[j1,:] - com
            for j2 in range(j1+1,j1+3,1):
                #draw a cylinder from xyz[j1] to xyz[j2]
                X2 = xyz[j2,:] - com
                p = X2-X1 #desired cylinder orientation
                r = np.linalg.norm(p)
                t = np.cross(z,p)  #angle about which to rotate
                a = np.arccos( np.dot( z,p) / r ) #rotation angle
                a *= (180. / np.pi)  #change units to angles
                GL.glPushMatrix()
                GL.glTranslate( X1[0], X1[1], X1[2] )
                GL.glRotate( a, t[0], t[1], t[2] )
                GLUT.glutSolidCone(.2,r,30,30)  #I can't seem to draw a cylinder
                GL.glPopMatrix()
         



    def Align(self, coords1, coords2):
        from pygmin.mindist.minpermdist_rbmol import minPermDistRBMol as minpermdist
        dist, X1, X2 = minpermdist( coords1, coords2, self.mysys, niter = 100 )
        return X1, X2
    
    def createNEB(self, coords1, coords2):
        return NEB.NEB(coords1, coords2, self.mysys, k = 100., nimages=20)

       

class NewLJDialog(QtGui.QDialog,NewLJ.Ui_DialogLJSetup):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)
    def natoms(self):
        return int(self.lineNatoms.text())
    def nsave(self):
        return int(self.lineNsave.text())
        
if __name__ == "__main__":
    import pygmin.gui.run as gr
    gr.run_gui(RBSystem)
