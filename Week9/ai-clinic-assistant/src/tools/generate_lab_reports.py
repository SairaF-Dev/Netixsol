"""
Generates 30 synthetic lab report files in data/lab_reports/ for testing the Lab Report Understanding Pipeline.
Panels included: CBC, Diabetes, LFT, Renal Profile, Lipid Profile.
"""

import os
import random

LAB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "lab_reports")

PATIENTS = [
    ("PAT-0012", "Tariq Mahmood", 45, "Male"),
    ("PAT-0042", "Ayesha Khan", 34, "Female"),
    ("PAT-0089", "Muhammad Usman", 52, "Male"),
    ("PAT-0115", "Fatima Zahra", 29, "Female"),
    ("PAT-0164", "Bilal Ahmed", 61, "Male"),
    ("PAT-0201", "Sana Malik", 38, "Female"),
]

PANELS = [
    {
        "name": "Complete Blood Count (CBC)",
        "tests": [
            ("Hemoglobin", 13.5, 17.5, "g/dL", 9.5, 18.5),
            ("WBC Count", 4.5, 11.0, "x10^3/uL", 3.2, 14.5),
            ("Platelet Count", 150, 450, "x10^3/uL", 110, 480),
        ]
    },
    {
        "name": "Diabetes Panel",
        "tests": [
            ("Fasting Blood Sugar", 70, 99, "mg/dL", 60, 185),
            ("HbA1c", 4.0, 5.6, "%", 5.2, 9.1),
        ]
    },
    {
        "name": "Liver Function Tests (LFT)",
        "tests": [
            ("ALT (SGPT)", 7, 56, "U/L", 25, 95),
            ("AST (SGOT)", 10, 40, "U/L", 18, 75),
            ("Serum Bilirubin", 0.3, 1.2, "mg/dL", 0.5, 2.8),
        ]
    },
    {
        "name": "Renal Function Profile",
        "tests": [
            ("Serum Creatinine", 0.7, 1.3, "mg/dL", 0.8, 2.4),
            ("Blood Urea", 7, 20, "mg/dL", 12, 45),
        ]
    },
    {
        "name": "Lipid Profile",
        "tests": [
            ("Total Cholesterol", 125, 200, "mg/dL", 140, 260),
            ("Triglycerides", 50, 150, "mg/dL", 90, 220),
            ("HDL Cholesterol", 40, 60, "mg/dL", 32, 55),
        ]
    }
]

def generate_reports():
    os.makedirs(LAB_DIR, exist_ok=True)
    report_num = 1

    for p_id, p_name, p_age, p_gender in PATIENTS:
        for panel in PANELS:
            file_path = os.path.join(LAB_DIR, f"lab_report_{report_num:02d}.txt")
            
            lines = []
            lines.append("=========================================================")
            lines.append("           CITY CARE CLINICS - LAB REPORT                ")
            lines.append("=========================================================")
            lines.append(f"Patient ID   : {p_id}")
            lines.append(f"Patient Name : {p_name}")
            lines.append(f"Age / Gender : {p_age} / {p_gender}")
            lines.append(f"Test Panel   : {panel['name']}")
            lines.append(f"Report Date  : 2026-10-0{random.randint(1,6)}")
            lines.append("---------------------------------------------------------")
            lines.append(f"{'TEST NAME':<22} {'RESULT':<10} {'UNIT':<10} {'REFERENCE RANGE':<15}")
            lines.append("---------------------------------------------------------")

            for t_name, ref_min, ref_max, unit, val_min, val_max in panel["tests"]:
                # 40% abnormal chance
                if random.random() < 0.4:
                    val = round(random.choice([random.uniform(val_min, ref_min - 0.5), random.uniform(ref_max + 0.5, val_max)]), 1)
                else:
                    val = round(random.uniform(ref_min, ref_max), 1)

                lines.append(f"{t_name:<22} {val:<10} {unit:<10} {ref_min} - {ref_max}")

            lines.append("---------------------------------------------------------")
            lines.append("Status: Final Verified by Pathologist")
            lines.append("=========================================================")

            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            report_num += 1

    print(f"Generated {report_num - 1} synthetic lab reports in {LAB_DIR}")

if __name__ == "__main__":
    generate_reports()

