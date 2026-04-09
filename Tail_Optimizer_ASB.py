import aerosandbox as asb
import aerosandbox.numpy as np
from scipy.optimize import minimize
from scipy import integrate
import matplotlib.pyplot as plt
import aerosandbox.tools.pretty_plots as p

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import File_Reader
from Plane_Constructor import PlaneMaker


# Features/Assumptions and stuff
#   AC of all airfoils is 0.25 chord 
#   V-tail only (for now)
#   Unitless
#   Coordinate System:
#       Typical XYZ system (x is lengthwise, y is spanwise, z is vertical)
#       LE of wing is x = 0 increases as you move back to the tail

# ============== output toggles ==============
graphs 			    = True
three_view 		    = True
single_view 		= False
numerical_outputs 	= True
XFLR5_outputs 		= False
imperial_units 		= False
solidworks_export 	= True
GUI                 = False

# ============== inputs from .txt files ==============

FILES = {
    "Tail":  r"C:\Users\noahw\Documents\DBF Coding\Tail Optimization\Parameters\Testing\Tail_Input_Parameters_test.txt",
    "Wing":  r"C:\Users\noahw\Documents\DBF Coding\Tail Optimization\Parameters\Testing\Wing_Input_Parameters_test.txt",
    "Plane": r"C:\Users\noahw\Documents\DBF Coding\Tail Optimization\Parameters\Testing\Plane_Input_Parameters_test.txt",
    "Mass":  r"C:\Users\noahw\Documents\DBF Coding\Tail Optimization\Parameters\Testing\Mass_Input_Parameters_test.txt"
}

if GUI:
    File_Reader.show_launcher(FILES)

tail = File_Reader.read(FILES["Tail"]).load()
wing = File_Reader.read(FILES["Wing"]).load()
plane = File_Reader.read(FILES["Plane"]).load()
density = File_Reader.read(FILES["Mass"]).load()

# ============== setup equations ==============

def d2r(input):
    return (input * np.pi / 180)

def r2d(input):
    return (input * 180 / np.pi)

def pyramid_surface_area(l, w, h):
    return (l * w + l * np.sqrt((w / 2) ** 2 + h ** 2) + w * np.sqrt((l / 2) ** 2 + h ** 2))

# ============== setup values =============

tail.cl_av = 0.4
plane.NP = plane.SM + plane.CG
wing.AR = wing.span / wing.MAC
wing.area = wing.MAC * wing.span
#tail.LE_sweep = tail.LE_sweep * (np.pi / 180)   #conversion to rads
#tail.TE_sweep = tail.TE_sweep * (np.pi / 180)
#wing.QC_sweep = 0.75 * np.tan(wing.LE_sweep) + 0.25 * np.tan(wing.TE_sweep)

def simple_weight_buildup(plane, tail):
    tail.chordR = tail.MAC + tail.span / 2 * (np.tan(tail.LE_sweep) - np.tan(tail.TE_sweep)) / 2
    
    empennage_mass = tail.lever * plane.lever_density  
    surface_mass = tail.MAC * tail.span * plane.surface_density
    mount_mass = (tail.chordR - tail.chord_percentage) * plane.mount_density 
    
    return(empennage_mass + surface_mass + mount_mass)

def weight_buildup(plane, tail):
    
    # empennage 
    
    angle = np.arctan((tail.lever - plane.taper_start) / (plane.fuse_height - plane.end_height))
    
    empennage_area = pyramid_surface_area((tail.lever - plane.taper_start + plane.end_height * np.tan(angle)), plane.fuse_width, plane.fuse_height) 
    - pyramid_surface_area(plane.end_height * np.tan(angle), plane.end_width, plane.end_height) + (plane.end_width * plane.end_height)
    empennage_mass = empennage_area * density.fuse * 1.1 #jb weld factor lmao
    
    #tail itself     
    #airfoil arclength / chord * chord * span 
    surface_area = (18.46 / 9.16) * tail.MAC * tail.span
    #airfoil avg thickness / chord * chord * chord = base surface area
    volume = (0.05369862 * tail.MAC ** 2) * (((tail.span / np.cos(tail.LE_sweep)) + tail.span / np.cos(tail.TE_sweep)) / 2)
    mount_tape_area = tail.chordR * (1 - tail.chord_percentage) * (3 / 14.36) * tail.span * 2 #should account for JB weld

    foam_mass = volume * density.foam
    layup_mass = (surface_area + mount_tape_area) * density.fiberglass
    weight = (empennage_mass + layup_mass + foam_mass) * 9.805
    
    return (weight)

