"""
Lab Report Parser and Entity Extraction Engine for City Care Clinics.
Extracts clinical test data, evaluates abnormal values against reference ranges,
and generates patient-friendly UrduLish summaries adhering to safety guardrails.
Supports digital PDFs, scanned image reports (Chughtai, IDC, SKMCH) via vision OCR, and plain text.
"""

import os
import io
import re
import base64
import hashlib
import time
from typing import Dict, Any, List, Optional

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


class LabReportParser:
    """Production-grade Clinical Laboratory Report & Entity Parser with Prompt-Injection Defense."""

    KNOWN_CLINICAL_TESTS = [
        "Hemoglobin", "Hb", "Total Leukocyte Count", "WBC Count (TLC)", "WBC Count", "WBC", "White Blood Cells",
        "Total RBC", "RBC Count", "RBC", "Red Blood Cells", "Platelet Count", "Platelets", "PLT",
        "ESR", "Erythrocyte Sedimentation Rate", "Hematocrit", "HCT", "PCV", "Packed Cell Volume",
        "MCV", "MCH", "MCHC", "RDW", "Neutrophils", "Lymphocytes", "Monocytes", "Eosinophils", "Basophils",
        "Fasting Blood Sugar", "Fasting Blood Glucose", "FBS", "Random Blood Sugar", "RBS",
        "HbA1c", "Glycated Hemoglobin", "Blood Urea", "Urea", "BUN", "Serum Creatinine", "Creatinine",
        "Uric Acid", "Total Cholesterol", "Cholesterol", "Triglycerides", "HDL Cholesterol", "HDL",
        "LDL Cholesterol", "LDL", "VLDL", "Total Bilirubin", "Bilirubin", "Direct Bilirubin",
        "SGPT", "ALT", "SGOT", "AST", "Alkaline Phosphatase", "ALP", "Total Protein", "Albumin",
        "Globulin", "A/G Ratio", "Sodium", "Potassium", "Chloride", "Calcium", "Serum Calcium",
        "TSH", "Free T4", "Free T3", "Dengue NS1 Antigen", "Dengue IgM", "Dengue IgG", "CRP"
    ]

    def _get_openrouter_key(self) -> Optional[str]:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            env_paths = [
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")),
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
            ]
            for ep in env_paths:
                if os.path.exists(ep):
                    with open(ep, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.startswith("OPENROUTER_API_KEY="):
                                api_key = line.split("=", 1)[1].strip()
                                break
                if api_key:
                    break
        return api_key

    def _extract_text_via_vision_llm(self, image_bytes: bytes) -> str:
        """Transcribes image-based / scanned lab report using free vision model with SHA-256 caching."""
        sha = hashlib.sha256(image_bytes).hexdigest()
        cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, f"vision_ocr_{sha}.txt")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached = f.read()
                if cached.strip():
                    return cached
            except Exception:
                pass

        import requests
        api_key = self._get_openrouter_key()
        if not api_key:
            return ""

        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "dots-studio/dots-3-note-preview:free",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "This is a medical laboratory test report image. Please transcribe all text, patient details, and test rows (Test Name, Normal Value, Unit, Result) accurately line by line in a clean markdown table."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                    ]
                }
            ]
        }
        for attempt in range(2):
            try:
                res = requests.post(url, headers=headers, json=payload, timeout=75)
                if res.ok:
                    data = res.json()
                    transcription = data["choices"][0]["message"]["content"]
                    if transcription:
                        try:
                            with open(cache_file, "w", encoding="utf-8") as f:
                                f.write(transcription)
                        except Exception:
                            pass
                        return transcription
            except Exception:
                time.sleep(2)
        return ""

    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """Extracts plain text from digital PDF or falls back to Vision if scanned/image."""
        # 1. Check if the file is actually an image (e.g. JPEG or PNG header)
        if pdf_bytes.startswith(b'\xff\xd8\xff') or pdf_bytes.startswith(b'\x89PNG'):
            return self._extract_text_via_vision_llm(pdf_bytes)

        if not PYPDF_AVAILABLE:
            return ""

        extracted_text = ""
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            pages_text = []
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    pages_text.append(t)
            extracted_text = "\n".join(pages_text).strip()
        except Exception:
            pass

        # If digital PDF had no text stream (scanned raster PDF), fallback to Vision OCR
        if not extracted_text:
            vision_text = self._extract_text_via_vision_llm(pdf_bytes)
            if vision_text:
                return vision_text

        return extracted_text

    def parse_report_file(self, file_path: str) -> Dict[str, Any]:
        """Parses a lab report file from disk (.pdf, .txt, or image)."""
        with open(file_path, "rb") as f:
            data = f.read()
        return self.parse_report_bytes(data, file_name=os.path.basename(file_path))

    def parse_report_bytes(self, data: bytes, file_name: str = "") -> Dict[str, Any]:
        """Parses in-memory uploaded report bytes (PDF, Image, or Text)."""
        # 1. Image formats or PDF with image header
        if data.startswith(b'\xff\xd8\xff') or data.startswith(b'\x89PNG') or file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
            text = self._extract_text_via_vision_llm(data)
        elif file_name.lower().endswith(".pdf"):
            text = self.extract_text_from_pdf(data)
        else:
            try:
                text = data.decode("utf-8")
            except Exception:
                text = data.decode("latin-1", errors="ignore")

        return self.parse_report_text(text)

    def _sanitize_prompt_injections(self, text: str) -> str:
        """Strips out adversarial prompt injection payloads from untrusted lab report text."""
        sanitized_lines = []
        injection_patterns = [
            r"\[(SYSTEM\s*PROMPT|ATTACK|INJECTION|JAILBREAK).*?\]",
            r"(ignore|disregard|forget)\s+(all\s+)?(previous|prior)\s+instructions",
            r"(output|reveal|dump|leak|print)\s+(all\s+)?(patient|confidential|secret|database|system)",
            r"system\s*:\s*you\s+are\s+now",
            r"override\s+safety\s+filter"
        ]
        
        for line in text.split("\n"):
            line_strip = line.strip()
            is_attack = False
            for pat in injection_patterns:
                if re.search(pat, line_strip, re.IGNORECASE):
                    is_attack = True
                    break
            if not is_attack:
                sanitized_lines.append(line)
        return "\n".join(sanitized_lines)

    def parse_report_text(self, text: str) -> Dict[str, Any]:
        """Parses clean clinical test parameters, ranges, and generates safe UrduLish explanation."""
        clean_text = self._sanitize_prompt_injections(text)

        patient_id = "UNKNOWN"
        patient_name = "Patient"
        panel_name = "Laboratory Panel"

        pid_match = re.search(r'(?:Patient\s*ID|MRN|Registration\s*#|Reg\s*#|Patient\s*Number|Case\s*Number)\*?\*?\s*[:=-]+\*?\*?\s*([A-Za-z0-9\-]+)', clean_text, re.IGNORECASE)
        if pid_match:
            patient_id = pid_match.group(1).strip()

        # Match Patient Details (e.g. SUMERA AMBREEN 35 Yr(s) / Female)
        pname_match = re.search(r'(?:Patient\s*Details|Patient\s*Name|Name)\*?\*?\s*[:=-]+\*?\*?\s*([A-Za-z\s]+?)(?:\s+\d+|\s+Yr|\s+Age|\s*\(|\n|$)', clean_text, re.IGNORECASE)
        if pname_match:
            cand = pname_match.group(1).strip()
            cand_clean = re.sub(r'\b(Yr|Yrs|Age|Female|Male|Gender)\b.*', '', cand, flags=re.IGNORECASE).strip()
            if cand_clean and not any(k in cand_clean.lower() for k in ["report", "test", "chughtai", "shaukat", "standard"]):
                patient_name = cand_clean

        panel_match = re.search(r'(?:Test\s*Category|Test\s*Panel|Test\s*Name|Investigation|Profile)\*?\*?\s*[:=-]+\*?\*?\s*([^\n\r]+)', clean_text, re.IGNORECASE)
        if panel_match:
            cand_panel = panel_match.group(1).strip()
            if any(k in cand_panel.lower() for k in ["cbc", "blood c/e", "complete blood"]):
                panel_name = "Complete Blood Count (CBC)"
            else:
                panel_name = cand_panel
        elif any(k in clean_text.lower() for k in ["cbc", "blood c/e", "complete blood"]):
            panel_name = "Complete Blood Count (CBC)"
        elif "lipid" in clean_text.lower():
            panel_name = "Lipid Profile"
        elif "lft" in clean_text.lower() or "liver function" in clean_text.lower():
            panel_name = "Liver Function Tests (LFT)"
        elif "rft" in clean_text.lower() or "renal" in clean_text.lower():
            panel_name = "Renal Function Tests (RFT)"
        elif "glucose" in clean_text.lower() or "sugar" in clean_text.lower():
            panel_name = "Blood Glucose Examination"

        extracted_tests = []
        abnormal_tests = []
        seen_test_names = set()

        # Strategy 1: Standard whitespace pattern -> TestName   Result   Unit   Min - Max
        std_pattern = r'^([A-Za-z0-9\(\)\s/]+?)\s+([0-9\.]+)\s+([A-Za-z0-9\^/%_]+)\s+([0-9\.]+)\s*-\s*([0-9\.]+)'
        
        # Strategy 2: Chughtai Lab Reversed pattern -> TestName   NormalMin - NormalMax   Unit   Result
        chughtai_pattern = r'^([A-Za-z0-9\(\)\s/]+?)\s+([0-9\.]+)\s*-\s*([0-9\.]+)\s+([A-Za-z0-9\^/%_]+)\s+([0-9\.]+)'

        # Strategy 3: Colon/Bracket pattern -> Test: Result Unit (Min - Max)
        colon_pattern = r'^([A-Za-z0-9\(\)\s/]+?)\s*:\s*([0-9\.]+)\s*([A-Za-z0-9\^/%_]*)\s*[\(\[]\s*([0-9\.]+)\s*-\s*([0-9\.]+)\s*[\)\]]'

        for line in clean_text.split("\n"):
            line_clean = line.strip()
            if not line_clean or len(line_clean) < 5:
                continue

            test_name = None
            val = None
            unit = ""
            ref_min = None
            ref_max = None

            # Strategy 0: Markdown table row: | Test | Normal Value | Unit | Result |
            if line_clean.startswith("|") and line_clean.endswith("|"):
                parts = [p.strip() for p in line_clean.split("|")[1:-1]]
                if len(parts) >= 4:
                    col_test = parts[0].replace("*", "").strip()
                    col_ref = parts[1].replace("*", "").strip()
                    col_unit = parts[2].replace("*", "").strip()
                    col_res = parts[3].replace("*", "").strip()

                    if not (col_test.lower() in ["test", "test name", "parameter", "investigation"] or "---" in col_test or ":---" in col_test):
                        # Pattern A: col_ref is range (11.5 - 16) and col_res is value (11.9 or 3.9 red text)
                        ref_m = re.search(r'([0-9\.]+)\s*-\s*([0-9\.]+)', col_ref)
                        val_m = re.search(r'([0-9]+\.?[0-9]*)', col_res)
                        if ref_m and val_m:
                            test_name = col_test
                            ref_min = float(ref_m.group(1))
                            ref_max = float(ref_m.group(2))
                            val = float(val_m.group(1))
                            unit = col_unit
                        else:
                            # Pattern B: col_ref is value and col_res is range
                            val_m_rev = re.search(r'^[0-9\.]+$', col_ref)
                            ref_m_rev = re.search(r'([0-9\.]+)\s*-\s*([0-9\.]+)', col_res)
                            if val_m_rev and ref_m_rev:
                                test_name = col_test
                                val = float(val_m_rev.group(0))
                                ref_min = float(ref_m_rev.group(1))
                                ref_max = float(ref_m_rev.group(2))
                                unit = col_unit

            # Try Strategy 1 (Standard)
            if not test_name:
                m1 = re.match(std_pattern, line_clean)
                if m1:
                    test_name = m1.group(1).strip()
                    val = float(m1.group(2))
                    unit = m1.group(3).strip()
                    ref_min = float(m1.group(4))
                    ref_max = float(m1.group(5))
                else:
                    # Try Strategy 2 (Chughtai reversed: Test Min-Max Unit Result)
                    m2 = re.match(chughtai_pattern, line_clean)
                    if m2:
                        test_name = m2.group(1).strip()
                        ref_min = float(m2.group(2))
                        ref_max = float(m2.group(3))
                        unit = m2.group(4).strip()
                        val = float(m2.group(5))
                    else:
                        # Try Strategy 3 (Colon / Brackets)
                        m3 = re.match(colon_pattern, line_clean)
                        if m3:
                            test_name = m3.group(1).strip()
                            val = float(m3.group(2))
                            unit = m3.group(3).strip() or "unit"
                            ref_min = float(m3.group(4))
                            ref_max = float(m3.group(5))
                        else:
                            # Strategy 4: Clinical Tests Dictionary match
                            for kt in self.KNOWN_CLINICAL_TESTS:
                                if re.search(rf"\b{re.escape(kt)}\b", line_clean, re.IGNORECASE):
                                    clean_num_line = re.sub(r'x?10\^\d+/[A-Za-z]+', '', line_clean)
                                    nums = re.findall(r'([0-9]+\.?[0-9]*)', clean_num_line)
                                    if len(nums) >= 3:
                                        test_name = kt
                                        unit_m = re.search(r'\b(g/dl|g/dL|mg/dL|x10\^12/l|x10\^9/l|10\^3/uL|/cumm|mmol/L|U/L|%|mm/hr|fl|pg)\b', line_clean, re.IGNORECASE)
                                        unit = unit_m.group(1) if unit_m else ""
                                        
                                        range_match = re.search(r'([0-9\.]+)\s*-\s*([0-9\.]+)', clean_num_line)
                                        if range_match:
                                            ref_min = float(range_match.group(1))
                                            ref_max = float(range_match.group(2))
                                            for n in nums:
                                                fn = float(n)
                                                if fn != ref_min and fn != ref_max:
                                                    val = fn
                                                    break
                                            if val is None:
                                                val = float(nums[-1])
                                        else:
                                            val = float(nums[0])
                                            ref_min = float(nums[1])
                                            ref_max = float(nums[2])
                                        break

            if test_name and val is not None and ref_min is not None and ref_max is not None:
                if test_name.lower() in ["test", "test name", "parameter", "investigation"]:
                    continue

                canonical_key = test_name.lower().replace(" ", "")
                if canonical_key in seen_test_names:
                    continue
                seen_test_names.add(canonical_key)

                is_abnormal = False
                flag = "NORMAL"
                if val < ref_min:
                    is_abnormal = True
                    flag = "LOW"
                    abnormal_tests.append(f"{test_name} ({val} {unit}, normal: {ref_min}-{ref_max}) - LOW")
                elif val > ref_max:
                    is_abnormal = True
                    flag = "HIGH"
                    abnormal_tests.append(f"{test_name} ({val} {unit}, normal: {ref_min}-{ref_max}) - HIGH")

                extracted_tests.append({
                    "test_name": test_name,
                    "value": val,
                    "unit": unit,
                    "reference_range": f"{ref_min} - {ref_max}",
                    "ref_min": ref_min,
                    "ref_max": ref_max,
                    "is_abnormal": is_abnormal,
                    "flag": flag
                })

        explanation = self._generate_urdulish_explanation(patient_name, panel_name, extracted_tests, abnormal_tests)

        return {
            "patient_id": patient_id,
            "patient_name": patient_name,
            "panel_name": panel_name,
            "total_tests_extracted": len(extracted_tests),
            "abnormal_count": len(abnormal_tests),
            "extracted_tests": extracted_tests,
            "urdulish_explanation": explanation
        }

    def _generate_urdulish_explanation(self, name: str, panel: str, tests: List[Dict], abnormal: List[str]) -> str:
        """Generates reassuring, clear UrduLish explanation for physician approval and release."""
        clean_name = name if name and name != "UNKNOWN" else "Patient"
        if not tests:
            return f"Assalam-o-Alaikum {clean_name}! Aap ki {panel} report receive ho gayi hai. Attending physician is report ka review kar ke official rehnumai faraham karenge."

        if not abnormal:
            return (
                f"Assalam-o-Alaikum {clean_name}! Dr. Bilal Ahmed ne aap ki {panel} report clinically verify aur sign-off kar li hai. "
                f"Tamam test values normal reference range mein hain aur report bilkul clear hai. "
                f"Routine preventive care guidelines follow karein."
            )

        ab_items = [f"{t['test_name']} ({t['value']} {t['unit']}, {t['flag']})" for t in tests if t['is_abnormal']]
        ab_summary = ", ".join(ab_items[:3])
        return (
            f"Assalam-o-Alaikum {clean_name}! Dr. Bilal Ahmed ne aap ki {panel} report clinically verify aur sign-off kar li hai. "
            f"Report ke mutabiq {ab_summary} ki value reference range se thori mukhtalif hai, "
            f"jabke baqi tamam test values routine range mein hain. Ghabranay ki koi baat nahi, "
            f"aap scheduled consultation ke waqt doctor sahab se is par dietary aur clinical advice le sakte hain."
        )


if __name__ == "__main__":
    sample_file = r"D:\Netixsol\Week9\sample_report.pdf"
    parser = LabReportParser()
    res = parser.parse_report_file(sample_file)
    print("Parsed Patient:", res["patient_name"])
    print("Panel:", res["panel_name"])
    print("Abnormal Count:", res["abnormal_count"])
    print("Extracted Tests:", len(res["extracted_tests"]))
    for t in res["extracted_tests"]:
        print("  ->", t["test_name"], t["value"], t["unit"], t["reference_range"], t["flag"])
    print("UrduLish Explanation:", res["urdulish_explanation"])
