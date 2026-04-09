import aerosandbox as asb
import aerosandbox.numpy as np
import matplotlib.pyplot as plt
import aerosandbox.tools.pretty_plots as p

opti = asb.Opti()

#tools
def d2r(input):
    return (input * np.pi / 180)

def r2d(input):
    return (input * 180 / np.pi)

#super basic weight buildup do NOT use this for final
def simple_weight_buildup(lever, lever_density, wing_area, wing_MAC, wing_density, tail_area, tail_MAC, tail_density): 
    fuse_mass = 0.5
    lever_mass = lever * lever_density 
    tail_surface_mass = tail_area * tail_density * 0.07 * tail_MAC
    wing_mass = wing_area * wing_density * 0.07 * wing_MAC
    
    return(lever_mass + tail_surface_mass + fuse_mass + wing_mass)

#opti variables
span = opti.variable(init_guess = 3, upper_bound = 8, lower_bound=1)
halfspan = span / 2 

#wing parameter
root_chord = opti.variable(init_guess=0.5, lower_bound=0.1, upper_bound=1)
tip_chord = opti.variable(init_guess=0.2, lower_bound=0.1, upper_bound=root_chord)
taper_location = opti.variable(init_guess=0.9, upper_bound=halfspan, lower_bound=0)
tip_height = 0 #opti.variable(init_guess=0.1, upper_bound=0.3)
wing_area = root_chord * (taper_location) + (root_chord + tip_chord) / 2 * (span - taper_location)
MAC = wing_area / span

#tail parameters
tail_chord = opti.variable(init_guess = 0.1, upper_bound = 0.5)
tail_span = tail_chord * 2
tail_area = tail_chord * tail_span
tail_dihedral = opti.variable(init_guess = d2r(40), upper_bound=d2r(60), lower_bound=d2r(30))

#empennage parameters
lever_arm = 1 #opti.variable(init_guess=1, upper_bound=1.5, lower_bound=0.5)

#design constants
wing_airfoil = asb.Airfoil("e222")    #probably swap airfoils but I understand this one p well
tail_airfoil = asb.Airfoil("naca0010")
cruise_speed = 10
alpha = 0 #opti.variable(init_guess=1, lower_bound=0, upper_bound=5)

#plane components
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
N = 6
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

tail = asb.Wing (
    symmetric = True,
    xsecs = [
        #root
        asb.WingXSec (
            xyz_le = [lever_arm - tail_chord / 4, 0, 0],
            chord = tail_chord,
            airfoil = tail_airfoil,
        ),
        asb.WingXSec (
            xyz_le = [
                lever_arm - tail_chord / 4,
                tail_span * np.cos(tail_dihedral), 
                tail_span * np.sin(tail_dihedral),
            ],
            chord = tail_chord,
            airfoil = tail_airfoil,
        ),
    ],
)

weight = 10 #simple_weight_buildup(lever_arm, 0.01, wing_area, wing_area / wing.span(), 0.01, tail_area, tail_chord, 0.01) * .009805

#structure constants
outer_radius = 0.005
inner_radius = 0.004
max_g = 2
FoS = 1.5

#wing structure calcs
I = np.pi / 2 * (outer_radius ** 4 - inner_radius ** 4)
y = outer_radius
centroid = 4 * (halfspan) / (3 * np.pi)
moment = (weight * max_g * FoS) / 2 * centroid
max_stress = moment * y / I

airplane = asb.Airplane(
    wings=[elliptical_wing, tail],
    xyz_ref=[0, 0, 0],
    name = "lil jit",
)

op_point = asb.OperatingPoint(
    velocity = cruise_speed,
    alpha = alpha,
)

buildup = asb.AeroBuildup(
    airplane=airplane,
    op_point=op_point,
    #spanwise_resolution=3,
    #chordwise_resolution=4,
    #verbose=False,
)

derivs = buildup.run_with_stability_derivatives(alpha=True, beta=True, p=False, q=False, r=False)

aero_buildup = buildup.run()

area_est = weight / (0.4 * 1.225 * (cruise_speed ** 2))

opti.subject_to(aero_buildup["L"] == weight)        #lift requirement
opti.subject_to(max_stress <= 60e7)                 #structure calcs
opti.subject_to(wing.area() == area_est) 

#stability requirements
opti.subject_to(derivs["x_np"] == (0.25 + 0.15) * (MAC))
opti.subject_to(derivs["Cnb"] <= 0.15)
opti.subject_to(derivs["Cnb"] >= 0.09)
opti.subject_to(derivs["Cma"] <= -0.9)
    
opti.minimize(aero_buildup["D"] + 0.05 * np.sum(np.diff(chords, n=2)**2))
opti.subject_to(np.diff(chords) <= 0)  #chord can't increase

sol = opti.solve()

print(f"wing_area: ", sol.value(wing.area()))
print(sol(wing_area))
print(f"tail area: ", sol(tail_area))
print(f"dihedral: ", r2d(sol(tail_dihedral)))
print(f"span: ", sol.value(span))
print(f"neutral point: ", sol(derivs["x_np"]))
print(f"mac: ", MAC)
print(f"Cnb: ", sol(derivs["Cnb"]))
print(f"Cma: ", sol(derivs["Cma"]))

sol(buildup).draw()
sol(airplane).draw()

#need to rerun with different buildup to get all the alphas
def aero_graphs(aero, alpha):
    fig, ax = plt.subplots(2, 2)

    plt.sca(ax[0, 0])
    plt.plot(alpha, aero["CL"])
    plt.xlabel(r"$\alpha$ [deg]")
    plt.ylabel(r"$C_L$")
    p.set_ticks(5, 1, 0.5, 0.1)

    plt.sca(ax[0, 1])
    plt.plot(alpha, aero["CD"])
    plt.xlabel(r"$\alpha$ [deg]")
    plt.ylabel(r"$C_D$")
    p.set_ticks(5, 1, 0.05, 0.01)
    plt.ylim(bottom=0)

    plt.sca(ax[1, 0])
    plt.plot(alpha, aero["Cm"])
    plt.xlabel(r"$\alpha$ [deg]")
    plt.ylabel(r"$C_m$")
    p.set_ticks(5, 1, 0.5, 0.1)

    plt.sca(ax[1, 1])
    plt.plot(alpha, aero["CL"] / aero["CD"])
    plt.xlabel(r"$\alpha$ [deg]")
    plt.ylabel(r"$C_L/C_D$")
    p.set_ticks(5, 1, 10, 2)

    p.show_plot("Aircraft Aerodynamics")

alpha_range = np.linspace(-20, 20, 80)   
new_buildup = asb.AeroBuildup(
    airplane=airplane,
    op_point=asb.OperatingPoint(
        velocity = cruise_speed,
        alpha = alpha_range,
    )
)

#aero_graphs(sol(new_buildup.run()), alpha_range)

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