def analyze_sandwich_tail(
    span, 
    chord_root,
    chord_tip,
    airfoil_thickness_ratio,
    max_load_force,
    skin_thickness,
    material_type,
    mos_target_min,
    mos_target_max,
    advanced_output,
):
    
    if material_type == "carbon":
        E_skin = 199e6
        ultimate_strain = 0.04270
        Sigma_ultimate = E_skin * ultimate_strain
    else:
        E_skin = 68.5e6
        ultimate_strain = 0.03970
        Sigma_ultimate = E_skin * ultimate_strain

    E_foam = 35e6 #elastic modulus
    Tau_ultimate_foam = 0.8e6   #shear max
    safety_factor = 1.5

    y = np.linspace(0, span, 50)
    chord = chord_root + (chord_tip - chord_root) * (y / span)
    t_airfoil = chord * airfoil_thickness_ratio
    t_core = np.maximum(t_airfoil - 2 * skin_thickness, 0)
    c_core = np.maximum(chord - 2 * skin_thickness, 0)

    # Section Properties
    I_outer = 0.036 * (t_airfoil ** 3) * chord
    I_inner = 0.036 * (t_core ** 3) * c_core
    I_skin = I_outer - I_inner
    I_core = I_inner
    EI_total = (E_skin * I_skin) + (E_foam * I_core)

    # Load Distribution (Elliptical)
    q_load = max_load_force * (4 / (np.pi * span)) * np.sqrt(1 - (y / span) ** 2)

    # Integration (Cantilever)
    shear_force = integrate.cumulative_trapezoid(q_load[::-1], y[::-1], initial=0)[::-1]
    shear_force = np.abs(shear_force)
    moment = integrate.cumulative_trapezoid(shear_force[::-1], y[::-1], initial=0)[::-1]
    moment = np.abs(moment)
    curvature = moment / EI_total
    slope = integrate.cumulative_trapezoid(curvature, y, initial=0)
    deflection = integrate.cumulative_trapezoid(slope, y, initial=0)

    # Stress Analysis
    c_dist = t_airfoil / 2
    stress_skin = (moment * c_dist * E_skin) / EI_total
    area_core = t_core * chord
    stress_shear_core = shear_force / area_core

    # Margins of Safety
    max_skin_stress = np.max(stress_skin)
    max_core_shear = np.max(stress_shear_core)
    MoS_skin = (Sigma_ultimate / (max_skin_stress * safety_factor)) - 1
    MoS_core = (Tau_ultimate_foam / (max_core_shear * safety_factor)) - 1

    # Only check bending stress MoS against target window (ignore shear)
    mos_ok = (MoS_skin >= mos_target_min)
    mos_overbuilt = (MoS_skin > mos_target_max)
    
    if advanced_output:
        return {
            "Max Skin Stress (MPa)": max_skin_stress / 1e6,
            "Max Core Shear (MPa)": max_core_shear / 1e6,
            "Tip Deflection (mm)": deflection[-1] * 1000,
            "MoS (Skin Bending)": MoS_skin,
            "MoS (Core Shear)": MoS_core,
            "Meets MoS Window (0.4-1.0)": mos_ok and not mos_overbuilt,
            "Below Min MoS": not mos_ok,
            "Overbuilt (MoS>1)": mos_overbuilt,
        }
    else:
        return {
            "Meets Margin of Safety (MoS) Window (0.4-1.0)": mos_ok and not mos_overbuilt,
            "Below Min MoS": not mos_ok,
            "Overbuilt (MoS>1)": mos_overbuilt,
        }

