import aerosandbox as asb
from aerosandbox.geometry import Wing, WingXSec, Airfoil
import numpy as np

#need to implement the calculation of the tail AC
#THIS NEEDS TO BE RUN AFTER THE TAIL OPTIMIZER CALCS VALUES.
#THIS PROGRAM EXPECTS DATA THAT IS AN OUTPUT FROM THE OPTIMIZER

class PlaneMaker:
    def __init__(self, wing, tail, plane):
        
        self.tail = tail
        self.plane = plane
        self.wing = wing     
        self.tail_incidence = 0

        #calculated
        self.tail.AC = (self.tail.span / 2) * np.tan(self.tail.LE_sweep) + ((self.tail.chordR + self.tail.chordT) / 2) * 0.25
     
    # This def makes the plane from components
    def MakePlane(self):
        # ============= WING =============
        wing = asb.Wing (
            name = "Main Wing",
            symmetric = True,
            xsecs = [
                #root 
                WingXSec(
                    xyz_le = [0, 0, 0],
                    chord = self.wing.chordR,
                    airfoil = Airfoil(self.wing.airfoil)
                ),
                #taper start
                WingXSec (
                    xyz_le = [0, self.wing.span / 2 * self.wing.taper_start, 0],                
                    chord = self.wing.chordR,
                    airfoil = Airfoil(self.wing.airfoil),

                    control_surface_type="symmetric",
                    control_surface_deflection = 0,  # degrees
                    control_surface_hinge_point = 1 - (self.wing.chord_percentage / self.wing.chordR),
                ),
                #tip 
                WingXSec (
                    xyz_le = [0 / 39.3701, self.wing.span / 2, 0 / 39.3701], 
                    chord = self.wing.chordT,     
                    airfoil = Airfoil(self.wing.airfoil),
                    
                    control_surface_type="symmetric",
                    control_surface_deflection = 0,  # degrees
                    control_surface_hinge_point = 1 - (self.wing.chord_percentage / self.wing.chordT),
                ),
            ],
            chordwise_resolution = 2,
            spanwise_resolution = 3
        )

        # ============= TAIL =============
        #this is relative to the leading edge of the tail
        tail_le = self.tail.chordR * 0.25 + self.tail.lever - self.tail.AC
        #3.4 / 39.3701
        #this code sharts itself the second you ask for negative sweep. This is buns. I will be fixing at some point

        #TE = self.tail.span / 2 * np.tan(self.tail.TE_sweep)

        tip = tail_le + (self.tail.span / 2 * np.tan(self.tail.LE_sweep))
        
        ruddervator = asb.ControlSurface(
            name = "ruddervator",
            symmetric = True,
            deflection = self.tail.deflection,  # degrees
            hinge_point = 1 - (self.tail.chord_percentage),
            trailing_edge = True,
        )
            
        tail = asb.Wing (
            name = "Tail",
            symmetric = True,
            xsecs = [
                #root
                WingXSec (
                    xyz_le = [tail_le, 0, self.tail.root_height],
                    chord = self.tail.chordR,
                    airfoil = Airfoil(self.tail.airfoil),
                    twist = self.tail_incidence,
                    control_surfaces=[ruddervator]
                ),
                #tip tail_le + (np.tan(self.tail_LE_sweep) + np.tan(self.tail_TE_sweep)) * self.tailspan,
                WingXSec (
                    xyz_le = [
                        tip,
                        self.tail.span / 2 * np.cos(self.tail.dihedral), 
                        self.tail.root_height + (self.tail.span / 2) * np.sin(self.tail.dihedral)
                    ],
                    chord = self.tail.chordT,
                    airfoil = Airfoil(self.tail.airfoil),
                    twist = self.tail_incidence,
                    control_surfaces=[ruddervator]
                ),
            ],
            chordwise_resolution = 2,
            spanwise_resolution = 3
        )

        airplane = asb.Airplane (
            name = "UW-26 Mako", 
            xyz_ref=[0, 0, 0],
            wings = [wing, tail],
        )

        return (airplane)