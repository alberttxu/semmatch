import numpy as np
from scipy.optimize import curve_fit


def sin_deg(angle, a, b, phase):
    return a * np.sin((angle + phase) * np.pi / 180) + b


def getZparams(angles, defoci):
    params, covariance = curve_fit(sin_deg, angles, defoci)
    return params


def getStageYparams(angles, shifts):
    degree_fit = 3
    params = np.polyfit(angles, shifts, degree_fit)
    return params


def createFakeAutodoc(outputfile, newLabel, params):
    fake_nav_pts = []
    for i, param in enumerate(params):
        label = newLabel + i
        fake_nav_pt = "\n".join(
            [
                f"[Item = {label}]",
                "Color = 0",
                "NumPts = 1",
                "Regis = 1",
                "Type = 0",
                "PtsX = 0",
                f"PtsY = {i}",
                f"StageXYZ = 0 {i} 0",
                f"Note = {param}",
            ]
        )
        fake_nav_pts.append(fake_nav_pt)

    with open(outputfile, "w") as f:
        print(f"writing output to {outputfile}")
        f.write("AdocVersion = 2.00\n\n" + "\n\n".join(fake_nav_pts))