def tail_sizing(tail, plane, opti):
    tail.lever = 19 / 39.3701 #opti.variable(init_guess = (plane.lever_min + plane.lever_max) / 2, scale = 0.5, lower_bound = plane.lever_min, upper_bound=plane.lever_max)
    tail.dihedral = opti.variable(init_guess = d2r(45), scale = d2r(1), upper_bound = d2r(90))
    
    tail.MAC = opti.variable(init_guess = (10 / 39.3701), scale = (1 / 39.3701), lower_bound = (3 / 39.3701), upper_bound = (15 / 39.3701))
    #tail.span = opti.variable(init_guess = (30 / 39.3701), lower_bound = (10 / 39.3701), upper_bound = (50 / 39.3701))
    tail.AR = 4 #opti.variable(init_guess = 3, lower_bound = 1, upper_bound = 4) NEED TO GET STRUCTURE CALCS I CAN DO THIS BC CEE220 GOATED
    tail.span = tail.MAC * tail.AR

    tail.LE_sweep = d2r(15) #opti.variable(init_guess = d2r(10), scale = d2r(1), lower_bound = 0, upper_bound = d2r(45))
    #tail.TE_sweep = opti.variable(init_guess = d2r(0), scale = d2r(1), lower_bound = d2r(-10), upper_bound = d2r(25))
    tail.TE_sweep = 0
    #replace this with taper ratio probably. Then pick the appropriete sweep angle? Or just remove TE which would do the same thing??

    tail.chordR = tail.MAC + tail.span / 2 * (np.tan(tail.LE_sweep) - np.tan(tail.TE_sweep)) / 2
    tail.chordT = tail.MAC + tail.span / 2 * (np.tan(tail.TE_sweep) - np.tan(tail.LE_sweep)) / 2

#  ============= minimized function =============

opti = asb.Opti()

tail_sizing(tail, plane, opti)

tail.deflection = 0 #opti.variable(init_guess = 0, scale = 1, upper_bound = 5, lower_bound = -5)
deflection_map = {"ruddervator": tail.deflection}

maker = PlaneMaker(wing, tail, plane)
airplane = maker.MakePlane()    #.with_control_deflections(deflection_map)

#drag calcs     !!! THIS NEEDS WORK !!! the aero buildup can spit out better data
frontal_area = tail.span * tail.MAC * 0.08
cd_i = (tail.cl_av ** 2) / (np.pi * tail.AR * 0.8)     #0.8 is tail oswald efficieny factor; should calc this
cd_0 = 0.0047                                          # tail cd at alpha = 0
drag = 0.5 * (1.225) * frontal_area * (cd_0 + cd_i) * (plane.speed ** 2)

vlm = asb.VortexLatticeMethod(
    airplane = airplane,
    op_point = asb.OperatingPoint(velocity=plane.speed, alpha = plane.cruise_alpha), #make cl match weight
    #align_trailing_vortices_with_wind=False,
)

buildup = asb.AeroBuildup(
    airplane = airplane,
    op_point = asb.OperatingPoint(velocity = plane.speed, alpha = plane.cruise_alpha),
)

derivs = vlm.run_with_stability_derivatives(alpha=True, beta=True, p=False, q=False, r=False)

#stability requirements

opti.subject_to(derivs["x_np"] == (0.25 + 0.20) * wing.MAC) #remove static margin requirement? Just add in all the dynamic requirements
opti.subject_to(derivs["Cnb"] >= 0.125)
opti.subject_to(derivs["Cma"] <= -0.9)

aero_VLM = vlm.run()
aero_buildup = buildup.run()

factor = simple_weight_buildup(plane, tail) + drag / plane.WD_tradeoff

opti.minimize(factor)
try:
    sol = opti.solve()
except Exception as e:
    print("\n--- OPTIMIZATION FAILED. PRINTING DEBUG VALUES ---")
    
    # Print out your design variables to see if they slammed into a bound
    print(f"Last Tail Area guess: {opti.debug.value(tail.span * tail.MAC)} m^2")
    print(f"Last Tail Moment Arm guess: {opti.debug.value(tail.lever)} m")
    
    # Print out your constraints to see which one is violating your rules
    print(f"Last Cma guess: {opti.debug.value(derivs['Cma'])}")
    print(f"Last Cnb guess: {opti.debug.value(derivs['Cnb'])}")
    print(f"Last SM guess: {opti.debug.value(derivs['x_np'])}")

# ============= final sizing calcs =============

