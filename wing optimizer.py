import aerosandbox as asb
import aerosandbox.numpy as np
import matplotlib.pyplot as plt
import aerosandbox.tools.pretty_plots as p

#import sys
#import os
#sys.path.append(os.path.dirname(os.path.abspath(__file__)))
#import File_Reader

#wing = File_Reader.read(r"C:\Users\noahw\Documents\DBF Coding\Tail Optimization\Parameters\Wing_Opti_Parameters.txt").load()

sexy_graphs = False

opti = asb.Opti()

#design constants
wing_airfoil = asb.Airfoil("e222")    #probably swap airfoils but I understand this one p well
weight = 1 * 9.805
cruise_speed = 10

#structure constants
outer_radius = 0.005
inner_radius = 0.004
max_g = 2
FoS = 1.5

#opti variables
span = opti.variable(init_guess = 3, upper_bound = 8, lower_bound=1)
halfspan = span / 2
alpha = 1    #opti.variable(init_guess = 1, lower_bound=0, upper_bound=5)

root_chord = opti.variable(init_guess=0.5, lower_bound=0.1, upper_bound=1)
tip_chord = opti.variable(init_guess=0.2, lower_bound=0.1, upper_bound=root_chord)
taper_location = opti.variable(init_guess=0.5, upper_bound=halfspan, lower_bound=0.1)
tip_height = 0 #opti.variable(init_guess=0.1, upper_bound=0.3)

#structure calcs
I = np.pi / 2 * (outer_radius ** 4 - inner_radius ** 4)
y = outer_radius
#root_lift = weight / (np.pi * (halfspan / 2)) * max_g * FoS #from eliptical loading eq 
centroid = 4 * (halfspan) / (3 * np.pi)
moment = (weight * max_g * FoS) / 2 * centroid
max_stress = moment * y / I

#the wing 
wing = asb.Wing(
    symmetric=True,
    xsecs=[
        asb.WingXSec(
            xyz_le=[0, 0, 0],
            chord = root_chord,
            airfoil = wing_airfoil,
        ),
        asb.WingXSec(
            xyz_le=[0,taper_location,0],
            chord = root_chord,
            airfoil=wing_airfoil,
        ),
        asb.WingXSec(
            xyz_le=[(root_chord-tip_chord) / 4, halfspan, tip_height],
            chord = tip_chord,
            airfoil = wing_airfoil,
        )
    ],
)

#this code is directly from asb tut
N = 12
section_y = np.sinspace(0, 1, N, reverse_spacing=True)
chords = opti.variable(init_guess=np.ones(N), upper_bound=np.ones(N), lower_bound=np.ones(N) * 0) 

elliptical_wing = asb.Wing(
    symmetric=True,
    xsecs=[
        asb.WingXSec(
            xyz_le=[
                -0.25 * chords[i],  # This keeps the quarter-chord-line straight.
                section_y[i],  # Our (known) span locations for each section.
                0,
            ],
            chord=chords[i],
            airfoil = wing_airfoil
        )
        for i in range(N)
    ],
)

airplane = asb.Airplane(  # Make an airplane object containing only this wing.
    wings=[elliptical_wing]
)

op_point = asb.OperatingPoint(
    velocity = cruise_speed,
    alpha = alpha,
)

buildup = asb.VortexLatticeMethod(
    airplane=airplane,
    op_point=op_point,
    spanwise_resolution=3,
    chordwise_resolution=8,
)

derivs = buildup.run_with_stability_derivatives(alpha=False, beta=True, p=False, q=False, r=False)

aero_buildup = buildup.run()

area_est = weight / (0.4 * 1.225 * (cruise_speed ** 2))

#opti.subject_to(np.diff(chords) >= -0.2)
opti.subject_to(aero_buildup["L"] == weight)        #lift requirement
opti.subject_to(wing.area() == area_est)
opti.subject_to(max_stress < 60e6)                  #structure calcs 
#opti.subject_to(elliptical_wing.aspect_ratio(type="geometric") >= 4)
#opti.subject_to(aero_vlm["CD"] > 0)                #minimize CD

#roll stability requirement
#opti.subject_to(derivs["Clb"] <= -0.04)
opti.minimize(aero_buildup["D"] + 0.05 * np.sum(np.diff(chords, n=2)**2))
opti.subject_to(np.diff(chords) <= 0)  #chord can't increase

sol = opti.solve()

aero_buildup = sol(aero_buildup)
sol(buildup).draw()

print(f"wing_area: ", sol.value(wing.area()))
print(f"est area: ", area_est)
print(f"lift: ", sol.value(aero_buildup["L"]))
print(f"drag: ", sol.value(aero_buildup["D"]))
print(f"span: ", sol.value(span))
print(f"max stress: ", sol.value(max_stress))

#sol(airplane).draw()

avl = asb.AVL(
    verbose=True,
    airplane=sol(airplane),
    op_point=asb.OperatingPoint(
        velocity=10, # m/s
        alpha=0, # deg
        beta=0, # deg
        p=0, # rad/sec
        q=0, # rad/sec
        r=0, # rad/sec
    ),
    avl_command = r"c:/Users/noahw/Downloads/avl.exe"
)

#avl.open_interactive()
#outputs = avl.run()
#avl.write_avl(filepath=r"C:\Users\noahw\Documents\DBF Coding\Tail Optimization\avlfiles\plane.avl")

#print(f"AVL CL: ", outputs['CL'])
