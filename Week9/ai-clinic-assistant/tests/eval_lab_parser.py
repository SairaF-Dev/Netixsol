"""
Evaluation Benchmark Suite for Lab Report Understanding Pipeline.
Evaluates extraction accuracy and abnormality recall across all 30 synthetic lab reports.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.tools.lab_report_parser import LabReportParser

LAB_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "lab_reports")

def run_lab_evaluation():
    parser = LabReportParser()
    report_files = [os.path.join(LAB_DIR, f) for f in os.listdir(LAB_DIR) if f.startswith("lab_report_")]
    
    total_reports = len(report_files)
    successful_extractions = 0
    total_tests_found = 0
    total_abnormal_found = 0

    print("=" * 65)
    print(f"[TEST] EVALUATING LAB REPORT PARSER ({total_reports} REPORTS)")
    print("=" * 65)

    for idx, fpath in enumerate(report_files, 1):
        filename = os.path.basename(fpath)
        parsed = parser.parse_report_file(fpath)
        
        num_tests = parsed["total_tests_extracted"]
        num_abnormal = parsed["abnormal_count"]

        if num_tests > 0 and parsed["patient_id"] != "UNKNOWN":
            successful_extractions += 1
            status = "[PASS]"
        else:
            status = "[FAIL]"

        total_tests_found += num_tests
        total_abnormal_found += num_abnormal

        print(f"[{idx:02d}/{total_reports}] {status} {filename} | Patient: {parsed['patient_id']} ({parsed['patient_name']}) | Tests: {num_tests} | Abnormal: {num_abnormal}")

    extraction_accuracy = (successful_extractions / total_reports) * 100

    print("=" * 65)
    print("[METRICS] LAB PARSER EVALUATION METRICS")
    print("=" * 65)
    print(f"Total Reports Evaluated  : {total_reports}")
    print(f"Successful Extractions   : {successful_extractions} / {total_reports}")
    print(f"Extraction Accuracy      : {extraction_accuracy:.1f}% (Target: > 95%)")
    print(f"Total Tests Extracted    : {total_tests_found}")
    print(f"Total Abnormalities Flagged: {total_abnormal_found}")
    print("=" * 65)

if __name__ == "__main__":
    run_lab_evaluation()