tail.control_offset = sol.value(tail.chord_percentage * tail.MAC)
#this converts all the optimization variables back into real numbers.
def value_conversion(tail): 
    
    tail.MAC = sol.value(tail.MAC)
    tail.span = sol.value(tail.span)

    tail.area = tail.MAC * tail.span
    
    tail.LE_sweep = sol.value(tail.LE_sweep)
    tail.TE_sweep = sol.value(tail.TE_sweep)
    
    tail.chordR = tail.MAC + tail.span / 2 * (np.tan(tail.LE_sweep) - np.tan(tail.TE_sweep)) / 2
    tail.chordT = tail.MAC + tail.span / 2 * (np.tan(tail.TE_sweep) - np.tan(tail.LE_sweep)) / 2

    tail.dihedral = sol.value(tail.dihedral)
    tail.lever = sol.value(tail.lever)
    tail.deflection = sol.value(tail.deflection)

value_conversion(tail)

#cool outputs

maker = PlaneMaker(wing, tail, plane)
airplane = maker.MakePlane()

vlm = sol(vlm)

#vlm.draw()

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

aero = asb.AeroBuildup(
    airplane = airplane,
    op_point = asb.OperatingPoint(
        velocity = plane.speed,
        alpha = alpha_range,
    ),
).run()

if graphs:
    aero_graphs(aero, alpha_range)
    
if imperial_units:
    conversion = 39.3701
    symbol = "in"
else:
    conversion = 1
    symbol = "m"    

if three_view:
    airplane.draw_three_view()

if single_view:
    airplane.draw(show = True)

if numerical_outputs:
    rows = [
        (f"Lever arm ({symbol}):", tail.lever * conversion),
        (f"Area ({symbol}^2):", tail.area * conversion ** 2),
        (f"Dihedral (deg):", tail.dihedral * 180 / np.pi),
        (f"Tail MAC ({symbol}):", tail.MAC * conversion),
        (f"Tail AR ({symbol}):", tail.AR),
        (f"Span ({symbol}):", tail.span * conversion),
        (f"Root Chord ({symbol}):", tail.chordR * conversion),
        (f"Tip Chord ({symbol})", tail.chordT * conversion),
        (f"TE sweep (deg):", r2d(tail.TE_sweep)),
        (f"LE sweep (deg):", r2d(tail.LE_sweep)),
    ]
        
    print("================ Results (per side) ================"),
    for label, value in rows:
        print(f"{label:<35} {sol.value(value):>12.4f}")

if solidworks_export:
    with open("C:/Users/noahw/Documents/DBF Coding/Tail Optimization/Tail CAD/TailEq.txt", "w") as f:
        f.write(f"\"root_chord\"= {(tail.chordR):.4f}m\n")
        f.write(f"\"tip_chord\"= {(tail.chordT):.4f}m\n")
        f.write(f"\"span\"= {(tail.span) / 2:.4f}m\n")
        f.write(f"\"end_width\"= {plane.end_width}m\n")
        f.write(f"\"end_height\"= {plane.end_height}m\n")
        f.write(f"\"fillet_radius\"= {plane.fillet_radius}in\n")

        #need someone who CADs to help me figure out if I can just remove these and put them in some other folder
        f.write(f"\"D1@Boom Sketch\"= \"end_height\"\n")
        f.write(f"\"D2@Boom Sketch\"= \"end_width\"\n")
        f.write(f"\"D3@Boom Sketch\"= \"fillet_radius\"\n")

        f.write(f"\"dihedral_angle\"= {(r2d(tail.dihedral)):.4f}deg\n")
        f.write(f"\"D4@Boom Sketch\"= \"dihedral_angle\"\n")

        f.write(f"\"D1@Root Chord\"= \"root_chord\"\n")
        f.write(f"\"D5@Boom Sketch\"= \"span\"\n")
        f.write(f"\"D1@Tip Chord\"= \"tip_chord\"\n")
        f.write(f"\"D1@Root Chord Line\"= \"root_chord\"\n")

        f.write(f"\"LE_sweep\"= {tail.LE_sweep * (180 / np.pi)}deg\n")
        f.write(f"\"TE_sweep\"= {tail.TE_sweep * (180 / np.pi)}deg\n")
        f.write(f"\"control_offset\"= {tail.control_offset:.4f}m\n")
        
        f.write(f"\"D1@Loft Guides\"= \"LE_sweep\"\n")
        f.write(f"\"D2@Loft Guides\"= \"TE_sweep\"\n")
        f.write(f"\"D1@Hinge Line\"= \"control_offset\"\n")

        print()
        print("Solidworks equations file created")
