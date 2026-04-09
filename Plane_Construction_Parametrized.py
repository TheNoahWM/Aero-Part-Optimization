import aerosandbox as asb
from aerosandbox.geometry import Wing, WingXSec, Airfoil
import numpy as np

#need to implement the calculation of the tail AC
#THIS NEEDS TO BE RUN AFTER THE TAIL OPTIMIZER CALCS VALUES.
#THIS PROGRAM EXPECTS DATA THAT IS AN OUTPUT FROM THE OPTIMIZER

class PlaneMaker:
    def __init__(self, wing, tail, plane):
        
        self.wingspan = wing.span
        self.root_chord = wing.chordR
        self.tip_chord = wing.chordT
        self.MAC = (self.tip_chord + self.root_chord) / 2
        self.taper_start = wing.taper_start
        self.airfoil = wing.airfoil
        self.aileron_chord = wing.chord_percentage * self.MAC  
        #constant thickness aileron on the taper section.

        self.tailspan = tail.span / 2
        self.tail_MAC = tail.MAC
        self.tail_LE_sweep = tail.LE_sweep 
        self.tail_TE_sweep = tail.TE_sweep
        self.tail_airfoil = tail.airfoil
        self.lever_arm = tail.lever
        self.tail_dihedral_angle = tail.dihedral
        self.ruddervator_chord = tail.chord_percentage * self.tail_MAC
        self.ruddervator_deflection = tail.deflection
        
        self.tail_incidence = 0
        
        self.tail_root_chord = tail.MAC + tail.span / 2 * (np.tan(tail.LE_sweep) - np.tan(tail.TE_sweep)) / 2
        self.tail_tip_chord = tail.MAC + tail.span / 2 * (np.tan(tail.TE_sweep) - np.tan(tail.LE_sweep)) / 2

        #calculated
        self.tail_AC = (self.tailspan / 2) * np.tan(self.tail_LE_sweep) + self.tail_MAC * 0.25
        self.cg = plane.CG

        # calculate the wing AC NEED A MORE ROBUST WAY OF DOING THIS THIS IS VERY LIMITED AND NOT GOOD!!!
        self.wing_area = self.wingspan * self.taper_start * self.root_chord + (self.wingspan * (1 - self.taper_start) * (self.root_chord * self.tip_chord) / 2)
        self.wing_MAC = self.wing_area / self.wingspan   
     
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
                    chord = self.root_chord,
                    airfoil = Airfoil(self.airfoil)
                ),
                #taper start
                WingXSec (
                    xyz_le = [0, self.wingspan / 2 * self.taper_start, 0],                
                    chord = self.root_chord,
                    airfoil = Airfoil(self.airfoil),

                    control_surface_type="symmetric",
                    control_surface_deflection = 0,  # degrees
                    control_surface_hinge_point = 1 - (self.aileron_chord / self.root_chord),
                ),
                #tip 
                WingXSec (
                    xyz_le = [1.48 / 39.3701, self.wingspan / 2, 0], 
                    chord = self.tip_chord,     
                    airfoil = Airfoil(self.airfoil),
                    control_surface_type="symmetric",
                    control_surface_deflection = 0,  # degrees
                    control_surface_hinge_point = 1 - (self.aileron_chord / self.tip_chord),
                ),
            ],
            chordwise_resolution = 4,
            spanwise_resolution = 3
        )

        # ============= TAIL =============
        #this is relative to the leading edge of the tail
        tail_le = self.root_chord * 0.25 + self.lever_arm - self.tail_AC
        z_root = 0 #3.4 / 39.3701
        #this code sharts itself the second you ask for negative sweep. This is buns. I will be fixing at some point

       
        TE = self.tailspan / 2 * np.tan(self.tail_TE_sweep)

        tip = tail_le + (self.tailspan * np.tan(self.tail_LE_sweep))
        
        ruddervator = asb.ControlSurface(
            name = "ruddervator",
            symmetric = True,
            deflection = self.ruddervator_deflection,  # degrees
            hinge_point = 1 - (self.ruddervator_chord),
            trailing_edge = True,
        )
            
        tail = asb.Wing (
            name = "Tail",
            symmetric = True,
            xsecs = [
                #root
                WingXSec (
                    xyz_le = [tail_le, 0, z_root],
                    chord = self.tail_root_chord,
                    airfoil = Airfoil(self.tail_airfoil),
                    twist = self.tail_incidence,
                    control_surfaces=[ruddervator]
                ),
                #tip tail_le + (np.tan(self.tail_LE_sweep) + np.tan(self.tail_TE_sweep)) * self.tailspan,
                WingXSec (
                    xyz_le = [
                        tip,
                        self.tailspan * np.cos(self.tail_dihedral_angle), 
                        z_root + self.tailspan * np.sin(self.tail_dihedral_angle)
                    ],
                    chord = self.tail_tip_chord,
                    airfoil = Airfoil(self.tail_airfoil),
                    twist = self.tail_incidence,
                    control_surfaces=[ruddervator]
                ),
            ],
            chordwise_resolution = 4,
            spanwise_resolution = 3
        )

        airplane = asb.Airplane (
            name = "UW-26 Mako", 
            xyz_ref=[0, 0, 0],
            wings = [wing, tail],
        )

        return (airplane)