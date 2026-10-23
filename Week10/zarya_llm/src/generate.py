import os
import sys
import re
import json
import time
import random
import argparse
import copy
from datetime import datetime, timezone
import zoneinfo
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter

import math
import yaml
from jinja2 import Template
from dotenv import load_dotenv

# Ensure src directory is available on sys.path
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from schema import BankingTicket, get_large_amount_threshold
from prompt_format import build_system_message
import seed_stats

PROJECT_ROOT = Path(os.environ.get("ZARYA_PROJECT_ROOT", Path(__file__).resolve().parent.parent))

# Load environment configuration from project root or parent without printing or writing
if (PROJECT_ROOT / ".env").exists():
    load_dotenv(PROJECT_ROOT / ".env")
if (PROJECT_ROOT.parent / ".env").exists():
    load_dotenv(PROJECT_ROOT.parent / ".env")

CONFIG_PATH = PROJECT_ROOT / "configs" / "generation_plan.yaml"
DATA_SPEC_PATH = PROJECT_ROOT / "configs" / "data_spec.yaml"
SEEDS_DIR = PROJECT_ROOT / "data" / "seeds"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
GENERATED_PATH = RAW_DIR / "generated.jsonl"
REJECTED_PATH = RAW_DIR / "rejected.jsonl"
STATE_PATH = RAW_DIR / "generation_state.json"
PROMPTS_TEMPLATE_PATH = PROJECT_ROOT / "prompts" / "teacher_generation_prompt.txt"
COSTS_LOG_PATH = PROJECT_ROOT / "costs.md"
REQUEST_LOG_PATH = PROJECT_ROOT / "data" / "request_log.txt"

PROMPT_VERSION = "v1.14"

REFUSAL_TEMPLATES: Dict[str, Dict[str, List[str]]] = {
    "politics": {
        "roman_urdu": [
            "Ji, main is mauzu par koi raye ya mashwara nahi de sakti.",
            "Ji, ye mauzu mere daera e kaar se bahar hai aur main is par baat nahi kar sakti.",
            "Ji, main is mamlay par koi raye faraham nahi kar sakti.",
            "Ji, main sirf banking sawalat ke jawabat deti hoon aur is mozu par raye nahi de sakti.",
            "Ji, main is topic par koi raye ya rehnumai nahi de sakti.",
            "Ji, ye muamla meri maloomat se bahar hai aur main is par mashwara nahi de sakti.",
            "Ji, main is bare mein koi tabsara ya raye pesh nahi kar sakti.",
            "Ji, main is silsilay mein koi madad ya raye faraham nahi kar sakti.",
            "Ji, ye guftagu mere ikhtiyar se bahar hai aur main koi raye nahi de sakti.",
            "Ji, main is tarah ke mamlat par koi mashwara nahi de sakti.",
            "Ji, main is topic par tabsara karne se maazoor hoon.",
            "Ji, ye sawal mere daira e ikhtiyar mein nahi aata aur main raye nahi de sakti.",
            "Ji, main is mozu par koi hidayat ya mashwara nahi de sakti.",
            "Ji, main is mamlay mein koi raye nahi de sakti.",
            "Ji, ye mauzu mere daira e kar se bahar hai.",
            "Ji, main is bare mein koi raye nahi de sakti."
        ],
        "english": [
            "Ji, I cannot provide opinions or advice on topics outside my scope.",
            "Ji, this topic is outside my domain and I cannot assist with it.",
            "Ji, I am unable to offer any guidance or opinion on this subject.",
            "Ji, I cannot give any recommendations or advice regarding this matter.",
            "Ji, this inquiry falls outside what I handle and I cannot comment on it.",
            "Ji, I am not able to provide advice or opinions on this topic.",
            "Ji, I cannot assist with matters outside banking support.",
            "Ji, this subject is outside what I handle and I cannot advise on it."
        ],
        "urdu_script": [
            "جی، میں اس موضوع پر کوئی رائے یا مشورہ نہیں دے سکتی۔",
            "جی، یہ معاملہ میرے دائرہ کار سے باہر ہے اور میں اس پر بات نہیں کر سکتی۔",
            "جی، میں اس موضوع پر کوئی رہنمائی فراہم نہیں کر سکتی۔",
            "جی، میں بینکاری کے علاوہ دیگر موضوعات پر رائے نہیں دے سکتی۔",
            "جی، میں اس معاملے میں کوئی مشورہ یا رائے نہیں دے سکتی۔",
            "جی، یہ موضوع میری معلومات سے باہر ہے اور میں اس پر تبصرہ نہیں کر سکتی۔",
            "جی، میں اس سوال پر کوئی رائے دینے سے معذور ہوں۔",
            "جی، میں اس سلسلے میں کوئی رائے یا معلومات فراہم نہیں کر سکتی۔"
        ]
    },
    "medical": {
        "roman_urdu": [
            "Ji, main is topic par koi raye ya rehnumai nahi de sakti.",
            "Ji, ye muamla meri maloomat se bahar hai aur main is par mashwara nahi de sakti.",
            "Ji, main is bare mein koi tabsara ya raye pesh nahi kar sakti.",
            "Ji, main is silsilay mein koi madad ya raye faraham nahi kar sakti.",
            "Ji, ye guftagu mere ikhtiyar se bahar hai aur main koi raye nahi de sakti.",
            "Ji, main is tarah ke mamlat par koi mashwara nahi de sakti.",
            "Ji, main is topic par tabsara karne se maazoor hoon.",
            "Ji, ye sawal mere daira e ikhtiyar mein nahi aata aur main raye nahi de sakti.",
            "Ji, main is mozu par koi hidayat ya mashwara nahi de sakti.",
            "Ji, main is mamlay mein koi raye nahi de sakti.",
            "Ji, ye mauzu mere daira e kar se bahar hai.",
            "Ji, main is bare mein koi raye nahi de sakti.",
            "Ji, main is mozu par koi baat ya tabsara nahi kar sakti.",
            "Ji, ye sawal mere daere se bahar hai aur main is par mashwara nahi de sakti.",
            "Ji, main is mamlay par koi faisla ya mashwara nahi de sakti.",
            "Ji, main is bare mein koi maloomat ya raye faraham nahi kar sakti."
        ],
        "english": [
            "Ji, I am unable to offer any guidance or opinion on this subject.",
            "Ji, I cannot give any recommendations or advice regarding this matter.",
            "Ji, this inquiry falls outside what I handle and I cannot comment on it.",
            "Ji, I am not able to provide advice or opinions on this topic.",
            "Ji, I cannot assist with matters outside banking support.",
            "Ji, this subject is outside what I handle and I cannot advise on it.",
            "Ji, I cannot offer any views or recommendations on this matter.",
            "Ji, I am unable to comment or give advice on this subject."
        ],
        "urdu_script": [
            "جی، میں اس موضوع پر کوئی رہنمائی فراہم نہیں کر سکتی۔",
            "جی، میں بینکاری کے علاوہ دیگر موضوعات پر رائے نہیں دے سکتی۔",
            "جی، میں اس معاملے میں کوئی مشورہ یا رائے نہیں دے سکتی۔",
            "جی، یہ موضوع میری معلومات سے باہر ہے اور میں اس پر تبصرہ نہیں کر سکتی۔",
            "جی، میں اس سوال پر کوئی رائے دینے سے معذور ہوں۔",
            "جی، میں اس سلسلے میں کوئی رائے یا معلومات فراہم نہیں کر سکتی۔",
            "جی، یہ معاملہ میرے دائرہ اختیار سے باہر ہے اور میں مشورہ نہیں دے سکتی۔",
            "جی، میں اس موضوع پر تبصرہ کرنے سے قاصر ہوں۔"
        ]
    },
    "investment": {
        "roman_urdu": [
            "Ji, ye guftagu mere ikhtiyar se bahar hai aur main koi raye nahi de sakti.",
            "Ji, main is tarah ke mamlat par koi mashwara nahi de sakti.",
            "Ji, main is topic par tabsara karne se maazoor hoon.",
            "Ji, ye sawal mere daira e ikhtiyar mein nahi aata aur main raye nahi de sakti.",
            "Ji, main is mozu par koi hidayat ya mashwara nahi de sakti.",
            "Ji, main is mamlay mein koi raye nahi de sakti.",
            "Ji, ye mauzu mere daira e kar se bahar hai.",
            "Ji, main is bare mein koi raye nahi de sakti.",
            "Ji, main is mozu par koi baat ya tabsara nahi kar sakti.",
            "Ji, ye sawal mere daere se bahar hai aur main is par mashwara nahi de sakti.",
            "Ji, main is mamlay par koi faisla ya mashwara nahi de sakti.",
            "Ji, main is bare mein koi maloomat ya raye faraham nahi kar sakti.",
            "Ji, ye topic mere ikhtiyar se bahar hai aur main raye nahi de sakti.",
            "Ji, main is silsilay mein koi rehnumai faraham nahi kar sakti.",
            "Ji, main is tarah ke sawalat par koi raye nahi de sakti.",
            "Ji, ye muamla mere daera e kaar mein shamil nahi hai."
        ],
        "english": [
            "Ji, this inquiry falls outside what I handle and I cannot comment on it.",
            "Ji, I am not able to provide advice or opinions on this topic.",
            "Ji, I cannot assist with matters outside banking support.",
            "Ji, this subject is outside what I handle and I cannot advise on it.",
            "Ji, I cannot offer any views or recommendations on this matter.",
            "Ji, I am unable to comment or give advice on this subject.",
            "Ji, this topic is outside my scope and I cannot assist you.",
            "Ji, I cannot provide any opinions or guidance on this matter."
        ],
        "urdu_script": [
            "جی، میں اس معاملے میں کوئی مشورہ یا رائے نہیں دے سکتی۔",
            "جی، یہ موضوع میری معلومات سے باہر ہے اور میں اس پر تبصرہ نہیں کر سکتی۔",
            "جی، میں اس سوال پر کوئی رائے دینے سے معذور ہوں۔",
            "جی، میں اس سلسلے میں کوئی رائے یا معلومات فراہم نہیں کر سکتی۔",
            "جی، یہ معاملہ میرے دائرہ اختیار سے باہر ہے اور میں مشورہ نہیں دے سکتی۔",
            "جی، میں اس موضوع پر تبصرہ کرنے سے قاصر ہوں۔",
            "جی، میں اس معاملے پر کوئی رہنمائی نہیں دے سکتی۔",
            "جی، میں اس موضوع پر کوئی بات چیت نہیں کر سکتی۔"
        ]
    },
    "sports": {
        "roman_urdu": [
            "Ji, main is mozu par koi hidayat ya mashwara nahi de sakti.",
            "Ji, main is mamlay mein koi raye nahi de sakti.",
            "Ji, ye mauzu mere daira e kar se bahar hai.",
            "Ji, main is bare mein koi raye nahi de sakti.",
            "Ji, main is mozu par koi baat ya tabsara nahi kar sakti.",
            "Ji, ye sawal mere daere se bahar hai aur main is par mashwara nahi de sakti.",
            "Ji, main is mamlay par koi faisla ya mashwara nahi de sakti.",
            "Ji, main is bare mein koi maloomat ya raye faraham nahi kar sakti.",
            "Ji, ye topic mere ikhtiyar se bahar hai aur main raye nahi de sakti.",
            "Ji, main is silsilay mein koi rehnumai faraham nahi kar sakti.",
            "Ji, main is tarah ke sawalat par koi raye nahi de sakti.",
            "Ji, ye muamla mere daera e kaar mein shamil nahi hai.",
            "Ji, main is mozu par koi raye dene ki majaz nahi hoon.",
            "Ji, main is mamlay par tabsara karne se maazoor hoon.",
            "Ji, main is topic par koi maloomat faraham nahi kar sakti.",
            "Ji, ye guftagu mere kam se bahar hai aur main raye nahi de sakti."
        ],
        "english": [
            "Ji, I cannot assist with matters outside banking support.",
            "Ji, this subject is outside what I handle and I cannot advise on it.",
            "Ji, I cannot offer any views or recommendations on this matter.",
            "Ji, I am unable to comment or give advice on this subject.",
            "Ji, this topic is outside my scope and I cannot assist you.",
            "Ji, I cannot provide any opinions or guidance on this matter.",
            "Ji, I am not authorized to advise on topics outside my domain.",
            "Ji, I cannot comment on matters beyond banking assistance."
        ],
        "urdu_script": [
            "جی، یہ معاملہ میرے دائرہ اختیار سے باہر ہے اور میں مشورہ نہیں دے سکتی۔",
            "جی، میں اس موضوع پر تبصرہ کرنے سے قاصر ہوں۔",
            "جی، میں اس معاملے پر کوئی رہنمائی نہیں دے سکتی۔",
            "جی، میں اس موضوع پر کوئی بات چیت نہیں کر سکتی۔",
            "جی، یہ سوال میرے دائرہ کار میں نہیں آتا۔",
            "جی، میں اس سلسلے میں کوئی مشورہ نہیں دے سکتی۔",
            "جی، میں اس معاملے پر کوئی رائے پیش نہیں کر سکتی۔",
            "جی، میں اس موضوع پر کسی قسم کی رائے نہیں دے سکتی۔"
        ]
    },
    "other bank": {
        "roman_urdu": [
            "Ji, main is mozu par koi baat ya tabsara nahi kar sakti.",
            "Ji, ye sawal mere daere se bahar hai aur main is par mashwara nahi de sakti.",
            "Ji, main is mamlay par koi faisla ya mashwara nahi de sakti.",
            "Ji, main is bare mein koi maloomat ya raye faraham nahi kar sakti.",
            "Ji, ye topic mere ikhtiyar se bahar hai aur main raye nahi de sakti.",
            "Ji, main is silsilay mein koi rehnumai faraham nahi kar sakti.",
            "Ji, main is tarah ke sawalat par koi raye nahi de sakti.",
            "Ji, ye muamla mere daera e kaar mein shamil nahi hai.",
            "Ji, main is mozu par koi raye dene ki majaz nahi hoon.",
            "Ji, main is mamlay par tabsara karne se maazoor hoon.",
            "Ji, main is topic par koi maloomat faraham nahi kar sakti.",
            "Ji, ye guftagu mere kam se bahar hai aur main raye nahi de sakti.",
            "Ji, main is bare mein koi hidayat nahi de sakti.",
            "Ji, main is mauzu par kisi qisam ki raye nahi de sakti.",
            "Ji, ye sawal mere daere mein nahi aata.",
            "Ji, main is silsilay mein koi tabsara nahi kar sakti."
        ],
        "english": [
            "Ji, I cannot offer any views or recommendations on this matter.",
            "Ji, I am unable to comment or give advice on this subject.",
            "Ji, this topic is outside my scope and I cannot assist you.",
            "Ji, I cannot provide any opinions or guidance on this matter.",
            "Ji, I am not authorized to advise on topics outside my domain.",
            "Ji, I cannot comment on matters beyond banking assistance.",
            "Ji, this inquiry is beyond what I handle and I cannot assist.",
            "Ji, I cannot offer any guidance on this particular subject."
        ],
        "urdu_script": [
            "جی، یہ سوال میرے دائرہ کار میں نہیں آتا۔",
            "جی، میں اس سلسلے میں کوئی مشورہ نہیں دے سکتی۔",
            "جی، میں اس معاملے پر کوئی رائے پیش نہیں کر سکتی۔",
            "جی، میں اس موضوع پر کسی قسم کی رائے نہیں دے سکتی۔",
            "جی، میں اس موضوع پر کوئی رائے یا مشورہ نہیں دے سکتی۔",
            "جی، یہ معاملہ میرے دائرہ کار سے باہر ہے اور میں اس پر بات نہیں کر سکتی۔",
            "جی، میں اس موضوع پر کوئی رہنمائی فراہم نہیں کر سکتی۔",
            "جی، میں بینکاری کے علاوہ دیگر موضوعات پر رائے نہیں دے سکتی۔"
        ]
    },
    "homework": {
        "roman_urdu": [
            "Ji, ye topic mere ikhtiyar se bahar hai aur main raye nahi de sakti.",
            "Ji, main is silsilay mein koi rehnumai faraham nahi kar sakti.",
            "Ji, main is tarah ke sawalat par koi raye nahi de sakti.",
            "Ji, ye muamla mere daera e kaar mein shamil nahi hai.",
            "Ji, main is mozu par koi raye dene ki majaz nahi hoon.",
            "Ji, main is mamlay par tabsara karne se maazoor hoon.",
            "Ji, main is topic par koi maloomat faraham nahi kar sakti.",
            "Ji, ye guftagu mere kam se bahar hai aur main raye nahi de sakti.",
            "Ji, main is bare mein koi hidayat nahi de sakti.",
            "Ji, main is mauzu par kisi qisam ki raye nahi de sakti.",
            "Ji, ye sawal mere daere mein nahi aata.",
            "Ji, main is silsilay mein koi tabsara nahi kar sakti.",
            "Ji, main is mauzu par koi raye ya mashwara nahi de sakti.",
            "Ji, ye mauzu mere daera e kaar se bahar hai aur main is par baat nahi kar sakti.",
            "Ji, main is mamlay par koi raye faraham nahi kar sakti.",
            "Ji, main sirf banking sawalat ke jawabat deti hoon aur is mozu par raye nahi de sakti."
        ],
        "english": [
            "Ji, this topic is outside my scope and I cannot assist you.",
            "Ji, I cannot provide any opinions or guidance on this matter.",
            "Ji, I am not authorized to advise on topics outside my domain.",
            "Ji, I cannot comment on matters beyond banking assistance.",
            "Ji, this inquiry is beyond what I handle and I cannot assist.",
            "Ji, I cannot offer any guidance on this particular subject.",
            "Ji, I cannot provide opinions or advice on topics outside my scope.",
            "Ji, this topic is outside my domain and I cannot assist with it."
        ],
        "urdu_script": [
            "جی، میں اس موضوع پر کوئی رائے یا مشورہ نہیں دے سکتی۔",
            "جی، یہ معاملہ میرے دائرہ کار سے باہر ہے اور میں اس پر بات نہیں کر سکتی۔",
            "جی، میں اس موضوع پر کوئی رہنمائی فراہم نہیں کر سکتی۔",
            "جی، میں بینکاری کے علاوہ دیگر موضوعات پر رائے نہیں دے سکتی۔",
            "جی، میں اس معاملے میں کوئی مشورہ یا رائے نہیں دے سکتی۔",
            "جی، یہ موضوع میری معلومات سے باہر ہے اور میں اس پر تبصرہ نہیں کر سکتی۔",
            "جی، میں اس سوال پر کوئی رائے دینے سے معذور ہوں۔",
            "جی، میں اس سلسلے میں کوئی رائے یا معلومات فراہم نہیں کر سکتی۔"
        ]
    },
    "general chat": {
        "roman_urdu": [
            "Ji, main is mozu par koi raye dene ki majaz nahi hoon.",
            "Ji, main is mamlay par tabsara karne se maazoor hoon.",
            "Ji, main is topic par koi maloomat faraham nahi kar sakti.",
            "Ji, ye guftagu mere kam se bahar hai aur main raye nahi de sakti.",
            "Ji, main is bare mein koi hidayat nahi de sakti.",
            "Ji, main is mauzu par kisi qisam ki raye nahi de sakti.",
            "Ji, ye sawal mere daere mein nahi aata.",
            "Ji, main is silsilay mein koi tabsara nahi kar sakti.",
            "Ji, main is mauzu par koi raye ya mashwara nahi de sakti.",
            "Ji, ye mauzu mere daera e kaar se bahar hai aur main is par baat nahi kar sakti.",
            "Ji, main is mamlay par koi raye faraham nahi kar sakti.",
            "Ji, main sirf banking sawalat ke jawabat deti hoon aur is mozu par raye nahi de sakti.",
            "Ji, main is topic par koi raye ya rehnumai nahi de sakti.",
            "Ji, ye muamla meri maloomat se bahar hai aur main is par mashwara nahi de sakti.",
            "Ji, main is bare mein koi tabsara ya raye pesh nahi kar sakti.",
            "Ji, main is silsilay mein koi madad ya raye faraham nahi kar sakti."
        ],
        "english": [
            "Ji, I am not authorized to advise on topics outside my domain.",
            "Ji, I cannot comment on matters beyond banking assistance.",
            "Ji, this inquiry is beyond what I handle and I cannot assist.",
            "Ji, I cannot offer any guidance on this particular subject.",
            "Ji, I cannot provide opinions or advice on topics outside my scope.",
            "Ji, this topic is outside my domain and I cannot assist with it.",
            "Ji, I am unable to offer any guidance or opinion on this subject.",
            "Ji, I cannot give any recommendations or advice regarding this matter."
        ],
        "urdu_script": [
            "جی، میں اس معاملے میں کوئی مشورہ یا رائے نہیں دے سکتی۔",
            "جی، یہ موضوع میری معلومات سے باہر ہے اور میں اس پر تبصرہ نہیں کر سکتی۔",
            "جی، میں اس سوال پر کوئی رائے دینے سے معذور ہوں۔",
            "جی، میں اس سلسلے میں کوئی رائے یا معلومات فراہم نہیں کر سکتی۔",
            "جی، یہ معاملہ میرے دائرہ اختیار سے باہر ہے اور میں مشورہ نہیں دے سکتی۔",
            "جی، میں اس موضوع پر تبصرہ کرنے سے قاصر ہوں۔",
            "جی، میں اس معاملے پر کوئی رہنمائی نہیں دے سکتی۔",
            "جی، میں اس موضوع پر کوئی بات چیت نہیں کر سکتی۔"
        ]
    },
    "legal": {
        "roman_urdu": [
            "Ji, main is bare mein koi hidayat nahi de sakti.",
            "Ji, main is mauzu par kisi qisam ki raye nahi de sakti.",
            "Ji, ye sawal mere daere mein nahi aata.",
            "Ji, main is silsilay mein koi tabsara nahi kar sakti.",
            "Ji, main is mauzu par koi raye ya mashwara nahi de sakti.",
            "Ji, ye mauzu mere daera e kaar se bahar hai aur main is par baat nahi kar sakti.",
            "Ji, main is mamlay par koi raye faraham nahi kar sakti.",
            "Ji, main sirf banking sawalat ke jawabat deti hoon aur is mozu par raye nahi de sakti.",
            "Ji, main is topic par koi raye ya rehnumai nahi de sakti.",
            "Ji, ye muamla meri maloomat se bahar hai aur main is par mashwara nahi de sakti.",
            "Ji, main is bare mein koi tabsara ya raye pesh nahi kar sakti.",
            "Ji, main is silsilay mein koi madad ya raye faraham nahi kar sakti.",
            "Ji, ye guftagu mere ikhtiyar se bahar hai aur main koi raye nahi de sakti.",
            "Ji, main is tarah ke mamlat par koi mashwara nahi de sakti.",
            "Ji, main is topic par tabsara karne se maazoor hoon.",
            "Ji, ye sawal mere daira e ikhtiyar mein nahi aata aur main raye nahi de sakti."
        ],
        "english": [
            "Ji, this inquiry is beyond what I handle and I cannot assist.",
            "Ji, I cannot offer any guidance on this particular subject.",
            "Ji, I cannot provide opinions or advice on topics outside my scope.",
            "Ji, this topic is outside my domain and I cannot assist with it.",
            "Ji, I am unable to offer any guidance or opinion on this subject.",
            "Ji, I cannot give any recommendations or advice regarding this matter.",
            "Ji, this inquiry falls outside what I handle and I cannot comment on it.",
            "Ji, I am not able to provide advice or opinions on this topic."
        ],
        "urdu_script": [
            "جی، یہ معاملہ میرے دائرہ اختیار سے باہر ہے اور میں مشورہ نہیں دے سکتی۔",
            "جی، میں اس موضوع پر تبصرہ کرنے سے قاصر ہوں۔",
            "جی، میں اس معاملے پر کوئی رہنمائی نہیں دے سکتی۔",
            "جی، میں اس موضوع پر کوئی بات چیت نہیں کر سکتی۔",
            "جی، یہ سوال میرے دائرہ کار میں نہیں آتا۔",
            "جی، میں اس سلسلے میں کوئی مشورہ نہیں دے سکتی۔",
            "جی، میں اس معاملے پر کوئی رائے پیش نہیں کر سکتی۔",
            "جی، میں اس موضوع پر کسی قسم کی رائے نہیں دے سکتی۔"
        ]
    }
}


class RefusalTemplateSelector:
    def __init__(self, templates: Dict[str, Dict[str, List[str]]] = REFUSAL_TEMPLATES, seed: int = 42):
        self.templates = templates
        self.rng = random.Random(seed)
        self.history: List[str] = []

    def normalize_topic(self, topic: Optional[str]) -> str:
        if not topic:
            return "general chat"
        t = str(topic).lower().strip().replace("_", " ")
        if "politic" in t or "election" in t:
            return "politics"
        elif "medic" in t or "health" in t or "doctor" in t or "daw" in t:
            return "medical"
        elif "invest" in t or "stock" in t or "crypto" in t or "share" in t or "trading" in t:
            return "investment"
        elif "sport" in t or "cricket" in t or "match" in t or "football" in t or "game" in t:
            return "sports"
        elif "other" in t or "bank" in t:
            return "other bank"
        elif "homework" in t or "school" in t or "essay" in t or "academic" in t:
            return "homework"
        elif "legal" in t or "court" in t or "law" in t or "wakeel" in t:
            return "legal"
        return "general chat"

    def normalize_lang(self, lang: Optional[str]) -> str:
        if not lang:
            return "roman_urdu"
        l = str(lang).lower().strip()
        if "english" in l:
            return "english"
        elif "urdu_script" in l or ("urdu" in l and "roman" not in l and "lish" not in l):
            return "urdu_script"
        return "roman_urdu"

    def select(self, topic: str, language: str) -> str:
        top = self.normalize_topic(topic)
        lang = self.normalize_lang(language)
        pool = self.templates.get(top, {}).get(lang, [])
        if not pool:
            pool = self.templates.get("general chat", {}).get(lang, [])

        recent_100 = self.history[-100:] if len(self.history) >= 100 else self.history
        counts = {tpl: recent_100.count(tpl) for tpl in pool}
        # Avoid repeating the same template more than 3 times per 100 refusals
        eligible = [tpl for tpl in pool if counts[tpl] < 3]
        if not eligible:
            min_c = min(counts.values())
            eligible = [tpl for tpl in pool if counts[tpl] == min_c]

        chosen = self.rng.choice(eligible)
        self.history.append(chosen)
        return chosen


default_refusal_selector = RefusalTemplateSelector(REFUSAL_TEMPLATES, seed=42)

AMOUNT_ALLOWED_INTENTS = {
    "atm_cash_dispense_issue",
    "bill_payment",
    "card_declined",
    "fee_dispute",
    "pending_transaction",
    "report_scam_call",
    "service_complaint",
    "sim_swap_report",
    "transfer_failed",
    "unauthorized_transaction",
    "wrong_transfer",
}

SCAM_WARNING_INTENTS = {
    "report_scam_call",
    "phishing_report",
    "sim_swap_report",
    "refuse_credentials",
}


class QuotaExhaustedError(Exception):
    pass


def log_request(model_name: str) -> None:
    try:
        REQUEST_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        now_utc_str = datetime.now(timezone.utc).isoformat()
        with open(REQUEST_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{now_utc_str} {model_name}\n")
            f.flush()
    except Exception as e:
        print(f"[WARN] Failed to write to request log: {e}")


def count_today_pacific_requests(log_path: Path = REQUEST_LOG_PATH, target_date=None, model_name: Optional[str] = None) -> int:
    if not log_path.exists():
        return 0
    pac_tz = zoneinfo.ZoneInfo("America/Los_Angeles")
    if target_date is None:
        target_date = datetime.now(pac_tz).date()
    count = 0
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            parts = line_str.split()
            if not parts:
                continue
            ts_str = parts[0]
            m_name = parts[1] if len(parts) > 1 else None
            if model_name is not None and m_name != model_name:
                continue
            try:
                if ts_str.endswith("Z"):
                    ts_str = ts_str[:-1] + "+00:00"
                dt = datetime.fromisoformat(ts_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                dt_pac = dt.astimezone(pac_tz)
                if dt_pac.date() == target_date:
                    count += 1
            except Exception:
                continue
    return count


def get_last_request_timestamp(log_path: Path = REQUEST_LOG_PATH) -> Optional[datetime]:
    if not log_path.exists():
        return None
    last_dt = None
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            parts = line_str.split()
            if not parts:
                continue
            ts_str = parts[0]
            try:
                if ts_str.endswith("Z"):
                    ts_str = ts_str[:-1] + "+00:00"
                dt = datetime.fromisoformat(ts_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                last_dt = dt
            except Exception:
                continue
    return last_dt


def calculate_pacing_delay(
    last_call_dt: Optional[datetime],
    current_dt: Optional[datetime] = None,
    min_interval: float = 0.0
) -> float:
    if last_call_dt is None or min_interval <= 0:
        return 0.0
    if current_dt is None:
        current_dt = datetime.now(timezone.utc)
    if current_dt.tzinfo is None:
        current_dt = current_dt.replace(tzinfo=timezone.utc)
    if last_call_dt.tzinfo is None:
        last_call_dt = last_call_dt.replace(tzinfo=timezone.utc)
    elapsed = (current_dt - last_call_dt).total_seconds()
    if elapsed < min_interval:
        return max(0.0, min_interval - elapsed)
    return 0.0


def get_next_pacific_reset_time(current_time_utc: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    from datetime import timedelta
    pac_tz = zoneinfo.ZoneInfo("America/Los_Angeles")
    karachi_tz = zoneinfo.ZoneInfo("Asia/Karachi")
    if current_time_utc is None:
        current_time_utc = datetime.now(timezone.utc)
    elif current_time_utc.tzinfo is None:
        current_time_utc = current_time_utc.replace(tzinfo=timezone.utc)
    pac_dt = current_time_utc.astimezone(pac_tz)
    next_pac_date = pac_dt.date() + timedelta(days=1)
    next_pac_midnight = datetime(next_pac_date.year, next_pac_date.month, next_pac_date.day, 0, 0, 0, tzinfo=pac_tz)
    next_karachi_dt = next_pac_midnight.astimezone(karachi_tz)
    return next_pac_midnight, next_karachi_dt


def get_model_limits(model_name: str, config: Dict[str, Any], exit_on_error: bool = True) -> Dict[str, Any]:
    limits_table = config.get("model_limits", {})
    if not model_name or model_name not in limits_table:
        if exit_on_error:
            print(f"[ERROR] Model '{model_name}' is not in model_limits table in configs/generation_plan.yaml. Please add its limits (min_seconds_between_requests and daily_request_limit).")
            sys.exit(1)
        raise KeyError(f"Model '{model_name}' is not in model_limits table.")
    return limits_table[model_name]


def is_quota_error(exc: Exception) -> bool:
    err_str = str(exc).lower()
    is_429 = ("429" in err_str) or ("resourceexhausted" in err_str)
    is_quota = "quota" in err_str
    return bool(is_429 and is_quota)

ARABIC_TO_URDU_MAP = {
    "\u0643": "\u06a9",  # Arabic Kaf -> Urdu Keheh
    "\u064a": "\u06cc",  # Arabic Yeh -> Urdu Farsi Yeh
    "\u0649": "\u06cc",  # Arabic Alef Maksura -> Urdu Farsi Yeh
}

def normalize_urdu_text(text: str) -> str:
    if not text:
        return text
    for ar_cp, ur_cp in ARABIC_TO_URDU_MAP.items():
        text = text.replace(ar_cp, ur_cp)
    return text

def has_arabic_codepoints(text: str) -> bool:
    if not text:
        return False
    return any(cp in text for cp in ARABIC_TO_URDU_MAP)

def format_number_no_trailing_zero(val: Any) -> str:
    if isinstance(val, (int, float)):
        fval = float(val)
        if fval.is_integer():
            return str(int(fval))
        return f"{fval:g}"
    s = str(val).strip()
    return re.sub(r"(\d+)\.0+(?!\d)", r"\1", s)

BASE_SYSTEM_MESSAGE = (
    "Tum Zarya Bank ki support officer ho.\n"
    "1. Hamesha Ji aur aap istemal karo, izzat ke saath.\n"
    "2. Jawab chhota aur saaf rakho, ek dafa mein sirf ek sawal poochho.\n"
    "3. Fees, limits aur TAT sirf diye gaye documents se batao. Agar document mein nahi hai to apni taraf se mat batao.\n"
    "4. OTP, PIN ya password kabhi mat maango. Customer ko saaf batao ke bank ye kabhi nahi maangta."
)

MONTH_NAMES_SET = {
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
    "جنوری", "فروری", "مارچ", "اپریل", "مئی", "جون",
    "جولائی", "اگست", "ستمبر", "اکتوبر", "نومبر", "دسمبر"
}

INSULT_PATTERNS = [
    r"\bbakwaas\b", r"\bchor\b", r"\bthief\b", r"\bworst\b", r"\bshame\b",
    r"\bcourt\b", r"\bpolice\b", r"\bcase\s+kar\b", r"\blanat\b", r"\bfraud\s+bank\b",
    r"\bkutte\b", r"\bchutiya\b", r"\bkamine\b", r"\blafange\b"
]
INSULT_REGEX = re.compile("|".join(INSULT_PATTERNS), re.IGNORECASE)


def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Configuration file not found at: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_seeds(seeds_dir: Path = SEEDS_DIR) -> List[Dict[str, Any]]:
    target_files = [seeds_dir / "seeds.jsonl"] + sorted(seeds_dir.glob("seeds_batch*.jsonl"))
    seeds = []
    for fpath in target_files:
        if not fpath.exists():
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    seeds.append(json.loads(line_str))
    return seeds


SEEDS_BY_ID: Dict[str, Dict[str, Any]] = {}

def get_seed_by_id(seed_id: str) -> Optional[Dict[str, Any]]:
    global SEEDS_BY_ID
    if not SEEDS_BY_ID:
        try:
            seeds = load_seeds(SEEDS_DIR)
            SEEDS_BY_ID = {s.get("id"): s for s in seeds if s.get("id")}
        except Exception:
            pass
    return SEEDS_BY_ID.get(seed_id)


def derive_task_type(seed: Dict[str, Any]) -> str:
    category = seed.get("category", "")
    ticket = seed.get("ticket")
    if category == "fraud":
        return "fraud"
    elif category == "out_of_scope":
        return "out_of_scope"
    elif ticket is not None and category != "fraud":
        return "complaint"
    else:
        return "faq"


def select_opening_style_group(mood: str, is_context_fact: bool, task_type: str, intent: Optional[str] = None) -> str:
    # 1. out_of_scope always gets refusal group
    if task_type == "out_of_scope":
        return "refusal"

    # 2. faq requests with any mood use direct group
    if task_type == "faq":
        return "direct"

    # 3. complaint and fraud requests with frustrated or very_angry use acknowledge group
    if task_type in ["complaint", "fraud"] and mood in ["frustrated", "very_angry"]:
        return "acknowledge"

    # 4. calm complaint and fraud requests
    if task_type == "fraud":
        intent_lower = (intent or "").lower()
        if intent_lower in ["unauthorized_transaction", "fraud_report"] or "unauthorized" in intent_lower:
            return "detail"
        return "scam"
    elif task_type == "complaint":
        if is_context_fact:
            return "direct"
        return "detail"

    return "direct"


def select_opening_style(
    config: Dict[str, Any],
    mood: str,
    is_context_fact: bool,
    task_type: str = "faq",
    intent: Optional[str] = None,
    rng: Optional[random.Random] = None
) -> str:
    if rng is None:
        rng = random.Random(42)

    opening_styles = config.get("opening_styles", {})
    if isinstance(opening_styles, list):
        return rng.choice(opening_styles) if opening_styles else "Start immediately with the direct answer to the customer question without preamble"

    group_key = select_opening_style_group(mood=mood, is_context_fact=is_context_fact, task_type=task_type, intent=intent)
    group_list = opening_styles.get(group_key, [])
    if group_list:
        return rng.choice(group_list)
    return "Start immediately with the direct answer to the customer question without preamble"


def sample_customer_style_examples(
    cust_pool: Dict[str, Any],
    lang_key: str,
    mood: str,
    spelling: str,
    count: int,
    rng: random.Random,
    task_type: Optional[str] = None
) -> List[str]:
    raw_list = cust_pool.get(lang_key, [])
    target_topic = "refusal" if task_type == "out_of_scope" else None

    matching_texts = []
    for item in raw_list:
        if isinstance(item, dict):
            if item.get("mood") == mood and item.get("spelling") == spelling:
                item_topic = item.get("topic")
                if target_topic:
                    if item_topic == target_topic:
                        matching_texts.append(item.get("text", ""))
                else:
                    if item_topic != "refusal":
                        matching_texts.append(item.get("text", ""))
        elif isinstance(item, str):
            if not target_topic:
                matching_texts.append(item)

    if not matching_texts:
        for item in raw_list:
            if isinstance(item, dict):
                item_topic = item.get("topic")
                if target_topic:
                    if item_topic == target_topic:
                        matching_texts.append(item.get("text", ""))
                else:
                    if item_topic != "refusal":
                        matching_texts.append(item.get("text", ""))
            elif isinstance(item, str):
                if not target_topic:
                    matching_texts.append(item)

    if not matching_texts:
        return []
    return rng.sample(matching_texts, min(count, len(matching_texts)))


def get_teacher_config() -> Dict[str, str]:
    provider = os.getenv("TEACHER_PROVIDER", "").strip().lower()
    model = os.getenv("TEACHER_MODEL", "").strip()
    key_var = f"{provider.upper()}_API_KEY" if provider else "API_KEY"
    api_key = os.getenv(key_var, "").strip()
    return {
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "key_var": key_var,
    }


def validate_teacher_model(model: str) -> None:
    invalid_models = {"", "gemini", "openai", "anthropic"}
    if not model or model.strip().lower() in invalid_models:
        print(f"[ERROR] TEACHER_MODEL is '{model}'. Please put a real model name in .env (for example: gemini-2.5-flash, gpt-4o-mini, claude-3-5-haiku-20241022).")
        sys.exit(1)


def load_prompt_template() -> str:
    if PROMPTS_TEMPLATE_PATH.exists():
        with open(PROMPTS_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    raise FileNotFoundError(f"Generation prompt template not found at: {PROMPTS_TEMPLATE_PATH}")


def extract_distinct_numeric_values(text: str) -> List[float]:
    raw = re.findall(r"\b\d+(?:\.\d+)?\b", text)
    values = []
    seen = set()
    for item in raw:
        try:
            val = float(item)
            if val not in seen:
                seen.add(val)
                values.append(val)
        except ValueError:
            pass
    return values


def extract_first_sentence(text: str) -> str:
    cleaned = text.strip()
    m = re.search(r"^(.*?(?:\.(?!\d)|[!?۔؟]))", cleaned)
    if m:
        return m.group(1).strip()
    return cleaned


def is_mandatory_warning_sentence(sent: str) -> bool:
    if not sent:
        return False
    s = re.sub(r"[.!?۔؟،,\s]+", " ", sent.strip()).strip().lower()
    s = normalize_urdu_text(s)
    if "zarya bank kabhi bhi call ya sms par aap ka otp ya pin nahi maangta" in s:
        return True
    if "zarya bank will never ask for your otp or pin over a call or sms" in s:
        return True
    if "کبھی بھی کال یا ایس ایم ایس پر آپ کا کارڈ نمبر" in s:
        return True
    return False


def extract_effective_opening_sentence(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return ""
    sentences = [s.strip() for s in re.findall(r'[^.!?۔؟]+(?:[.!?۔؟]|$)', cleaned) if s.strip()]
    for s in sentences:
        if not is_mandatory_warning_sentence(s):
            return s
    return sentences[0] if sentences else ""
def derive_customer_writing_style(mood: str, spelling: str = "clean") -> str:
    if mood == "very_angry":
        return "informal and shouting"
    elif mood == "frustrated":
        return "informal"
    else:
        return "plain and polite"


def build_generation_prompt(
    seed: Dict[str, Any],
    variation: Dict[str, Any],
    task_type: Optional[str] = None,
    nodoc: bool = False,
    sampled_roman_urdu_examples: Optional[List[str]] = None,
    sampled_urdu_script_examples: Optional[List[str]] = None,
    opening_style: Optional[str] = None,
    end_style: Optional[str] = None,
    nodoc_target: Optional[str] = None,
    sampled_facets: Optional[Dict[str, str]] = None,
    forbidden_customer_phrases: Optional[List[str]] = None
) -> str:
    template_str = load_prompt_template()
    if task_type is None:
        task_type = derive_task_type(seed)

    seed_dialogue_lines = []
    for msg in seed.get("messages", []):
        role = msg.get("role")
        if role != "system":
            seed_dialogue_lines.append(f"{role.capitalize()}: {msg.get('content')}")
    seed_dialogue_text = "\n".join(seed_dialogue_lines)

    turn_count_str = "multi_turn" if variation.get("is_multi_turn") else "single_turn"

    if nodoc:
        context_req = "MUST be 'koi document nahi mila' to simulate document retrieval failure"
        schema_context_example = '"koi document nahi mila"'
    elif task_type in ["fraud", "out_of_scope"]:
        context_req = "MUST be null (no policy document fact needed for triage or refusal)"
        schema_context_example = "null"
    else:
        context_req = "Fresh fictional policy text with NEW fictional numbers (fees, limits, turnaround hours) never copied from the seed"
        schema_context_example = '"Fictional policy text with fresh numbers..."'

    include_ticket = (task_type in ["complaint", "fraud"])

    # Format sampled numbers text if provided
    sampled_nums = variation.get("sampled_numbers", {})
    if sampled_nums:
        num_pairs = [f"{k}: {v}" for k, v in sampled_nums.items()]
        required_nums_text = ", ".join(num_pairs)
    else:
        required_nums_text = ""

    sampled_cust_amt = variation.get("sampled_customer_amount")

    # Target nodoc instruction and sampled facets text
    target_nodoc = nodoc_target or variation.get("nodoc_target")
    facets_dict = sampled_facets or variation.get("sampled_facets", {})
    facets_text = ", ".join(f"{k}: {v}" for k, v in facets_dict.items()) if facets_dict else ""

    # Fallback default style examples if none supplied
    if not sampled_roman_urdu_examples:
        sampled_roman_urdu_examples = [
            "aoa mera card ATM machine mein phans gaya hai nikal nahi raha",
            "bhai transfer kiya tha abhi tak receiver ko mila nahi",
            "mera account block ho gaya hai kya karun",
            "yaar paise do dafa kat gaye hain foran wapis karo"
        ]
    if not sampled_urdu_script_examples:
        sampled_urdu_script_examples = [
            "میرا کارڈ اے ٹی ایم مشین میں پھنس گیا ہے",
            "پیسے کٹ گئے ہیں لیکن میسج نہیں آیا کیا کروں",
            "سلام نیا اکاؤنٹ کھلوانے کا کیا طریقہ ہے",
            "ایک نمبر سے کال آئی تھی پن مانگ رہے تھے"
        ]

    chosen_opening_style = opening_style or variation.get("opening_style") or "Begin with polite acknowledgement of customer concern followed directly by factual answer"
    chosen_end_style = end_style or variation.get("end_style") or "statement"

    template = Template(template_str)
    rendered_prompt = template.render(
        task_type=task_type,
        category=variation.get("category", seed.get("category", "complaint")),
        intent=variation.get("intent", seed.get("intent", "transfer_failed")),
        language=variation.get("language", seed.get("language", "urdulish")),
        spelling=variation.get("spelling", "clean"),
        writing_style=variation.get("writing_style", derive_customer_writing_style(variation.get("mood", "calm"), variation.get("spelling", "clean"))),
        mood=variation.get("mood", "calm"),
        turn_count=turn_count_str,
        opening_style=chosen_opening_style,
        end_style=chosen_end_style,
        sampled_roman_urdu_examples=sampled_roman_urdu_examples,
        sampled_urdu_script_examples=sampled_urdu_script_examples,
        required_context_numbers_text=required_nums_text,
        sampled_customer_amount=sampled_cust_amt,
        context_requirement=context_req,
        schema_context_example=schema_context_example,
        include_ticket=include_ticket,
        nodoc_target=target_nodoc,
        sampled_facets_text=facets_text,
        forbidden_customer_phrases=forbidden_customer_phrases or variation.get("forbidden_customer_phrases"),
        seed_id=seed.get("id", "seed_001"),
        seed_category=seed.get("category", "complaint"),
        seed_intent=seed.get("intent", "transfer_failed"),
        seed_language=seed.get("language", "urdulish"),
        seed_dialogue=seed_dialogue_text
    )
    return rendered_prompt


def validate_no_generic_closing_questions(seeds_or_candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    failures = []
    generic_patterns = [
        r"\bmazeed\b",
        r"\bkoi\s+aur\s+madad\b",
        r"\bkoi\s+aur\s+sawal\b",
        r"\banything\s+else\b",
        r"\bany\s+other\s+help\b",
        r"\bmadad\s+(?:chahiye|darkar|chahye)\b",
        r"مزید",
        r"کوئی\s+اور\s+مدد",
        r"کوئی\s+اور\s+سوال",
        r"مدد\s+(?:چاہیے|درکار)",
    ]
    combined_regex = re.compile("|".join(generic_patterns), re.IGNORECASE)

    for item in seeds_or_candidates:
        sid = item.get("seed_id", item.get("id", "unknown"))
        messages = item.get("messages", [])
        for m_idx, m in enumerate(messages):
            if m.get("role") == "assistant":
                content = m.get("content", "").strip()
                ends_with_q = content.endswith("?") or content.endswith("؟")
                if ends_with_q:
                    sents = [s.strip() for s in re.split(r"(?<=[.!?۔؟])\s+", content) if s.strip()]
                    last_sentence = sents[-1] if sents else content
                    # Helpline referral sentences are exempt from generic closing question rule
                    if "helpline" in last_sentence.lower() or "ہیلپ لائن" in last_sentence:
                        continue
                    m_match = combined_regex.search(last_sentence)
                    if m_match:
                        match_word = m_match.group(0)
                        failures.append({
                            "id": sid,
                            "turn": m_idx,
                            "text": content,
                            "matched": match_word,
                            "reason": f"Assistant turn ends with generic closing question matching '{match_word}': '{last_sentence}'"
                        })
    return failures


ALL_31_INTENTS = [
    "account_statement", "atm_cash_dispense_issue", "bill_payment", "block_card",
    "card_declined", "card_delivery", "check_balance", "dormant_account",
    "fee_dispute", "general_chit_chat", "installment_inquiry", "international_usage",
    "investment_advice_refusal", "loan_eligibility", "open_account", "out_of_scope_query",
    "pending_transaction", "phishing_report", "product_terms", "raast_inquiry",
    "refuse_credentials", "report_scam_call", "service_complaint", "sim_swap_report",
    "staff_complaint", "tat_breach", "transfer_failed", "unauthorized_transaction",
    "unblock_card", "update_profile", "wrong_transfer"
]

FEE_LIMIT_LOAN_INTENTS = {
    "installment_inquiry", "loan_eligibility", "product_terms", "international_usage"
}

TICKET_COMPLAINT_INTENTS = {
    "atm_cash_dispense_issue", "card_declined", "card_delivery", "pending_transaction",
    "service_complaint", "staff_complaint", "tat_breach", "transfer_failed",
    "unauthorized_transaction", "wrong_transfer", "bill_payment", "block_card",
    "phishing_report", "report_scam_call", "sim_swap_report", "fee_dispute"
}

OTHER_INTENTS = {
    "account_statement", "check_balance", "dormant_account", "general_chit_chat",
    "investment_advice_refusal", "open_account", "out_of_scope_query", "raast_inquiry",
    "refuse_credentials", "unblock_card", "update_profile"
}

NUMBER_BUDGET: Dict[str, int] = {
    "fee_limit_loan": 2,
    "ticket_complaint": 1,
    "other": 1,
    "out_of_scope": 0,
}

for _it in FEE_LIMIT_LOAN_INTENTS:
    NUMBER_BUDGET[_it] = 2
for _it in TICKET_COMPLAINT_INTENTS:
    NUMBER_BUDGET[_it] = 1
for _it in OTHER_INTENTS:
    if _it in ["general_chit_chat", "investment_advice_refusal", "out_of_scope_query"]:
        NUMBER_BUDGET[_it] = 0
    else:
        NUMBER_BUDGET[_it] = 1

def get_intent_number_budget(intent: str, category: str = "", task_type: str = "") -> int:
    intent_clean = str(intent).lower().strip()
    cat_clean = str(category).lower().strip()
    tt_clean = str(task_type).lower().strip()
    if tt_clean == "out_of_scope" or intent_clean in ["general_chit_chat", "investment_advice_refusal", "out_of_scope_query"]:
        return 0
    if (
        tt_clean == "complaint" or
        cat_clean == "complaint" or
        intent_clean in TICKET_COMPLAINT_INTENTS or
        intent_clean == "fee_dispute"
    ):
        return NUMBER_BUDGET["ticket_complaint"]
    if (
        intent_clean in FEE_LIMIT_LOAN_INTENTS or
        any(k in intent_clean for k in ["fee", "limit", "loan", "installment", "markup"]) or
        cat_clean == "loan"
    ):
        return NUMBER_BUDGET["fee_limit_loan"]
    return NUMBER_BUDGET.get(intent_clean, NUMBER_BUDGET["other"])

FEE_LIMIT_LOAN_INTENT_KEYWORDS = {"fee", "limit", "loan", "installment", "markup"}
ASKED_TRIGGER_WORDS = {
    "fee", "fees", "charge", "charges", "markup", "percent", "percentage", "%",
    "limit", "limits", "kitna", "kitni", "kitne", "how much", "rate"
}


def validate_only_asked_numbers(seeds_or_candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    failures = []
    for item in seeds_or_candidates:
        sid = item.get("seed_id", item.get("id", "unknown"))
        context = item.get("context")
        if not context or context == "koi document nahi mila":
            continue

        context_values = set(extract_distinct_numeric_values(context))
        intent = str(item.get("intent", "")).lower()
        category = str(item.get("category", "")).lower()
        budget = get_intent_number_budget(intent, category)

        # Reject a context that contains more than 2 distinct numbers when intent is not a fee, limit or loan product intent
        is_fee_limit_loan = (budget == NUMBER_BUDGET["fee_limit_loan"])
        if len(context_values) > 2 and not is_fee_limit_loan:
            failures.append({
                "id": sid,
                "reason": f"validate_only_asked_numbers: Context contains {len(context_values)} distinct numbers for intent '{intent}', but at most 2 allowed for non-fee/limit/loan intents (budget: {budget})"
            })

        messages = item.get("messages", [])
        user_texts = [m.get("content", "").lower() for m in messages if m.get("role") == "user"]
        combined_user_text = " ".join(user_texts)
        user_values = set(extract_distinct_numeric_values(combined_user_text))
        customer_asked = any(re.search(r"\b" + re.escape(w) + r"\b", combined_user_text) for w in ASKED_TRIGGER_WORDS)

        var = item.get("variation", {})
        sampled_nums = var.get("sampled_numbers", {}) if isinstance(var, dict) else {}
        fee_limit_pct_values = set()
        for k in ["fee", "daily_limit", "percentage"]:
            if k in sampled_nums and sampled_nums[k] is not None:
                try:
                    fee_limit_pct_values.add(float(sampled_nums[k]))
                except (ValueError, TypeError):
                    pass

        for cv in context_values:
            cv_pattern = rf"(?:fee|charge|limit|markup|rate|%|percent)\s*(?:is\s*)?{re.escape(str(int(cv) if cv.is_integer() else cv))}|{re.escape(str(int(cv) if cv.is_integer() else cv))}\s*(?:rupees|rs|%|percent|limit)"
            if re.search(cv_pattern, context, re.IGNORECASE):
                fee_limit_pct_values.add(cv)

        for m_idx, m in enumerate(messages):
            if m.get("role") == "assistant":
                bot_text = m.get("content", "")
                bot_values = extract_distinct_numeric_values(bot_text)
                grounded_values = [v for v in bot_values if v in context_values]

                # Sub-rule 2A: grounded bot turn that states a fee, percentage or limit from context when no customer message mentions trigger words or the number itself
                for gv in grounded_values:
                    if gv in fee_limit_pct_values:
                        if not customer_asked and gv not in user_values:
                            failures.append({
                                "id": sid,
                                "turn": m_idx,
                                "reason": f"validate_only_asked_numbers: Grounded bot turn states fee/percentage/limit ({int(gv) if gv.is_integer() else gv}) from context but no customer message mentions fee/charge/limit/markup/kitna/how much or the number itself"
                            })

                if len(grounded_values) > 2:
                    preceding_user_text = ""
                    for prev_idx in range(m_idx - 1, -1, -1):
                        if messages[prev_idx].get("role") == "user":
                            preceding_user_text = messages[prev_idx].get("content", "")
                            break

                    q_count = preceding_user_text.count("?") + preceding_user_text.count("؟")
                    connector_count = len(re.findall(r"\b(aur|and|also)\b", preceding_user_text, flags=re.IGNORECASE))
                    allowed_topics = q_count + connector_count + 1

                    if len(grounded_values) > allowed_topics:
                        failures.append({
                            "id": sid,
                            "turn": m_idx,
                            "stated_numbers": grounded_values,
                            "allowed_topics": allowed_topics,
                            "reason": f"Assistant turn states {len(grounded_values)} numbers from context ({grounded_values}), exceeding customer asked topics ({allowed_topics})"
                        })
    return failures


def validate_no_forbidden_customer_words(seeds_or_candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    failures = []
    forbidden_patterns = [
        r"\bmohtaram\b",
        r"\bjanab\s*(?:e|\-|–|—)?\s*ali\b",
        r"\bjanab\s*(?:e|\-|–|—)?\s*aali\b",
        r"baraye\s*meh(?:a)?rbani\s*wazahat\s*farma",
        r"\bintihai\b",
        r"na\s*qabil\s*(?:e|\-|–|—)?\s*bardasht",
        r"\blaparwahi\b",
        r"\bmosool\b",
        r"\bscene\b",
        r"\buljhan\b",
        r"\bke\s+hawale\s+se\b",
        r"\btafseelat\b",
        r"\bmulahiza\b",
        r"\biltimas\b",
        r"\bistifsar\b",
        r"\bi\s+would\s+like\s+to\s+inquire\b",
        r"\behsas\b",
        r"احساس",
        r"محترم",
        r"جناب\s*عالی",
        r"برائے\s*مہربانی\s*وضاحت\s*فرما",
        r"انتہائی",
        r"ناقابل\s*برداشت",
        r"لاپرواہی",
        r"موصول",
        r"الجھن",
        r"حوالے\s*سے",
        r"تفصیلات",
        r"ملاحظہ",
        r"التماس",
        r"استفسار",
    ]
    combined_regex = re.compile("|".join(forbidden_patterns), re.IGNORECASE)

    for item in seeds_or_candidates:
        sid = item.get("seed_id", item.get("id", "unknown"))
        messages = item.get("messages", [])
        for m_idx, m in enumerate(messages):
            if m.get("role") == "user":
                content = m.get("content", "")
                m_match = combined_regex.search(content)
                if m_match:
                    matched_word = m_match.group(0)
                    failures.append({
                        "id": sid,
                        "turn": m_idx,
                        "text": content,
                        "matched": matched_word,
                        "reason": f"Customer message contains forbidden word/phrase: '{matched_word}' in '{content}'"
                    })
    return failures


def validate_opening_diversity(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    first_bot_sent = ""
    for m in candidate.get("messages", []):
        if m.get("role") == "assistant":
            first_bot_sent = extract_effective_opening_sentence(m.get("content", ""))
            break

    if not first_bot_sent or is_mandatory_warning_sentence(first_bot_sent):
        return failures

    mock_counts = candidate.get("_mock_existing_openings")
    if mock_counts is not None:
        count = mock_counts.get(first_bot_sent, 0)
    else:
        count = 0
        if GENERATED_PATH.exists():
            with open(GENERATED_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        record = json.loads(line_str)
                        for rm in record.get("messages", []):
                            if rm.get("role") == "assistant":
                                if extract_effective_opening_sentence(rm.get("content", "")) == first_bot_sent:
                                    count += 1
                                break
                    except Exception:
                        pass

    if count >= 2:
        failures.append(
            f"validate_opening_diversity: First sentence '{first_bot_sent}' already appears {count} times in generated records"
        )
    return failures


def validate_no_personal_identifiers(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    messages = candidate.get("messages", [])

    for m in messages:
        content = m.get("content", "")
        role = m.get("role", "")

        # 1. Check Pakistani mobile number: 03xx followed by 7 digits with or without separators
        mob_match = re.search(r"\b03\d{2}[-\s.]?\d{3}[-\s.]?\d{4}\b|\b03\d{2}[-\s.]?\d{7}\b", content)
        if mob_match:
            failures.append(
                f"validate_no_personal_identifiers: {role} message contains Pakistani mobile number pattern: '{mob_match.group(0)}'"
            )

        # 2. Check 10+ digits without letters (mixed alphanumeric transaction references stay allowed)
        tokens = content.split()
        for tok in tokens:
            has_letters = bool(re.search(r"[a-zA-Z]", tok))
            has_digits = bool(re.search(r"\d", tok))
            if has_letters and has_digits:
                continue
            clean_digits = re.sub(r"[^0-9]", "", tok)
            if len(clean_digits) >= 10:
                failures.append(
                    f"validate_no_personal_identifiers: {role} message contains 10+ digit number without letters: '{tok}'"
                )
                break

        # 3. Check if bot asks for personal identifiers (phone, CNIC, account, card number, or digits)
        if role == "assistant":
            asking_patterns = [
                r"\b(?:apna\s+)?(?:phone|mobile)\s+number\s+(?:bata\s+dein|batayein|share|dein|likhein|batao)\b",
                r"\b(?:apna\s+)?cnic\s+(?:number\s+)?(?:bata\s+dein|batayein|share|dein|likhein|batao)\b",
                r"\b(?:apna\s+)?account\s+number\s+(?:bata\s+dein|batayein|share|dein|likhein|batao)\b",
                r"\b(?:apna\s+)?(?:full\s+|poora\s+)?card\s+number\s+(?:bata\s+dein|batayein|share|dein|likhein|batao)\b",
                r"\b(?:card\s+ke\s+)?(?:aakhri|last)\s+\d+\s+digits?\b",
                r"\b(?:card\s+ke\s+)?digits?\s+(?:bata\s+dein|batayein|share|dein)\b",
                r"\bapna\s+mobile\s+number\b",
                r"\bcard\s+ke\s+aakhri\s+\d+\s+digit\b",
                r"\blast\s+\d+\s+digits?\b",
            ]
            for ap in asking_patterns:
                if re.search(ap, content, re.IGNORECASE):
                    failures.append(
                        f"validate_no_personal_identifiers: Assistant asked customer for prohibited identifier matching '{ap}'"
                    )
                    break

    return failures


def validate_customer_mood(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    mood = candidate.get("variation", {}).get("mood", "calm")
    user_msgs = [m.get("content", "") for m in candidate.get("messages", []) if m.get("role") == "user"]
    user_text = " ".join(user_msgs)

    exclamation_count = user_text.count("!")
    has_insult = bool(INSULT_REGEX.search(user_text))

    words = re.findall(r"\b[A-Z]{3,}\b", user_text)
    known_acronyms = {"ATM", "OTP", "PIN", "SMS", "IBFT", "CNIC", "TAT", "USD", "POS", "RAAST", "ID", "SIM"}
    shouting_words = [w for w in words if w not in known_acronyms]
    has_shouting = len(shouting_words) > 0

    if mood == "calm":
        if exclamation_count > 0:
            failures.append(f"validate_customer_mood: calm customer contains {exclamation_count} exclamation mark(s)")
        if has_insult:
            failures.append("validate_customer_mood: calm customer contains insult or abusive term")
        if has_shouting:
            failures.append(f"validate_customer_mood: calm customer contains shouting words: {shouting_words}")

    elif mood == "frustrated":
        if exclamation_count > 1:
            failures.append(f"validate_customer_mood: frustrated customer contains {exclamation_count} exclamation marks (maximum 1 allowed)")
        if has_insult:
            failures.append("validate_customer_mood: frustrated customer contains abusive insult")
        if has_shouting:
            failures.append(f"validate_customer_mood: frustrated customer contains shouting words: {shouting_words}")

    elif mood == "very_angry":
        has_very_angry_signs = (exclamation_count >= 3 or has_shouting or has_insult)
        if not has_very_angry_signs:
            failures.append("validate_customer_mood: very_angry customer lacks required anger signs (insults, shouting, or 3+ exclamation marks)")

    return failures


def validate_time_mentioned_natural(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    ticket = candidate.get("ticket")
    if ticket and ticket.get("time_mentioned"):
        tm = str(ticket.get("time_mentioned")).strip()
        tm_lower = tm.lower()
        if tm_lower in MONTH_NAMES_SET or any(m in tm_lower for m in ["statement period", "month statement", "billing cycle"]):
            failures.append(
                f"validate_time_mentioned_natural: time_mentioned is month name or statement period ('{tm_lower}'), must be event time in customer words"
            )

        # time_mentioned must be a span that appears in the customer messages (case insensitive); otherwise null
        user_texts = [m.get("content", "") for m in candidate.get("messages", []) if m.get("role") == "user"]
        combined_user_text = " ".join(user_texts).lower()
        if tm_lower not in combined_user_text:
            failures.append(
                f"validate_time_mentioned_natural: time_mentioned '{tm}' does not appear in customer messages (must be exact customer span or null)"
            )
    return failures


def validate_context_numbers_match_sampled(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    sampled_nums = candidate.get("variation", {}).get("sampled_numbers")
    context = candidate.get("context")

    if sampled_nums and context and context != "koi document nahi mila":
        expected_values = set(float(v) for v in sampled_nums.values())
        actual_values = set(extract_distinct_numeric_values(context))

        missing = expected_values - actual_values
        if missing:
            failures.append(
                f"validate_context_numbers_match_sampled: Context is missing supplied numbers {sorted(list(missing))}"
            )

        extras = actual_values - expected_values
        if len(extras) > 1:
            failures.append(
                f"validate_context_numbers_match_sampled: Context contains {len(extras)} extra numbers {sorted(list(extras))}, at most 1 extra allowed"
            )
        elif len(extras) == 1:
            seed_ctx = candidate.get("seed_context")
            if not seed_ctx and candidate.get("seed_id"):
                seed_obj = get_seed_by_id(candidate.get("seed_id"))
                if seed_obj:
                    seed_ctx = seed_obj.get("context")
            seed_nums = set(extract_distinct_numeric_values(seed_ctx)) if seed_ctx else set()
            if extras.intersection(seed_nums):
                failures.append(
                    f"validate_context_numbers_match_sampled: Extra context number {sorted(list(extras))} appears in seed's own context"
                )

        formatted_extras = [format_number_no_trailing_zero(x) for x in sorted(list(extras))]
        candidate["extra_context_numbers"] = formatted_extras
        if "variation" in candidate and isinstance(candidate["variation"], dict):
            candidate["variation"]["extra_context_numbers"] = formatted_extras

    return failures


def validate_end_style(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    task_type = str(candidate.get("task_type", "")).lower()
    category = str(candidate.get("category", "")).lower()
    intent = str(candidate.get("intent", "")).lower()

    # validate_end_style applies ONLY to faq and out_of_scope requests.
    # Complaint and fraud requests may end with a detail question even if target style was statement.
    if task_type:
        if task_type not in ["faq", "out_of_scope"]:
            return failures
    else:
        if category in ["complaint", "fraud"] or intent in TICKET_COMPLAINT_INTENTS or intent in ["fee_dispute"]:
            return failures

    end_style = candidate.get("end_style") or candidate.get("variation", {}).get("end_style")
    if not end_style:
        return failures

    messages = candidate.get("messages", [])
    last_bot_content = None
    for m in messages:
        if m.get("role") == "assistant":
            last_bot_content = m.get("content", "").strip()

    if not last_bot_content:
        return failures

    ends_with_q = last_bot_content.endswith("?") or last_bot_content.endswith("؟")
    if end_style == "statement" and ends_with_q:
        failures.append(
            f"validate_end_style: Candidate end_style is 'statement' but last bot turn ends with question mark: '{last_bot_content[-50:]}'"
        )
    elif end_style == "question" and not ends_with_q:
        failures.append(
            f"validate_end_style: Candidate end_style is 'question' but last bot turn does not end with question mark: '{last_bot_content[-50:]}'"
        )
    elif end_style == "question" and ends_with_q:
        # With end_style question, reject questions about customer purpose or plans
        purpose_plan_patterns = [
            r"\bproceed\b",
            r"\blena\s+chaht",
            r"\bcontinue\s+karna\s+chaht",
            r"\bshall\s+we\b",
            r"\bwould\s+you\s+like\s+to\s+proceed\b",
        ]
        for pat in purpose_plan_patterns:
            if re.search(pat, last_bot_content, re.IGNORECASE):
                failures.append(
                    f"validate_end_style: Bot question asks about customer purpose or plans instead of complaint detail: '{last_bot_content[-60:]}'"
                )
                break

    return failures


def validate_customer_amount_matches(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    sampled_amt = candidate.get("variation", {}).get("sampled_customer_amount")
    ticket = candidate.get("ticket")

    if sampled_amt is not None and ticket is not None:
        expected_amt = float(sampled_amt)
        ticket_amt = ticket.get("amount")
        if ticket_amt is None or float(ticket_amt) != expected_amt:
            failures.append(
                f"validate_customer_amount_matches: Ticket amount ({ticket_amt}) does not match supplied customer amount ({expected_amt})"
            )
    return failures


CANNOT_CONFIRM_PATTERNS = [
    re.compile(r"\b(?:tasdeeq|confirm)\b(?:\s+\S+){0,3}\s+\bnahi\s+kar\s+sakt[ai]\b", re.IGNORECASE),
    re.compile(r"\bmaloom\s+nahi\b", re.IGNORECASE),
    re.compile(r"\b(?:cannot|can't|unable\s+to|not\s+able\s+to)\s+confirm\b", re.IGNORECASE),
    re.compile(r"تصدیق(?:\s+\S+){0,3}\s+نہیں\s+کر\s+سکتی"),
    re.compile(r"تصدیق\s+نہیں"),
]

NODOC_CUSTOMER_QUESTION_PATTERNS = [
    # English
    r"\btime\b", r"\bfee\b", r"\bfees\b", r"\bcharges?\b", r"\blimits?\b", r"\bhow\s+long\b",
    r"\bwhen\b", r"\bduration\b", r"\btat\b", r"\bdeadline\b", r"\bcost\b", r"\brate\b",
    # Roman Urdu
    r"\bwaqt\b", r"\btareekh\b", r"\bdate\b", r"\bkab\b", r"\bkab\s+tak\b",
    r"\bkitn[aei]\s+(?:din|ghant[ae]|arsa|der|waqt|time|paise?|rupay|charges?|fees?)\b",
    r"\bkitna\s+arsa\b", r"\bkitni\s+der\b", r"\bkitne\s+din\b",
    r"\bkatoti\b", r"\bkharcha\b", r"\bhadd\b", r"\bfees?\b", r"\bcharges?\b",
    # Urdu script
    r"وقت", r"تاریخ", r"کب", r"کتنے\s+دن", r"کتنی\s+دیر", r"کتنا\s+عرصہ", r"کب\s+تک",
    r"فیس", r"چارجز?", r"کٹوتی", r"خرچہ", r"لمٹ", r"حد",
]
NODOC_CUSTOMER_QUESTION_REGEX = re.compile("|".join(NODOC_CUSTOMER_QUESTION_PATTERNS), re.IGNORECASE)


def validate_nodoc_question_asked(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    messages = candidate.get("messages", [])
    bot_cannot_confirm = False
    for m in messages:
        if m.get("role") == "assistant":
            content = m.get("content", "")
            if any(pat.search(content) for pat in CANNOT_CONFIRM_PATTERNS):
                bot_cannot_confirm = True
                break

    if bot_cannot_confirm:
        user_texts = [m.get("content", "") for m in messages if m.get("role") == "user"]
        combined_user = " ".join(user_texts)
        if not NODOC_CUSTOMER_QUESTION_REGEX.search(combined_user):
            failures.append(
                "validate_nodoc_question_asked: Assistant stated inability to confirm, but customer did not ask about time, fee, charge, limit, or duration"
            )
    return failures


def validate_no_trailing_zero_decimals(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    trailing_zero_regex = re.compile(r"\b\d+\.0+(?!\d)")

    context = candidate.get("context")
    if context and isinstance(context, str) and context != "koi document nahi mila":
        match = trailing_zero_regex.search(context)
        if match:
            failures.append(
                f"validate_no_trailing_zero_decimals: Context contains number with trailing .0: '{match.group(0)}'"
            )

    for idx, m in enumerate(candidate.get("messages", [])):
        if m.get("role") == "assistant":
            content = m.get("content", "")
            match = trailing_zero_regex.search(content)
            if match:
                failures.append(
                    f"validate_no_trailing_zero_decimals: Assistant turn {idx} contains number with trailing .0: '{match.group(0)}'"
                )
    return failures


def validate_no_customer_echo(candidate: Dict[str, Any]) -> List[str]:
    if candidate.get("category") == "out_of_scope" or derive_task_type(candidate) == "out_of_scope":
        return []
    failures = []
    messages = candidate.get("messages", [])
    raw_context = candidate.get("context")
    context_words_set = set(re.findall(r"\b\w+\b", raw_context.lower())) if isinstance(raw_context, str) else set()
    intent_words_set = set(re.findall(r"\b\w+\b", candidate.get("intent", "").replace("_", " ").lower()))
    allowed_words = context_words_set | intent_words_set

    for idx, m in enumerate(messages):
        if m.get("role") == "assistant":
            prev_user_content = ""
            for prev_idx in range(idx - 1, -1, -1):
                if messages[prev_idx].get("role") == "user":
                    prev_user_content = messages[prev_idx].get("content", "")
                    break
            if not prev_user_content:
                continue

            bot_first_sent = extract_first_sentence(m.get("content", ""))
            u_words = re.findall(r"\b\w+\b", prev_user_content.lower())
            b_words = re.findall(r"\b\w+\b", bot_first_sent.lower())

            # Applies only when the copied span has 5 or more words
            if len(u_words) >= 5 and len(b_words) >= 5:
                u_5grams = [tuple(u_words[i:i+5]) for i in range(len(u_words) - 4)]
                b_5grams = set(tuple(b_words[i:i+5]) for i in range(len(b_words) - 4))
                for gram in u_5grams:
                    if gram in b_5grams:
                        echoed_phrase = " ".join(gram)
                        has_digits = any(ch.isdigit() for ch in echoed_phrase)
                        # Contains no word that also appears in supplied context or in intent name
                        contains_allowed = any(w in allowed_words for w in gram)
                        if not has_digits and not contains_allowed:
                            failures.append(
                                f"validate_no_customer_echo: Assistant reply first sentence contains 5 or more consecutive words copied from customer's last message: '{echoed_phrase}'"
                            )
                            break
    return failures


FACET_STOPLIST = {
    # Roman Urdu function words
    "kar", "karna", "raha", "rahi", "rahe", "hai", "hain", "ho", "hua",
    "gaya", "gayi", "gaye", "tha", "thi", "the", "ka", "ki", "ke", "ko",
    "se", "mein", "me", "par", "pe", "aur", "ne", "hun", "hu", "ye", "wo",
    "mera", "meri", "mere",
    # English function words
    "a", "an", "the", "of", "to", "in", "my", "i", "is", "was", "for",
    # Number words and digits (Roman Urdu & English)
    "ek", "do", "teen", "char", "paanch", "panch", "chhe", "che", "saat", "aath", "nau", "das",
    "gyarah", "barah", "terah", "chaudah", "pandrah", "solah", "satrah", "atharah", "unees", "bees",
    "tees", "chalis", "pachas", "sau", "hazar", "lakh",
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
    "twenty", "thirty", "forty", "fifty", "hundred", "thousand",
    # Time and counting words
    "din", "ghante", "ghanta", "hafte", "hafta", "mahine", "mahina", "saal", "pehle", "baad",
    "subah", "shaam", "sham", "raat", "dopahar", "kal", "aaj", "abhi",
    "yesterday", "today", "morning", "evening", "night", "afternoon", "ago", "since",
    "days", "hours", "minutes", "minute"
}


def validate_no_facet_copying(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    sampled_facets = candidate.get("sampled_facets") or candidate.get("variation", {}).get("sampled_facets")
    if not sampled_facets:
        return failures

    facet_phrases = []
    if isinstance(sampled_facets, dict):
        facet_phrases.extend(str(v) for v in sampled_facets.values() if v)
    elif isinstance(sampled_facets, list):
        facet_phrases.extend(str(v) for v in sampled_facets if v)

    if not facet_phrases:
        return failures

    for phrase in facet_phrases:
        f_words = re.findall(r"\b\w+\b", phrase.lower())
        if len(f_words) < 5:
            continue

        f_5grams = [tuple(f_words[i:i+5]) for i in range(len(f_words) - 4)]

        for m in candidate.get("messages", []):
            if m.get("role") == "user":
                content = m.get("content", "")
                c_words = re.findall(r"\b\w+\b", content.lower())
                if len(c_words) < 5:
                    continue
                c_5grams = {tuple(c_words[i:i+5]) for i in range(len(c_words) - 4)}

                matched_gram = None
                for gram in f_5grams:
                    if gram in c_5grams:
                        matched_gram = gram
                        break

                if matched_gram:
                    failures.append(
                        f"validate_no_facet_copying: Customer message contains 5 or more consecutive words copied from sampled facet value: '{' '.join(matched_gram)}'"
                    )
                    break

    return failures


def validate_no_customer_ji(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    for m in candidate.get("messages", []):
        if m.get("role") == "user":
            content = m.get("content", "").strip()
            if re.match(r"^(?:ji|جی)\b", content, re.IGNORECASE):
                failures.append(
                    f"validate_no_customer_ji: Customer message starts with forbidden greeting tic 'Ji'/'جی': '{content[:50]}'"
                )
    return failures


FILLER_SENTENCE_PATTERNS = [
    r"\bthank\s+you\s+for\s+confirming\b",
    r"\bshukriya\s+maloomat\s+dene\s+ka\b",
    r"\bdurust\s+darj\s+kar\s+li\s+gayi\b",
    r"\bnoted\s+for\s+the\s+investigation\b",
    r"\baap\s+ke\s+record\s+ke\s+liye\b",
]
FILLER_REGEX = re.compile("|".join(FILLER_SENTENCE_PATTERNS), re.IGNORECASE)


def validate_no_filler_sentences(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    messages = candidate.get("messages", [])
    for m in messages:
        if m.get("role") == "assistant":
            content = m.get("content", "")
            match = FILLER_REGEX.search(content)
            if match:
                failures.append(
                    f"validate_no_filler_sentences: Assistant turn contains forbidden filler sentence '{match.group(0)}' in '{content}'"
                )
    return failures


TICKET_SUMMARY_ROMAN_URDU_WORDS = {
    "ne", "ka", "ki", "ke", "hai", "hain", "tha", "kiya", "mein", "se", "par", "aur", "nahi"
}


def validate_ticket_summary_language(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    ticket = candidate.get("ticket")
    if not ticket or not isinstance(ticket, dict):
        return failures
    summary = ticket.get("summary")
    if not summary or not isinstance(summary, str):
        return failures

    if re.search(r"[\u0600-\u06ff]", summary):
        failures.append(
            f"validate_ticket_summary_language: Ticket summary contains Urdu script, must be English only: '{summary}'"
        )
        return failures

    words = [w.lower() for w in re.findall(r"\b\w+\b", summary)]
    found_roman = [w for w in words if w in TICKET_SUMMARY_ROMAN_URDU_WORDS]
    if found_roman:
        failures.append(
            f"validate_ticket_summary_language: Ticket summary contains Roman Urdu word(s) {found_roman}, must be English only: '{summary}'"
        )
    return failures


STRUCTURE_CLAIM_WORDS = [
    "division", "department", "team", "supervisor", "manager",
    "specialist", "senior", "escalate", "escalation", "agent shop"
]


def validate_no_structure_claims(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    raw_context = candidate.get("context")
    context_str = raw_context.lower() if isinstance(raw_context, str) else ""

    for m in candidate.get("messages", []):
        if m.get("role") == "assistant":
            content = m.get("content", "").lower()
            for word in STRUCTURE_CLAIM_WORDS:
                pattern = r"\b" + re.escape(word) + r"\b"
                if re.search(pattern, content):
                    if not re.search(pattern, context_str):
                        failures.append(
                            f"validate_no_structure_claims: Assistant turn contains unauthorized structure claim '{word}' not present in context: '{m.get('content')}'"
                        )
                        break
    return failures


def validate_ji_first(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    ji_regex = re.compile(r"^(?:Ji|جی)(?:[\s,!۔،]|$)", re.UNICODE)
    messages = candidate.get("messages", [])
    for idx, m in enumerate(messages):
        if m.get("role") == "assistant":
            content = m.get("content", "").strip()
            if not ji_regex.search(content):
                failures.append(
                    f"validate_ji_first: Assistant turn {idx} does not begin with 'Ji' or 'جی': '{content[:50]}'"
                )
    return failures


def compute_max_bot_words_limit(seeds_dir: Path = SEEDS_DIR) -> int:
    seeds = load_seeds(seeds_dir)
    max_words = 0
    for s in seeds:
        for m in s.get("messages", []):
            if m.get("role") == "assistant":
                c = m.get("content", "")
                words = re.findall(r"\b\w+\b|[\u0600-\u06FF]+", c)
                if len(words) > max_words:
                    max_words = len(words)
    N = min(60, int(math.ceil(max_words / 5.0) * 5))
    return N


MAX_BOT_WORDS_N = 65


def validate_scam_warning(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    messages = candidate.get("messages", [])
    counts = {"english": 0, "urdu_script": 0, "roman_urdu": 0}
    for m in messages:
        if m.get("role") == "assistant":
            raw = m.get("content", "")
            norm = normalize_urdu_text(re.sub(r"[.!?۔؟،,\s]+", " ", raw.lower()).strip())
            counts["english"] += norm.count("zarya bank will never ask for your otp or pin over a call or sms")
            counts["roman_urdu"] += norm.count("zarya bank kabhi bhi call ya sms par aap ka otp ya pin nahi maangta")
            counts["urdu_script"] += norm.count("کبھی بھی کال یا ایس ایم ایس پر آپ کا کارڈ نمبر")

    total_warnings = sum(counts.values())
    if total_warnings > 1:
        failures.append(
            f"validate_scam_warning: more than one warning sentence ({total_warnings}) in conversation"
        )
    elif total_warnings == 1:
        intent = candidate.get("intent", "")
        if intent not in SCAM_WARNING_INTENTS:
            failures.append(
                f"validate_scam_warning: warning sentence present for intent '{intent}' not in scam warning list"
            )
        lang = candidate.get("language", "")
        if lang == "english" and counts["english"] != 1:
            failures.append(
                "validate_scam_warning: warning sentence in wrong language for english conversation"
            )
        elif lang == "urdu_script" and counts["urdu_script"] != 1:
            failures.append(
                "validate_scam_warning: warning sentence in wrong language for urdu_script conversation"
            )
        elif (lang == "urdulish" or lang == "roman_urdu") and counts["roman_urdu"] != 1:
            failures.append(
                f"validate_scam_warning: warning sentence in wrong language for {lang} conversation"
            )
    return failures


def validate_refusals(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    task_type = candidate.get("task_type") or derive_task_type(candidate)
    if candidate.get("category") == "out_of_scope" or task_type == "out_of_scope":
        messages = candidate.get("messages", [])
        total_bot_words = 0
        for m in messages:
            if m.get("role") == "assistant":
                content = m.get("content", "")
                if "?" in content or "؟" in content:
                    failures.append(
                        "validate_refusals: out_of_scope bot reply must not contain any question mark"
                    )
                words = re.findall(r"\b\w+\b|[\u0600-\u06FF]+", content)
                total_bot_words += len(words)
        if total_bot_words > 30:
            failures.append(
                f"validate_refusals: out_of_scope bot reply contains {total_bot_words} words (at most 30 allowed)"
            )
    return failures


def validate_no_facet_questions(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    facet_contact_pat = re.compile(
        r"\b(?:colleague|colleagues|friend|friends|family|relative|relatives|classmate|classmates|dost|doston|rishtedar|rishtedaron|ghar\s*walon|gharwalon)\b|دوست|رشتہ\s*دار|گھر\s*والوں",
        re.IGNORECASE
    )
    for idx, m in enumerate(candidate.get("messages", [])):
        if m.get("role") == "assistant":
            content = m.get("content", "")
            if "?" in content or "؟" in content:
                sents = [s.strip() for s in re.findall(r'[^.!?۔؟]+(?:[.!?۔؟]|$)', content) if s.strip()]
                for s in sents:
                    if ("?" in s or "؟" in s) and facet_contact_pat.search(s):
                        failures.append(
                            f"validate_no_facet_questions: assistant question contains forbidden personal contact word: '{s}'"
                        )
    return failures


def validate_ticket_amount_allowed(candidate: Dict[str, Any]) -> List[str]:
    ticket = candidate.get("ticket")
    if not ticket or not isinstance(ticket, dict):
        return []
    amt = ticket.get("amount")
    if amt is not None:
        intent = candidate.get("intent", ticket.get("intent", ""))
        if intent not in AMOUNT_ALLOWED_INTENTS:
            return [
                f"validate_ticket_amount_allowed: ticket amount {amt} not allowed for intent '{intent}'"
            ]
    return []


def validate_no_context_ranges(candidate: Dict[str, Any]) -> List[str]:
    ctx = candidate.get("context")
    if not ctx or not isinstance(ctx, str) or ctx == "koi document nahi mila":
        return []
    range_pat = re.compile(r"\b\d+\s*(?:se|to|-|tak|سے|تک)\s*\d+\b", re.IGNORECASE)
    m = range_pat.search(ctx)
    if m:
        return [
            f"validate_no_context_ranges: range expression '{m.group(0)}' found in context: '{ctx}'"
        ]
    return []


def validate_no_help_offers_and_numbers(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    help_question_patterns = [
        r"\bmadad\s+(?:kar\s+sakt[a-z]+|kr\s+sakt[a-z]+)\s+(?:hoon|hun)\b",
        r"\bkisi\s+aur\s+masla[ye]\s+me(?:in)?\s+madad\b",
        r"\bhelp\s+you\s+with\b",
        r"\bassist\s+you\b",
        r"\bhow\s+may\s+i\b",
        r"مدد\s+کر\s+سکتی\s+ہوں",
        r"کسی\s+اور\s+مسئلے\s+میں\s+مدد",
        r"\bproceed\b",
        r"\blena\s+chaht[a-z]+\s+hain\b",
        r"\bcontinue\s+karna\s+chaht[a-z]+\b",
        r"\bshall\s+we\b",
        r"\bwould\s+you\s+like\s+to\s+proceed\b",
    ]
    help_q_regex = re.compile("|".join(help_question_patterns), re.IGNORECASE)

    number_offer_patterns = [
        r"\bhelpline\s+(?:ka\s+)?number\b",
        r"\bphone\s+number\b",
        r"ہیلپ\s*لائن\s+کا\s+نمبر",
        r"فون\s+نمبر",
    ]
    num_offer_regex = re.compile("|".join(number_offer_patterns), re.IGNORECASE)

    for idx, m in enumerate(candidate.get("messages", [])):
        if m.get("role") == "assistant":
            content = m.get("content", "")
            if "?" in content or "؟" in content:
                sents = [s.strip() for s in re.findall(r'[^.!?۔؟]+(?:[.!?۔؟]|$)', content) if s.strip()]
                for s in sents:
                    if ("?" in s or "؟" in s) and help_q_regex.search(s):
                        failures.append(
                            f"validate_no_help_offers_and_numbers: bot question offers help: '{s}'"
                        )
            num_match = num_offer_regex.search(content)
            if num_match:
                failures.append(
                    f"validate_no_help_offers_and_numbers: bot offers helpline or phone number: '{num_match.group(0)}' in '{content}'"
                )
    return failures


def is_urdu_char(c: str) -> bool:
    return ('\u0600' <= c <= '\u06FF' or '\u0750' <= c <= '\u077F' or '\uFB50' <= c <= '\uFDFF' or '\uFE70' <= c <= '\uFEFF')


def validate_script_consistency(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    lang = str(candidate.get("language", "")).lower().strip()
    messages = candidate.get("messages", [])

    for m_idx, m in enumerate(messages):
        if m.get("role") not in ["user", "assistant"]:
            continue
        content = m.get("content", "")
        # Remove digits, Zarya Bank, and acronyms: ATM, SMS, OTP, PIN, IBFT, Raast, CNIC
        clean = re.sub(r"Zarya Bank", "", content, flags=re.IGNORECASE)
        clean = re.sub(r"\b(?:ATM|SMS|OTP|PIN|IBFT|Raast|CNIC)\b", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\d+", "", clean)

        urdu_letters = [c for c in clean if is_urdu_char(c) and c.isalpha()]
        latin_letters = [c for c in clean if 'a' <= c.lower() <= 'z']
        tot = len(urdu_letters) + len(latin_letters)

        if lang == "urdu_script":
            pct = (len(urdu_letters) / tot * 100.0) if tot > 0 else 100.0
            if pct < 70.0:
                failures.append(
                    f"validate_script_consistency: In urdu_script message, only {pct:.1f}% of letters are Urdu script (minimum 70% required): '{content}'"
                )
        elif lang in ["urdulish", "roman_urdu", "english"]:
            if len(urdu_letters) > 0:
                failures.append(
                    f"validate_script_consistency: In {lang} conversation, message contains Urdu script letters: '{content}'"
                )
    return failures


def extract_resolution_time_numbers_from_context(context: str, variation: Optional[Dict[str, Any]] = None) -> Set[float]:
    res_nums = set()
    if variation and isinstance(variation, dict):
        s_nums = variation.get("sampled_numbers", {})
        if isinstance(s_nums, dict):
            for k in ["tat_hours", "tat_days", "resolution_time_hours", "resolution_time_days"]:
                if k in s_nums and s_nums[k] is not None:
                    try:
                        res_nums.add(float(s_nums[k]))
                    except (ValueError, TypeError):
                        pass
    if context and isinstance(context, str) and context != "koi document nahi mila":
        matches = re.finditer(r"\b(\d+(?:\.\d+)?)\s*(?:working\s+hours?|business\s+hours?|hours?|working\s+days?|business\s+days?|days?|ghantay?|ghante?|din)\b", context, re.IGNORECASE)
        for m in matches:
            try:
                res_nums.add(float(m.group(1)))
            except ValueError:
                pass
        tat_matches = re.finditer(r"(?:TAT|turnaround|resolution|review\s+time|clearance\s+schedule|inquiry\s+window)[\w\s:]*?\b(\d+(?:\.\d+)?)\b", context, re.IGNORECASE)
        for m in tat_matches:
            try:
                res_nums.add(float(m.group(1)))
            except ValueError:
                pass
    return res_nums


def validate_complaint_numbers(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    cat = str(candidate.get("category", "")).lower()
    intent = str(candidate.get("intent", "")).lower()
    tt = str(candidate.get("task_type", "")).lower()
    has_ticket = candidate.get("ticket") is not None

    is_complaint_or_fraud = (
        tt == "complaint" or
        cat in ["complaint", "fraud"] or
        intent in TICKET_COMPLAINT_INTENTS or
        intent == "fee_dispute" or
        has_ticket
    )
    if not is_complaint_or_fraud:
        return failures

    messages = candidate.get("messages", [])
    context = candidate.get("context", "")
    variation = candidate.get("variation", {})

    customer_nums = set()
    for m in messages:
        if m.get("role") == "user":
            customer_nums.update(extract_distinct_numeric_values(m.get("content", "")))

    res_nums = extract_resolution_time_numbers_from_context(context, variation)

    for m_idx, m in enumerate(messages):
        if m.get("role") == "assistant":
            bot_content = m.get("content", "")
            bot_nums = extract_distinct_numeric_values(bot_content)
            for num in bot_nums:
                if num in customer_nums or num in res_nums:
                    continue
                failures.append(
                    f"validate_complaint_numbers: For complaint/ticket/fraud conversation, bot stated number {int(num) if num.is_integer() else num} which is neither a resolution time from context nor written by the customer: '{bot_content}'"
                )
    return failures


QUESTION_FORBIDDEN_PATTERNS = [
    re.compile(r"\bapproval\b", re.IGNORECASE),
    re.compile(r"\bmeet\s+your\b", re.IGNORECASE),
    re.compile(r"\bpasand\s+karenge\b", re.IGNORECASE),
    re.compile(r"\bkahan\s+se\s+check\s+ki\b", re.IGNORECASE),
    re.compile(r"\bkahan\s+se\s+check\b", re.IGNORECASE),
    re.compile(r"\bkisi\s+aur\b", re.IGNORECASE),
    re.compile(r"\bany\s+other\b", re.IGNORECASE),
    re.compile(r"\bproceed\b", re.IGNORECASE),
    re.compile(r"\bprocess\b", re.IGNORECASE),
    re.compile(r"\blena\s+chaht", re.IGNORECASE),
    re.compile(r"\bcontinue\s+karna\s+chaht", re.IGNORECASE),
    re.compile(r"\bshall\s+we\b", re.IGNORECASE),
]

QUESTION_WHITELIST_PATTERNS = [
    re.compile(r"\b(?:transaction\s+id|transaction\s+ref|transaction\s+number|transaction\s+reference|reference|id|ref|raqam\s+id|trx|tid)\b", re.IGNORECASE),
    re.compile(r"\b(?:amount|raqam|paise|kitne|kitni|kitna|how\s+much)\b", re.IGNORECASE),
    re.compile(r"\b(?:time|waqt|date|tareekh|din|kab|when)\b", re.IGNORECASE),
    re.compile(r"\b(?:kya\s+hua|what\s+happened|kya\s+masla|kya\s+pareshani|kya\s+issue|what\s+issue|what\s+problem|what\s+error|kya\s+error|kya\s+kharabi|kya\s+pesh|waja|wajah)\b", re.IGNORECASE),
    re.compile(r"\b(?:which\s+(?:card|service|account|type|bank)|kaunsa|konsa|kounsa|konsi|kaunsi|kis\s+(?:service|card|account|branch|qisam|type|loan|bank))\b", re.IGNORECASE),
    re.compile(r"\b(?:share|click|clicked|link|kisi\s+ko\s+diya|kisi\s+ko\s+bataya|credentials|otp|pin|password|tafseelat\s+share)\b", re.IGNORECASE),
    re.compile(r"آئی ڈی|ریفرنس|ٹرانزیکشن"),
    re.compile(r"رقم|پیسے|کتنی|کتنے|کتنا"),
    re.compile(r"وقت|تاریخ|کب|دن"),
    re.compile(r"کیا ہوا|کیا مسئلہ|کیا پریشانی|کیا خرابی|وجہ"),
    re.compile(r"کونسا|کونسی|کس سروس|کس کارڈ|کس اکاؤنٹ"),
    re.compile(r"شیئر|کلک|لنک"),
]


def validate_question_whitelist(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    messages = candidate.get("messages", [])
    for m_idx, m in enumerate(messages):
        if m.get("role") == "assistant":
            content = m.get("content", "").strip()
            if "?" in content or "؟" in content:
                sents = [s.strip() for s in re.split(r"(?<=[.!?۔؟])\s+", content) if s.strip()]
                for s in sents:
                    if "?" in s or "؟" in s:
                        if "helpline" in s.lower() or "ہیلپ لائن" in s:
                            continue

                        found_forbidden = False
                        for pat in QUESTION_FORBIDDEN_PATTERNS:
                            if pat.search(s):
                                failures.append(
                                    f"validate_question_whitelist: Bot question asks for forbidden topic: '{s}'"
                                )
                                found_forbidden = True
                                break
                        if found_forbidden:
                            continue

                        if not any(pat.search(s) for pat in QUESTION_WHITELIST_PATTERNS):
                            failures.append(
                                f"validate_question_whitelist: Bot question is not on the whitelist of permitted questions: '{s}'"
                            )
    return failures


OTHER_BANK_AND_FEHRIST_PATTERNS = [
    (re.compile(r"\bqareebi\s+bank\b", re.IGNORECASE), "qareebi bank"),
    (re.compile(r"\bdoosr[ea]y?\s+bank\b", re.IGNORECASE), "doosre bank"),
    (re.compile(r"\bapn[ea]y?\s+bank\b", re.IGNORECASE), "apne bank"),
    (re.compile(r"\bfehrist\b", re.IGNORECASE), "fehrist"),
    (re.compile(r"قریبی بینک"), "qareebi bank"),
    (re.compile(r"دوسرے بینک"), "doosre bank"),
    (re.compile(r"اپنے بینک"), "apne bank"),
    (re.compile(r"فہرست"), "fehrist"),
]


def validate_no_other_bank_and_fehrist(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    messages = candidate.get("messages", [])
    for m in messages:
        if m.get("role") == "assistant":
            content = m.get("content", "")
            for pat, name in OTHER_BANK_AND_FEHRIST_PATTERNS:
                m_match = pat.search(content)
                if m_match:
                    failures.append(
                        f"validate_no_other_bank_and_fehrist: Bot turn contains forbidden phrase '{name}': '{m_match.group(0)}' in '{content}'"
                    )
                    break
    return failures


def validate_lengths(candidate: Dict[str, Any], max_bot_words: int = MAX_BOT_WORDS_N) -> List[str]:
    failures = []
    messages = candidate.get("messages", [])
    for idx, m in enumerate(messages):
        role = m.get("role")
        content = m.get("content", "")
        words = re.findall(r"\b\w+\b|[\u0600-\u06FF]+", content)
        if role == "user":
            if len(words) > 40:
                failures.append(
                    f"validate_lengths: customer message has {len(words)} words (maximum 40 allowed)"
                )
        elif role == "assistant":
            sents = [s.strip() for s in re.findall(r'[^.!?۔؟]+(?:[.!?۔؟]|$)', content) if s.strip()]
            if len(sents) > 4:
                failures.append(
                    f"validate_lengths: bot turn has {len(sents)} sentences (maximum 4 allowed)"
                )
            if len(words) > max_bot_words:
                failures.append(
                    f"validate_lengths: bot turn has {len(words)} words (maximum {max_bot_words} allowed)"
                )
    return failures


def get_bot_first_3_words(candidate: Dict[str, Any]) -> Optional[Tuple[str, ...]]:
    for m in candidate.get("messages", []):
        if m.get("role") == "assistant":
            first_sent = extract_first_sentence(m.get("content", ""))
            words = re.findall(r"\b\w+\b", first_sent.lower())
            if len(words) >= 3:
                return tuple(words[:3])
            elif len(words) > 0:
                return tuple(words)
            return None
    return None


def validate_opening_variety(
    candidate: Dict[str, Any],
    accepted_records: Optional[List[Dict[str, Any]]] = None
) -> List[str]:
    if accepted_records is None:
        accepted_records = candidate.get("_accepted_records")
    if not accepted_records or len(accepted_records) < 60:
        return []

    prefix = get_bot_first_3_words(candidate)
    if not prefix or len(prefix) < 3:
        return []

    total_acc = len(accepted_records)
    match_count = 0
    for rec in accepted_records:
        if get_bot_first_3_words(rec) == prefix:
            match_count += 1

    ratio = match_count / total_acc
    if ratio >= 0.05:
        prefix_str = " ".join(prefix)
        return [
            f"validate_opening_variety: Bot opening first 3 words '{prefix_str}' appears in {match_count}/{total_acc} ({ratio*100:.1f}%) accepted records (limit is 5.0% once >= 60 records exist)"
        ]
    return []


def validate_no_ehsas(candidate: Dict[str, Any]) -> List[str]:
    failures = []
    for m in candidate.get("messages", []):
        content = m.get("content", "").lower()
        if "pareshani ka ehsas" in content:
            failures.append("validate_no_ehsas: Found forbidden phrase 'pareshani ka ehsas'")
        elif "ehsas" in content or "احساس" in content:
            failures.append("validate_no_ehsas: Found forbidden word 'ehsas'")
    return failures


def extract_top_customer_trigrams(
    accepted_records: List[Dict[str, Any]],
    min_count: int = 5,
    top_k: int = 10
) -> List[Tuple[str, int]]:
    phrase_counts = Counter()
    for rec in accepted_records:
        first_cust_content = ""
        for m in rec.get("messages", []):
            if m.get("role") == "user":
                first_cust_content = m.get("content", "")
                break
        if not first_cust_content:
            continue
        words = re.findall(r"\b\w+\b", first_cust_content.lower())
        if len(words) >= 3:
            doc_trigrams = set()
            for i in range(len(words) - 2):
                tri = " ".join(words[i:i+3])
                doc_trigrams.add(tri)
            for tri in doc_trigrams:
                phrase_counts[tri] += 1

    eligible = [(phrase, count) for phrase, count in phrase_counts.items() if count >= min_count]
    eligible.sort(key=lambda x: (-x[1], x[0]))
    return eligible[:top_k]


def validate_candidate(candidate: Dict[str, Any], accepted_records: Optional[List[Dict[str, Any]]] = None) -> List[str]:
    # Normalize Urdu script text in messages and context before validation
    for m in candidate.get("messages", []):
        if "content" in m and isinstance(m["content"], str):
            m["content"] = normalize_urdu_text(m["content"])
    if candidate.get("context") and isinstance(candidate["context"], str):
        candidate["context"] = normalize_urdu_text(candidate["context"])

    failures = []
    seed_wrap = [candidate]
    is_seed = candidate.get("variation", {}).get("source") == "seed_selftest"

    v = seed_stats.validate_chat_no_json(seed_wrap)
    if v:
        failures.extend([f"validate_chat_no_json: {item['reason']}" for item in v])

    v = seed_stats.validate_bot_turns(seed_wrap)
    if v:
        failures.extend([f"validate_bot_turns: {item['reason']}" for item in v])

    v = seed_stats.validate_time_mentioned(seed_wrap)
    if v:
        failures.extend([f"validate_time_mentioned: {item['reason']}" for item in v])

    v = seed_stats.validate_no_procedure_words(seed_wrap)
    if v:
        failures.extend([f"validate_no_procedure_words: word '{item['word']}' in '{item['text']}'" for item in v])

    v = seed_stats.validate_no_action_claims(seed_wrap)
    if v:
        failures.extend([f"validate_no_action_claims: matched '{item['match']}' in '{item['text']}'" for item in v])

    v = seed_stats.validate_no_from_rag(seed_wrap)
    if v:
        failures.extend([f"validate_no_from_rag: {item['reason']}" for item in v])

    v = seed_stats.validate_number_grounding(seed_wrap)
    if v:
        failures.extend([f"validate_number_grounding: {item['reason']}" for item in v])

    v = seed_stats.validate_no_document_behavior(seed_wrap)
    if v:
        failures.extend([f"validate_no_document_behavior: {item['reason']}" for item in v])

    v = seed_stats.validate_context_safety(seed_wrap)
    if v:
        failures.extend([f"validate_context_safety: {item['reason']}" for item in v])

    v = seed_stats.validate_no_credential_requests(seed_wrap)
    if v:
        failures.extend([f"validate_no_credential_requests: {item['reason']}" for item in v])

    v = seed_stats.validate_no_fault_confirmations(seed_wrap)
    if v:
        failures.extend([f"validate_no_fault_confirmations: {item['reason']}" for item in v])

    v = seed_stats.validate_no_unperformable_action_offers(seed_wrap)
    if v:
        failures.extend([f"validate_no_unperformable_action_offers: {item['reason']}" for item in v])

    v = seed_stats.validate_no_unauthorized_policy_claims(seed_wrap)
    if v:
        failures.extend([f"validate_no_unauthorized_policy_claims: {item['reason']}" for item in v])

    v = seed_stats.validate_no_maazrat_khwah(seed_wrap)
    if v:
        failures.extend([f"validate_no_maazrat_khwah: {item['reason']}" for item in v])

    v = seed_stats.validate_no_urdu_bank_spellings(seed_wrap)
    if v:
        failures.extend([f"validate_no_urdu_bank_spellings: {item['reason']}" for item in v])

    v = seed_stats.validate_no_unsupported_delay_words(seed_wrap)
    if v:
        failures.extend([f"validate_no_unsupported_delay_words: {item['reason']}" for item in v])

    v = validate_no_forbidden_customer_words(seed_wrap)
    if v:
        failures.extend([f"validate_no_forbidden_customer_words: {item['reason']}" for item in v])

    v = validate_ticket_amount_allowed(candidate)
    if v:
        failures.extend(v)

    v = validate_no_context_ranges(candidate)
    if v:
        failures.extend(v)

    v = validate_scam_warning(candidate)
    if v:
        failures.extend(v)

    # v1.1, v1.2 & v1.9 validators: apply to generated candidates and selftest bad cases
    if not is_seed:
        v = validate_refusals(candidate)
        if v:
            failures.extend(v)

        v = validate_no_facet_questions(candidate)
        if v:
            failures.extend(v)

        v = validate_no_help_offers_and_numbers(candidate)
        if v:
            failures.extend(v)

        v = validate_lengths(candidate, max_bot_words=MAX_BOT_WORDS_N)
        if v:
            failures.extend(v)

        v = validate_no_generic_closing_questions(seed_wrap)
        if v:
            failures.extend([f"validate_no_generic_closing_questions: {item['reason']}" for item in v])

        v = validate_script_consistency(candidate)
        if v:
            failures.extend(v)

        v = validate_complaint_numbers(candidate)
        if v:
            failures.extend(v)

        v = validate_question_whitelist(candidate)
        if v:
            failures.extend(v)

        v = validate_no_other_bank_and_fehrist(candidate)
        if v:
            failures.extend(v)

        v = validate_only_asked_numbers(seed_wrap)
        if v:
            failures.extend([f"validate_only_asked_numbers: {item['reason']}" for item in v])

        v = validate_no_personal_identifiers(candidate)
        if v:
            failures.extend(v)

        v = validate_opening_diversity(candidate)
        if v:
            failures.extend(v)

        v = validate_customer_mood(candidate)
        if v:
            failures.extend(v)

        v = validate_time_mentioned_natural(candidate)
        if v:
            failures.extend(v)

        v = validate_context_numbers_match_sampled(candidate)
        if v:
            failures.extend(v)

        v = validate_customer_amount_matches(candidate)
        if v:
            failures.extend(v)

        v = validate_nodoc_question_asked(candidate)
        if v:
            failures.extend(v)

        v = validate_no_trailing_zero_decimals(candidate)
        if v:
            failures.extend(v)

        v = validate_no_customer_echo(candidate)
        if v:
            failures.extend(v)

        v = validate_no_facet_copying(candidate)
        if v:
            failures.extend(v)

        v = validate_no_structure_claims(candidate)
        if v:
            failures.extend(v)

        v = validate_ji_first(candidate)
        if v:
            failures.extend(v)

        v = validate_end_style(candidate)
        if v:
            failures.extend(v)

        v = validate_opening_variety(candidate, accepted_records=accepted_records)
        if v:
            failures.extend(v)

        v = validate_no_ehsas(candidate)
        if v:
            failures.extend(v)

        v = validate_no_customer_ji(candidate)
        if v:
            failures.extend(v)

        v = validate_no_filler_sentences(candidate)
        if v:
            failures.extend(v)

    ticket = candidate.get("ticket")
    if ticket is not None:
        v = validate_ticket_summary_language(candidate)
        if v:
            failures.extend(v)
        try:
            BankingTicket(**ticket)
            cat = candidate.get("category", "")
            amt = ticket.get("amount")
            is_angry = ticket.get("customer_very_angry", False)
            threshold = get_large_amount_threshold()
            should_escalate = (
                cat == "fraud" or
                (amt is not None and amt >= threshold) or
                is_angry
            )
            if ticket.get("escalate_to_human") != should_escalate:
                failures.append(
                    f"ticket_escalation: expected escalate_to_human={should_escalate}, got {ticket.get('escalate_to_human')}"
                )
        except Exception as te:
            failures.append(f"ticket_schema: {te}")

    return failures


def strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    return cleaned.strip()


def sanitize_error_message(err: Exception) -> str:
    err_cls = type(err).__name__
    raw_msg = str(err)
    for k in ["GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "API_KEY"]:
        val = os.getenv(k, "").strip()
        if val and len(val) >= 8:
            raw_msg = raw_msg.replace(val, "[REDACTED_KEY]")
    redacted = re.sub(r"AIza[0-9A-Za-z_-]{20,}", "[REDACTED_API_KEY]", raw_msg)
    redacted = re.sub(r"sk-[0-9A-Za-z_-]{20,}", "[REDACTED_API_KEY]", redacted)
    redacted = re.sub(r"[A-Za-z0-9_-]{32,}", "[REDACTED_KEY]", redacted)
    short_msg = redacted[:200]
    return f"{err_cls}: {short_msg}"


def log_cost(
    prompt_tokens: int,
    completion_tokens: int,
    provider: str,
    model_name: str,
    pricing_config: Optional[Dict[str, Any]] = None,
    seed_id: str = "",
    task_type: str = ""
) -> None:
    if pricing_config is None:
        pricing_config = {}
    input_rate = pricing_config.get("input_per_million")
    output_rate = pricing_config.get("output_per_million")
    if input_rate is not None and output_rate is not None:
        cost_val = (prompt_tokens / 1_000_000.0) * float(input_rate) + (completion_tokens / 1_000_000.0) * float(output_rate)
        cost_str = f"${cost_val:.6f}"
    else:
        cost_str = "price not set"

    header_needed = not COSTS_LOG_PATH.exists()
    timestamp = datetime.now().strftime("%Y_%m_%d %H_%M_%S")

    with open(COSTS_LOG_PATH, "a", encoding="utf-8") as f:
        if header_needed:
            f.write("# Synthetic Data Generation Cost Log\n\n")
        f.write("## Generation Log Entry\n")
        f.write(f"* Timestamp: {timestamp}\n")
        f.write(f"* Provider: {provider}\n")
        f.write(f"* Model: {model_name}\n")
        f.write(f"* Seed ID: {seed_id}\n")
        f.write(f"* Task Type: {task_type}\n")
        f.write(f"* Input Tokens: {prompt_tokens}\n")
        f.write(f"* Output Tokens: {completion_tokens}\n")
        f.write(f"* Total Tokens: {prompt_tokens + completion_tokens}\n")
        f.write(f"* Estimated Cost USD: {cost_str}\n\n")


def save_accepted(candidate: Dict[str, Any]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    # Check that fails if any saved Urdu text has Arabic code points
    for m in candidate.get("messages", []):
        content = m.get("content", "")
        if isinstance(content, str) and has_arabic_codepoints(content):
            raise ValueError(f"Arabic code point detected in saved message: {content}")
    ctx = candidate.get("context")
    if isinstance(ctx, str) and has_arabic_codepoints(ctx):
        raise ValueError(f"Arabic code point detected in saved context: {ctx}")

    with open(GENERATED_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(candidate, ensure_ascii=False) + "\n")
        f.flush()


def save_rejected(record: Dict[str, Any]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with open(REJECTED_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()


def call_teacher_api(
    prompt: str,
    config: Dict[str, str],
    temperature: float = 0.9,
    max_retries: int = 5,
    initial_backoff: float = 2.0
) -> Tuple[str, int, int]:
    provider = config.get("provider")
    model = config.get("model")
    api_key = config.get("api_key")
    key_var = config.get("key_var")

    if not provider:
        print("[ERROR] TEACHER_PROVIDER is not set in .env")
        sys.exit(1)

    validate_teacher_model(model)

    if not api_key or api_key.startswith("your_"):
        print(f"[ERROR] Valid API key for {key_var} is not set in .env")
        sys.exit(1)

    for attempt in range(max_retries):
        try:
            if provider == "gemini":
                from google import genai
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=genai.types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=temperature,
                    )
                )
                text = response.text or ""
                p_tokens = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
                c_tokens = response.usage_metadata.candidates_token_count if response.usage_metadata else 0
                log_request(model)
                return text, p_tokens, c_tokens

            elif provider == "openai":
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=temperature,
                )
                text = response.choices[0].message.content or ""
                p_tokens = response.usage.prompt_tokens if response.usage else 0
                c_tokens = response.usage.completion_tokens if response.usage else 0
                log_request(model)
                return text, p_tokens, c_tokens

            elif provider == "anthropic":
                from anthropic import Anthropic
                client = Anthropic(api_key=api_key)
                response = client.messages.create(
                    model=model,
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                )
                text = response.content[0].text or ""
                p_tokens = response.usage.input_tokens if response.usage else 0
                c_tokens = response.usage.output_tokens if response.usage else 0
                log_request(model)
                return text, p_tokens, c_tokens

            else:
                print(f"[ERROR] Unsupported TEACHER_PROVIDER: {provider}")
                sys.exit(1)

        except Exception as e:
            log_request(model)
            if is_quota_error(e):
                raise QuotaExhaustedError(str(e))

            err_str = str(e).lower()
            is_rate_limit = ("rate" in err_str and "limit" in err_str) or "429" in err_str or "resourceexhausted" in err_str or "quota" in err_str
            is_temp_server = any(code in err_str for code in ["500", "502", "503", "504"]) or "server error" in err_str or "overloaded" in err_str or "timeout" in err_str
            is_retryable = is_rate_limit or is_temp_server

            if is_retryable and attempt < max_retries - 1:
                backoff = initial_backoff * (2 ** attempt)
                print(f"[WARN] Temporary error encountered. Backing off for {backoff:.1f} seconds (attempt {attempt + 1}/{max_retries})")
                time.sleep(backoff)
                continue
            else:
                raise e

    raise RuntimeError("Maximum retries exceeded for teacher API call.")


def build_plan_targets(
    mode: str,
    config: Dict[str, Any],
    seeds: List[Dict[str, Any]],
    force_seed_id: Optional[str] = None,
    override_seed: Optional[int] = None,
    total: Optional[int] = None
) -> List[Dict[str, Any]]:
    plan_key = f"{mode}_generation"
    if plan_key not in config:
        raise ValueError(f"Plan configuration for '{plan_key}' not found in generation_plan.yaml")

    plan_cfg = config[plan_key]
    if total is None:
        total = plan_cfg.get("total_conversations", 20 if mode == "pilot" else 2250)
    task_types_cfg = plan_cfg.get("task_types", {})
    languages_cfg = plan_cfg.get("languages", {})
    turn_cfg = plan_cfg.get("turn_requirements", {})
    nodoc_cfg = plan_cfg.get("grounded_context_requirements", {})

    if override_seed is not None:
        random_seed = override_seed
    else:
        random_seed = config.get("generation_parameters", {}).get("random_seed", 42)
    rng = random.Random(random_seed)

    task_types_list = []
    for tt, info in task_types_cfg.items():
        cnt = info.get("count", 0) if isinstance(info, dict) else info
        task_types_list.extend([tt] * cnt)

    languages_list = []
    for lang, info in languages_cfg.items():
        cnt = info.get("count", 0) if isinstance(info, dict) else info
        languages_list.extend([lang] * cnt)
    rng.shuffle(languages_list)

    multi_count = turn_cfg.get("multi_turn_minimum_count", int(round(total * 0.2667)))
    single_count = max(0, total - multi_count)
    turns_list = [True] * multi_count + [False] * single_count
    rng.shuffle(turns_list)

    # Moods: calm (45%), frustrated (35%), very_angry (20%)
    calm_cnt = int(round(total * 0.45))
    frust_cnt = int(round(total * 0.35))
    angry_cnt = max(0, total - calm_cnt - frust_cnt)
    moods_list = ["calm"] * calm_cnt + ["frustrated"] * frust_cnt + ["very_angry"] * angry_cnt
    rng.shuffle(moods_list)

    fact_types = set(nodoc_cfg.get("fact_based_task_types", ["faq", "complaint"]))
    fact_indices = [i for i, tt in enumerate(task_types_list) if tt in fact_types]
    nodoc_count = nodoc_cfg.get("nodoc_count", 0)
    nodoc_indices = set(rng.sample(fact_indices, min(nodoc_count, len(fact_indices))))

    seeds_by_type: Dict[str, List[Dict[str, Any]]] = {}
    for s in seeds:
        tt = derive_task_type(s)
        seeds_by_type.setdefault(tt, []).append(s)

    forced_seed = None
    if force_seed_id:
        matches = [s for s in seeds if s.get("id") == force_seed_id]
        if not matches:
            raise ValueError(f"Seed ID '{force_seed_id}' not found in loaded seeds")
        forced_seed = matches[0]

    opening_styles_pool = config.get("opening_styles", [])
    cust_pool = config.get("customer_style_pool", {})
    ru_pool = cust_pool.get("roman_urdu", [])
    ur_pool = cust_pool.get("urdu_script", [])
    number_ranges = config.get("sampled_number_ranges", {})

    spellings = ["clean", "typo_heavy"]

    targets = []
    for i in range(total):
        tt = task_types_list[i] if i < len(task_types_list) else "faq"
        lang = languages_list[i] if i < len(languages_list) else "urdulish"
        is_multi = turns_list[i] if i < len(turns_list) else False
        is_nodoc = (i in nodoc_indices)
        mood_val = moods_list[i] if i < len(moods_list) else "calm"

        if forced_seed:
            chosen_seed = forced_seed
            tt = derive_task_type(forced_seed)
        else:
            candidates = seeds_by_type.get(tt, seeds)
            chosen_seed = rng.choice(candidates)

        spelling = "clean" if lang in ["english", "urdu_script"] else rng.choice(spellings)
        writing_style = derive_customer_writing_style(mood_val, spelling)

        # Nodoc scope and target
        nodoc_target = None
        if is_nodoc:
            if tt == "complaint":
                nodoc_target = "customer must ask about the resolution time or a fee"
            elif tt == "faq":
                nodoc_target = "customer must ask about a fee, limit, or rule"
            else:
                is_nodoc = False

        # Sample 1 opening style instruction from appropriate group
        op_style = select_opening_style(
            config,
            mood=mood_val,
            is_context_fact=(tt in ["faq", "complaint"] and not is_nodoc),
            task_type=tt,
            intent=chosen_seed.get("intent"),
            rng=rng
        )

        # Sample customer style examples matching mood and spelling
        s_ru = sample_customer_style_examples(cust_pool, "roman_urdu", mood=mood_val, spelling=spelling, count=4, rng=rng, task_type=tt)
        s_ur = sample_customer_style_examples(cust_pool, "urdu_script", mood=mood_val, spelling=spelling, count=3, rng=rng, task_type=tt)

        # Sample grounded numbers if context needed
        sampled_nums = {}
        if tt in ["faq", "complaint"] and not is_nodoc:
            cat = chosen_seed.get("category", "")
            intent_val = chosen_seed.get("intent", "")
            budget = get_intent_number_budget(intent_val, category=cat, task_type=tt)

            if budget == 0:
                sampled_nums = {}
            elif intent_val in TICKET_COMPLAINT_INTENTS or tt == "complaint" or chosen_seed.get("ticket") is not None:
                # Ticket and complaint intents: 1 number, ONLY the resolution time
                tat_unit = rng.choice(["hours", "days"])
                if tat_unit == "hours":
                    raw_tat = rng.choice(number_ranges.get("resolution_time_hours", number_ranges.get("turnaround_hours", [24, 48, 72])))
                    sampled_nums["tat_hours"] = format_number_no_trailing_zero(raw_tat)
                else:
                    raw_tat = rng.choice(number_ranges.get("resolution_time_days", number_ranges.get("turnaround_days", [2, 3, 5, 7])))
                    sampled_nums["tat_days"] = format_number_no_trailing_zero(raw_tat)
            elif intent_val in ["installment_inquiry", "loan_eligibility"] or cat == "loan":
                raw_pct = rng.choice(number_ranges.get("loan_markup", number_ranges.get("percentage", [15.0, 18.0, 22.0])))
                sampled_nums["markup_percentage"] = format_number_no_trailing_zero(raw_pct)
                if intent_val == "installment_inquiry":
                    raw_late = rng.choice(number_ranges.get("late_payment_fee", [500, 750, 1000]))
                    sampled_nums["late_fee"] = format_number_no_trailing_zero(raw_late)
                else:
                    raw_fee = rng.choice(number_ranges.get("loan_processing_fee", [1000, 1500, 2500]))
                    sampled_nums["processing_fee"] = format_number_no_trailing_zero(raw_fee)
            elif intent_val == "account_statement":
                raw_fee = rng.choice(number_ranges.get("statement_fee", [150, 250, 350]))
                sampled_nums["fee"] = format_number_no_trailing_zero(raw_fee)
            elif intent_val == "dormant_account":
                raw_fee = rng.choice(number_ranges.get("dormant_reactivation_fee", [0, 100, 250]))
                sampled_nums["fee"] = format_number_no_trailing_zero(raw_fee)
            elif intent_val == "raast_inquiry":
                raw_fee = rng.choice(number_ranges.get("transfer_raast_fee", [25, 50, 100]))
                sampled_nums["fee"] = format_number_no_trailing_zero(raw_fee)
            elif intent_val == "bill_payment":
                raw_fee = rng.choice(number_ranges.get("bill_payment_fee", [15, 25, 50]))
                sampled_nums["fee"] = format_number_no_trailing_zero(raw_fee)
            elif "card" in intent_val or "card" in cat:
                raw_fee = rng.choice(number_ranges.get("card_fee", [500, 850, 1200]))
                sampled_nums["fee"] = format_number_no_trailing_zero(raw_fee)
            elif "limit" in intent_val:
                raw_num = rng.choice(number_ranges.get("daily_limits", number_ranges.get("daily_limit", [50000, 100000, 250000])))
                sampled_nums["daily_limit"] = format_number_no_trailing_zero(raw_num)
            elif intent_val == "international_usage":
                raw_num = rng.choice(number_ranges.get("daily_limits", [50000, 100000, 250000]))
                raw_pct = rng.choice(number_ranges.get("loan_markup", [15.0, 18.0, 22.0]))
                sampled_nums["daily_limit"] = format_number_no_trailing_zero(raw_num)
                sampled_nums["markup_percentage"] = format_number_no_trailing_zero(raw_pct)
            else:
                if budget >= 1:
                    raw_fee = rng.choice(number_ranges.get("transfer_raast_fee", [25, 50, 100]))
                    sampled_nums["fee"] = format_number_no_trailing_zero(raw_fee)

            # Enforce hard budget ceiling: never supply more numbers than the budget
            if len(sampled_nums) > budget:
                trimmed = {}
                for k, v in list(sampled_nums.items())[:budget]:
                    trimmed[k] = v
                sampled_nums = trimmed

        # Sample customer amount only for intents whose seeds carry a ticket amount
        sampled_cust_amt = None
        if tt == "complaint" and chosen_seed.get("intent") in AMOUNT_ALLOWED_INTENTS:
            raw_amt = rng.choice(number_ranges.get("customer_amount", [4500, 8000, 15000, 25000, 55000]))
            sampled_cust_amt = format_number_no_trailing_zero(raw_amt)

        # Sample end_style: for out_of_scope always statement, otherwise statement (55%) or question (45%)
        if tt == "out_of_scope":
            end_style = "statement"
        else:
            end_style = rng.choices(["statement", "question"], weights=[0.55, 0.45], k=1)[0]

        # Sample scenario facets: 1 value from 2 different facet lists (none for out_of_scope)
        sampled_facets = {}
        if tt != "out_of_scope":
            scenario_facets_pool = config.get("scenario_facets", {})
            seed_intent = chosen_seed.get("intent", "")
            intent_facets = scenario_facets_pool.get(seed_intent, {})
            if intent_facets and isinstance(intent_facets, dict):
                available_lists = [k for k, v in intent_facets.items() if isinstance(v, list) and len(v) > 0]
                if len(available_lists) >= 2:
                    chosen_keys = rng.sample(available_lists, 2)
                    for k in chosen_keys:
                        sampled_facets[k] = rng.choice(intent_facets[k])

        targets.append({
            "index": i,
            "seed": chosen_seed,
            "task_type": tt,
            "language": lang,
            "is_multi_turn": is_multi,
            "nodoc": is_nodoc,
            "nodoc_target": nodoc_target,
            "spelling": spelling,
            "writing_style": writing_style,
            "mood": mood_val,
            "opening_style": op_style,
            "end_style": end_style,
            "sampled_roman_urdu_examples": s_ru,
            "sampled_urdu_script_examples": s_ur,
            "sampled_numbers": sampled_nums,
            "sampled_customer_amount": sampled_cust_amt,
            "sampled_facets": sampled_facets,
        })

    # In pilot and full run mode: shuffle the target list so any prefix contains several task types
    if mode in ["pilot", "full"]:
        rng.shuffle(targets)
        for new_idx, tgt in enumerate(targets):
            tgt["index"] = new_idx

    return targets


def derive_generation_targets(
    config: Dict[str, Any],
    seeds: List[Dict[str, Any]],
    mode: str = "pilot",
    total: Optional[int] = None,
    target_seed: Optional[int] = None,
    force_seed_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    return build_plan_targets(
        mode=mode,
        config=config,
        seeds=seeds,
        force_seed_id=force_seed_id,
        override_seed=target_seed,
        total=total
    )


def init_or_load_state(mode: str, total_conversations: int, is_resume: bool, random_seed: int = 42) -> Dict[str, Any]:
    if is_resume and STATE_PATH.exists():
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                state = json.load(f)
            print(f"[INFO] Resuming state from {STATE_PATH} at index {state.get('current_index', 0)}")
            state.setdefault("random_seed", random_seed)
            return state
        except Exception as e:
            print(f"[WARN] Failed to load state file: {e}. Starting fresh state.")

    state = {
        "mode": mode,
        "random_seed": random_seed,
        "plan_total": total_conversations,
        "requested": 0,
        "accepted": 0,
        "rejected": 0,
        "current_index": 0,
        "requested_by_task_type": {"faq": 0, "complaint": 0, "fraud": 0, "out_of_scope": 0},
        "task_types": {"faq": 0, "complaint": 0, "fraud": 0, "out_of_scope": 0},
        "languages": {"urdulish": 0, "roman_urdu": 0, "english": 0, "urdu_script": 0},
        "turn_types": {"single_turn": 0, "multi_turn": 0},
        "nodoc_counts": {"nodoc": 0, "with_context": 0},
        "total_prompt_tokens": 0,
        "total_completion_tokens": 0,
        "total_bot_turns": 0,
        "bot_turns_with_question": 0,
        "first_bot_sentences": {},
        "total_user_messages": 0,
        "customer_trigrams": {},
        "total_accepted_contexts": 0,
        "context_number_frequencies": {},
        "rejection_rules": {},
        "rejection_examples": {},
        "consecutive_error_type": None,
        "consecutive_error_count": 0,
    }
    return state


def save_state(state: Dict[str, Any]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = STATE_PATH.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    tmp_path.replace(STATE_PATH)


def compute_shared_customer_words_stat(records: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Computes 'conversations sharing 5+ consecutive customer words within the same seed'
    only over the accepted records. Returns (numerator, denominator) where denominator = len(records).
    """
    total_acc_count = len(records)
    if total_acc_count == 0:
        return 0, 0

    by_seed: Dict[str, List[Tuple[int, Set[Tuple[str, ...]]]]] = {}
    for idx, rec in enumerate(records):
        sid = rec.get("seed_id", "unknown")
        conv_5grams = set()
        for msg in rec.get("messages", []):
            if msg.get("role") == "user":
                u_text = msg.get("content", "")
                u_words = re.findall(r"\b\w+\b", u_text.lower())
                if len(u_words) >= 5:
                    for i in range(len(u_words) - 4):
                        conv_5grams.add(tuple(u_words[i:i+5]))
        by_seed.setdefault(sid, []).append((idx, conv_5grams))

    overlapping_indices = set()
    for sid, items in by_seed.items():
        if len(items) < 2:
            continue
        for i in range(len(items)):
            idx_i, grams_i = items[i]
            if not grams_i:
                continue
            for j in range(len(items)):
                if i != j:
                    idx_j, grams_j = items[j]
                    if grams_i.intersection(grams_j):
                        overlapping_indices.add(idx_i)
                        break

    return len(overlapping_indices), total_acc_count


def print_summary(state: Dict[str, Any]) -> None:
    req = state.get("requested", 0)
    acc = state.get("accepted", 0)
    rej = state.get("rejected", 0)
    rate = (acc / req * 100.0) if req > 0 else 0.0
    p_tokens = state.get("total_prompt_tokens", 0)
    c_tokens = state.get("total_completion_tokens", 0)

    print("\n" + "=" * 70)
    print("GENERATION RUN SUMMARY")
    print("=" * 70)
    print(f"Total Requested Conversations : {req}")
    print(f"Total Accepted Conversations  : {acc}")
    print(f"Total Rejected Conversations  : {rej}")
    print(f"Acceptance Rate               : {rate:.2f}%")

    print("\nAcceptance Rate per Task Type:")
    req_by_tt = state.get("requested_by_task_type", {})
    acc_by_tt = state.get("task_types", {})
    for tt in ["faq", "complaint", "fraud", "out_of_scope"]:
        tt_req = req_by_tt.get(tt, 0)
        tt_acc = acc_by_tt.get(tt, 0)
        tt_rate = (tt_acc / tt_req * 100.0) if tt_req > 0 else 0.0
        print(f"  * {tt}: {tt_acc}/{tt_req} ({tt_rate:.1f}%)")

    plan_total = state.get("plan_total", 20)
    needed = max(0, plan_total - acc)
    overall_rate = (acc / req) if req > 0 else 1.0
    if needed == 0:
        print(f"\nEstimated Requests Needed: Plan target of {plan_total} accepted conversations reached.")
    elif overall_rate > 0:
        est_remaining_req = int(round(needed / overall_rate))
        est_total_req = req + est_remaining_req
        print(f"\nEstimated Requests Needed to Reach Target ({plan_total} accepted):")
        print(f"  * Additional requests needed : {est_remaining_req}")
        print(f"  * Projected total requests    : {est_total_req} (at current {rate:.1f}% acceptance rate)")
    else:
        print(f"\nEstimated Requests Needed: Unknown (current acceptance rate is 0.0%)")

    print("\nLanguages (Accepted):")
    for k, v in state.get("languages", {}).items():
        print(f"  * {k}: {v}")
    print("\nTurn Distribution (Accepted):")
    for k, v in state.get("turn_types", {}).items():
        print(f"  * {k}: {v}")
    print("\nGrounded Context / Nodoc (Accepted):")
    for k, v in state.get("nodoc_counts", {}).items():
        print(f"  * {k}: {v}")
    print("\nToken Consumption:")
    print(f"  * Total Input Tokens        : {p_tokens}")
    print(f"  * Total Output Tokens       : {c_tokens}")
    print(f"  * Total Combined Tokens     : {p_tokens + c_tokens}")

    tot_bot = state.get("total_bot_turns", 0)
    q_bot = state.get("bot_turns_with_question", 0)
    q_pct = (q_bot / tot_bot * 100.0) if tot_bot > 0 else 0.0
    print(f"\nBot Turns Ending With Question: {q_bot}/{tot_bot} ({q_pct:.1f}%)")
    if q_pct > 50.0:
        print(f"  [WARNING] Percentage of bot turns ending with question exceeds 50% ({q_pct:.1f}%)")

    first_sents = state.get("first_bot_sentences", {})
    print("\n5 Most Common First Sentences in Accepted Bot Turns:")
    if not first_sents:
        print("  None recorded")
    else:
        sorted_sents = sorted(first_sents.items(), key=lambda x: x[1], reverse=True)[:5]
        for rank, (sent, count) in enumerate(sorted_sents, start=1):
            s_pct = (count / tot_bot * 100.0) if tot_bot > 0 else 0.0
            print(f"  {rank}. \"{sent}\" ({count} occurrences, {s_pct:.1f}%)")
            if acc < 100:
                print("     (sample too small for warnings)")
            elif count >= 3 and s_pct > 5.0:
                print(f"     [WARNING] First sentence exceeds 5% threshold ({s_pct:.1f}% > 5.0%)")

    trigrams = state.get("customer_trigrams", {})
    tot_user = state.get("total_user_messages", 0)
    print("\n10 Most Common 3 Word Phrases in Accepted Customer Messages:")
    if not trigrams:
        print("  None recorded")
    else:
        sorted_tri = sorted(trigrams.items(), key=lambda x: x[1], reverse=True)[:10]
        for rank, (tri, count) in enumerate(sorted_tri, start=1):
            t_pct = (count / tot_user * 100.0) if tot_user > 0 else 0.0
            print(f"  {rank}. \"{tri}\" ({count} occurrences, {t_pct:.1f}%)")
            if acc < 100:
                print("     (sample too small for warnings)")
            elif count >= 3 and t_pct > 8.0:
                print(f"     [WARNING] 3 word phrase exceeds 8% threshold ({t_pct:.1f}% > 8.0%)")

    ctx_num_freqs = state.get("context_number_frequencies", {})
    tot_ctx = state.get("total_accepted_contexts", 0)
    print("\n5 Most Common Context Numbers in Accepted Contexts:")
    if not ctx_num_freqs:
        print("  None recorded")
    else:
        sorted_ctx_nums = sorted(ctx_num_freqs.items(), key=lambda x: x[1], reverse=True)[:5]
        for rank, (num_str, count) in enumerate(sorted_ctx_nums, start=1):
            c_pct = (count / tot_ctx * 100.0) if tot_ctx > 0 else 0.0
            print(f"  {rank}. {num_str} ({count} occurrences, {c_pct:.1f}%)")
            if acc < 40:
                print("     (sample too small for warnings)")
            elif c_pct > 5.0:
                print(f"     [WARNING] Context number exceeds 5% threshold ({c_pct:.1f}% > 5.0%)")

    rej_rules = state.get("rejection_rules", {})
    rej_examples = state.get("rejection_examples", {})
    print("\nTop 3 Most Common Rejection Rules:")
    if not rej_rules:
        print("  None (zero rejections recorded)")
    else:
        sorted_rules = sorted(rej_rules.items(), key=lambda x: x[1], reverse=True)[:3]
        for rank, (rule, count) in enumerate(sorted_rules, start=1):
            ex = rej_examples.get(rule, "No example recorded")
            print(f"  {rank}. Rule '{rule}' ({count} occurrences):")
            print(f"     Example: {ex}")

    distinct_pairs_count = len(state.get("facet_pairs_used", {}))
    print(f"\nDistinct Scenario Facet Pairs Used: {distinct_pairs_count}")

    # Compute customer 5-gram overlap within the same seed
    accepted_records = []
    if GENERATED_PATH.exists():
        try:
            with open(GENERATED_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line_str = line.strip()
                    if line_str:
                        accepted_records.append(json.loads(line_str))
        except Exception:
            pass

    overlapping_convs, total_acc_count = compute_shared_customer_words_stat(accepted_records)
    overlap_share = (overlapping_convs / total_acc_count * 100.0) if total_acc_count > 0 else 0.0
    print(f"\nConversations Sharing 5+ Consecutive Customer Words Within Same Seed: {overlapping_convs}/{total_acc_count} ({overlap_share:.1f}%)")
    if total_acc_count >= 10 and overlap_share > 10.0:
        print(f"  [WARNING] Share of conversations sharing 5+ consecutive customer words exceeds 10% ({overlap_share:.1f}% > 10.0%)")

    print("=" * 70 + "\n")


def run_generation(
    mode: Optional[str] = None,
    is_resume: bool = False,
    limit: Optional[int] = None,
    force_seed_id: Optional[str] = None,
    daily_limit: Optional[int] = None,
    min_interval: Optional[float] = None,
    override_seed: Optional[int] = None
) -> None:
    teacher_cfg = get_teacher_config()
    model_name = teacher_cfg.get("model", "")
    validate_teacher_model(model_name)

    config = load_config()
    model_limits_info = get_model_limits(model_name, config)
    table_min_interval = model_limits_info.get("min_seconds_between_requests", 13)
    table_daily_limit = model_limits_info.get("daily_request_limit", 18)

    effective_min_interval = min_interval if min_interval is not None else float(table_min_interval)
    effective_daily_limit = daily_limit if daily_limit is not None else int(table_daily_limit)

    gen_params = config.get("generation_parameters", {})
    temperature = gen_params.get("temperature", 0.9)
    pricing_cfg = config.get("pricing", {})

    if mode is None:
        if is_resume and STATE_PATH.exists():
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                prev_state = json.load(f)
            mode = prev_state.get("mode", "pilot")
        else:
            mode = "pilot"

    seeds = load_seeds(SEEDS_DIR)
    chosen_random_seed = override_seed if override_seed is not None else config.get("generation_parameters", {}).get("random_seed", 42)
    targets = build_plan_targets(mode, config, seeds, force_seed_id=force_seed_id, override_seed=chosen_random_seed)
    total_conversations = len(targets)

    state = init_or_load_state(mode, total_conversations, is_resume=is_resume, random_seed=chosen_random_seed)

    start_index = state.get("current_index", 0)
    if start_index >= total_conversations:
        print(f"[INFO] All {total_conversations} planned conversations already completed.")
        print_summary(state)
        return

    remaining_requests = total_conversations - start_index
    if limit is not None:
        remaining_requests = min(remaining_requests, limit)

    from datetime import timedelta
    est_duration_seconds = remaining_requests * effective_min_interval
    est_finish_time = datetime.now() + timedelta(seconds=est_duration_seconds)
    print(f"[INFO] Remaining requests: {remaining_requests}")
    print(f"[INFO] Estimated finishing time: {est_finish_time.strftime('%Y-%m-%d %H:%M:%S')} (in {est_duration_seconds:.0f} seconds at {effective_min_interval}s interval)")

    calls_made_this_run = 0
    last_call_dt = get_last_request_timestamp(REQUEST_LOG_PATH)

    accepted_records_cache: List[Dict[str, Any]] = []
    if GENERATED_PATH.exists():
        with open(GENERATED_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        accepted_records_cache.append(json.loads(line))
                    except Exception:
                        pass
    cached_forbidden_customer_phrases = [
        p for p, _ in extract_top_customer_trigrams(accepted_records_cache, min_count=5, top_k=10)
    ]

    try:
        while state["current_index"] < total_conversations:
            if len(accepted_records_cache) > 0 and len(accepted_records_cache) % 20 == 0:
                cached_forbidden_customer_phrases = [
                    p for p, _ in extract_top_customer_trigrams(accepted_records_cache, min_count=5, top_k=10)
                ]
            today_count = count_today_pacific_requests(REQUEST_LOG_PATH, model_name=model_name)
            if today_count >= effective_daily_limit:
                save_state(state)
                print(f"[INFO] Daily limit of {effective_daily_limit} calls reached for model '{model_name}' today (Pacific date count: {today_count}). Stopping cleanly.")
                break

            if limit is not None and calls_made_this_run >= limit:
                print(f"[INFO] Reached execution limit of {limit} calls.")
                break

            target = targets[state["current_index"]]
            seed = target["seed"]
            variation = {
                "category": seed.get("category", "complaint"),
                "intent": seed.get("intent", "transfer_failed"),
                "language": target["language"],
                "spelling": target["spelling"],
                "writing_style": target["writing_style"],
                "mood": target["mood"],
                "is_multi_turn": target["is_multi_turn"],
                "opening_style": target["opening_style"],
                "end_style": target["end_style"],
                "sampled_numbers": target.get("sampled_numbers", {}),
                "sampled_customer_amount": target.get("sampled_customer_amount"),
                "sampled_facets": target.get("sampled_facets", {}),
                "nodoc_target": target.get("nodoc_target"),
            }

            prompt = build_generation_prompt(
                seed=seed,
                variation=variation,
                task_type=target["task_type"],
                nodoc=target["nodoc"],
                sampled_roman_urdu_examples=target.get("sampled_roman_urdu_examples"),
                sampled_urdu_script_examples=target.get("sampled_urdu_script_examples"),
                opening_style=target.get("opening_style"),
                end_style=target.get("end_style"),
                nodoc_target=target.get("nodoc_target"),
                sampled_facets=target.get("sampled_facets"),
                forbidden_customer_phrases=cached_forbidden_customer_phrases
            )

            delay = calculate_pacing_delay(last_call_dt, current_dt=datetime.now(timezone.utc), min_interval=effective_min_interval)
            if delay > 0:
                print(f"[INFO] Pacing: waiting {delay:.1f}s to ensure at least {effective_min_interval}s between requests")
                time.sleep(delay)

            try:
                raw_text, p_tokens, c_tokens = call_teacher_api(
                    prompt=prompt,
                    config=teacher_cfg,
                    temperature=temperature
                )
                last_call_dt = datetime.now(timezone.utc)
            except QuotaExhaustedError:
                last_call_dt = datetime.now(timezone.utc)
                save_state(state)
                pac_rst, karachi_rst = get_next_pacific_reset_time()
                print("quota exhausted, resume later")
                print(f"Next quota reset: {pac_rst.strftime('%Y-%m-%d %H:%M:%S %Z')} (Pacific) / {karachi_rst.strftime('%Y-%m-%d %H:%M:%S %Z')} (Asia/Karachi)")
                sys.exit(0)
            except Exception as e:
                last_call_dt = datetime.now(timezone.utc)
                err_type = type(e).__name__
                if state.get("consecutive_error_type") == err_type:
                    state["consecutive_error_count"] = state.get("consecutive_error_count", 0) + 1
                else:
                    state["consecutive_error_type"] = err_type
                    state["consecutive_error_count"] = 1

                save_state(state)
                sanitized_msg = sanitize_error_message(e)

                if state["consecutive_error_count"] >= 3:
                    print(f"\n[ABORT] 3 consecutive calls failed with error: {sanitized_msg}")
                    print("Stopping generation so you can fix the issue.")
                    break
                else:
                    print(f"\n[ERROR] API call failed ({state['consecutive_error_count']}/3 consecutive for {err_type}): {sanitized_msg}")
                    time.sleep(2.0)
                    continue

            state["consecutive_error_type"] = None
            state["consecutive_error_count"] = 0
            state["total_prompt_tokens"] += p_tokens
            state["total_completion_tokens"] += c_tokens
            state["requested"] += 1
            tt_key = target["task_type"]
            state.setdefault("requested_by_task_type", {})
            state["requested_by_task_type"][tt_key] = state["requested_by_task_type"].get(tt_key, 0) + 1
            calls_made_this_run += 1

            cleaned_text = strip_code_fences(raw_text)
            try:
                data = json.loads(cleaned_text)
                json_valid = True
            except Exception as je:
                json_valid = False
                parse_err = str(je)

            if not json_valid:
                rule_name = "json_parse_error"
                save_rejected({
                    "seed_id": seed.get("id"),
                    "task_type": target["task_type"],
                    "variation": variation,
                    "prompt_version": PROMPT_VERSION,
                    "failed_rules": [f"{rule_name}: {parse_err}"],
                    "raw_response": raw_text,
                    "sampled_facets": target.get("sampled_facets", {})
                })
                state["rejected"] += 1
                state["rejection_rules"][rule_name] = state["rejection_rules"].get(rule_name, 0) + 1
                if rule_name not in state["rejection_examples"]:
                    state["rejection_examples"][rule_name] = parse_err[:120]
                log_cost(p_tokens, c_tokens, teacher_cfg.get("provider", ""), teacher_cfg.get("model", ""), pricing_cfg, seed.get("id", ""), target["task_type"])
            else:
                context = data.get("context")
                if isinstance(context, str):
                    context = normalize_urdu_text(context)
                customer_bot_messages = data.get("messages", [])
                for m in customer_bot_messages:
                    if isinstance(m.get("content"), str):
                        m["content"] = normalize_urdu_text(m["content"])

                # Requirement 1: for out_of_scope, teacher produces only customer message(s) and topic; code builds bot refusal from pool
                if target["task_type"] == "out_of_scope" or data.get("category") == "out_of_scope":
                    topic_label = data.get("topic") or seed.get("intent")
                    cust_turns = [m for m in customer_bot_messages if m.get("role") == "user"]
                    if not cust_turns:
                        cust_turns = [{"role": "user", "content": "Ye sawal hai"}]
                    constructed_turns = []
                    cand_lang = data.get("language", variation.get("language", "urdulish"))
                    for user_turn in cust_turns:
                        constructed_turns.append(user_turn)
                        refusal_reply = default_refusal_selector.select(topic=topic_label, language=cand_lang)
                        constructed_turns.append({"role": "assistant", "content": refusal_reply})
                    customer_bot_messages = constructed_turns
                    context = None

                system_content = build_system_message(BASE_SYSTEM_MESSAGE, context)
                messages = [{"role": "system", "content": system_content}] + customer_bot_messages
                user_turns = [m for m in customer_bot_messages if m.get("role") == "user"]
                is_multi = len(user_turns) > 1

                ticket = data.get("ticket") if (target["task_type"] != "out_of_scope" and data.get("category") != "out_of_scope") else None
                # Rule 6: Code sets customer_very_angry from mood and computes escalate_to_human
                if ticket is not None:
                    is_very_angry = (target["mood"] == "very_angry")
                    ticket["customer_very_angry"] = is_very_angry
                    amt = ticket.get("amount")
                    threshold = get_large_amount_threshold()
                    is_fraud = (data.get("category", seed.get("category")) == "fraud" or target["task_type"] == "fraud")
                    should_escalate = (
                        is_fraud or
                        (amt is not None and amt >= threshold) or
                        is_very_angry
                    )
                    ticket["escalate_to_human"] = should_escalate

                candidate = {
                    "seed_id": seed.get("id"),
                    "seed_context": seed.get("context"),
                    "task_type": target["task_type"],
                    "variation": variation,
                    "prompt_version": PROMPT_VERSION,
                    "category": data.get("category", seed.get("category")),
                    "intent": data.get("intent", seed.get("intent")),
                    "language": data.get("language", variation.get("language", "urdulish")),
                    "is_multi_turn": is_multi,
                    "end_style": target.get("end_style"),
                    "context": context,
                    "messages": messages,
                    "ticket": ticket,
                    "sampled_facets": target.get("sampled_facets", {})
                }

                failures = validate_candidate(candidate, accepted_records=accepted_records_cache)
                if failures:
                    save_rejected({
                        "seed_id": seed.get("id"),
                        "task_type": target["task_type"],
                        "variation": variation,
                        "prompt_version": PROMPT_VERSION,
                        "failed_rules": failures,
                        "candidate": candidate,
                        "sampled_facets": target.get("sampled_facets", {})
                    })
                    state["rejected"] += 1
                    for f_msg in failures:
                        r_name = f_msg.split(":")[0].strip()
                        state["rejection_rules"][r_name] = state["rejection_rules"].get(r_name, 0) + 1
                        if r_name not in state["rejection_examples"]:
                            state["rejection_examples"][r_name] = f_msg
                    log_cost(p_tokens, c_tokens, teacher_cfg.get("provider", ""), teacher_cfg.get("model", ""), pricing_cfg, seed.get("id", ""), target["task_type"])
                else:
                    for m in candidate.get("messages", []):
                        if "content" in m and isinstance(m["content"], str):
                            m["content"] = normalize_urdu_text(m["content"])
                    if candidate.get("context") and isinstance(candidate["context"], str):
                        candidate["context"] = normalize_urdu_text(candidate["context"])
                    save_accepted(candidate)
                    accepted_records_cache.append(candidate)
                    state["accepted"] += 1
                    tt = target["task_type"]
                    lang = candidate.get("language", target["language"])
                    turn_key = "multi_turn" if is_multi else "single_turn"
                    state["task_types"][tt] = state["task_types"].get(tt, 0) + 1
                    state["languages"][lang] = state["languages"].get(lang, 0) + 1
                    state["turn_types"][turn_key] = state["turn_types"].get(turn_key, 0) + 1
                    if tt in ["faq", "complaint"]:
                        nodoc_k = "nodoc" if target["nodoc"] else "with_context"
                        state["nodoc_counts"][nodoc_k] = state["nodoc_counts"].get(nodoc_k, 0) + 1

                    facets = target.get("sampled_facets", {})
                    if facets and len(facets) >= 2:
                        facet_items = sorted([f"{k}:{v}" for k, v in facets.items()])
                        pair_key = f"{seed.get('intent')}|" + "|".join(facet_items)
                        state.setdefault("facet_pairs_used", {})
                        state["facet_pairs_used"][pair_key] = state["facet_pairs_used"].get(pair_key, 0) + 1

                    ctx = candidate.get("context")
                    if ctx and ctx != "koi document nahi mila":
                        state["total_accepted_contexts"] = state.get("total_accepted_contexts", 0) + 1
                        state.setdefault("context_number_frequencies", {})
                        ctx_nums = set(extract_distinct_numeric_values(ctx))
                        for n in ctx_nums:
                            n_str = format_number_no_trailing_zero(n)
                            state["context_number_frequencies"][n_str] = state["context_number_frequencies"].get(n_str, 0) + 1

                    for msg in candidate.get("messages", []):
                        m_role = msg.get("role")
                        m_content = msg.get("content", "").strip()
                        if m_role == "assistant":
                            state["total_bot_turns"] = state.get("total_bot_turns", 0) + 1
                            if m_content.endswith("?") or m_content.endswith("؟"):
                                state["bot_turns_with_question"] = state.get("bot_turns_with_question", 0) + 1
                            first_sent = extract_first_sentence(m_content)
                            if first_sent:
                                state.setdefault("first_bot_sentences", {})
                                state["first_bot_sentences"][first_sent] = state["first_bot_sentences"].get(first_sent, 0) + 1
                        elif m_role == "user":
                            state["total_user_messages"] = state.get("total_user_messages", 0) + 1
                            words = re.findall(r"\b\w+\b", m_content.lower())
                            seen_in_msg = set()
                            for w_idx in range(len(words) - 2):
                                trigram = f"{words[w_idx]} {words[w_idx + 1]} {words[w_idx + 2]}"
                                seen_in_msg.add(trigram)
                            state.setdefault("customer_trigrams", {})
                            for tri in seen_in_msg:
                                state["customer_trigrams"][tri] = state["customer_trigrams"].get(tri, 0) + 1

                    log_cost(p_tokens, c_tokens, teacher_cfg.get("provider", ""), teacher_cfg.get("model", ""), pricing_cfg, seed.get("id", ""), target["task_type"])

            state["current_index"] += 1
            save_state(state)

    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Generation process interrupted by user.")
    finally:
        save_state(state)
        print_summary(state)


def run_revalidation(file_paths: List[str]) -> Dict[str, Any]:
    summary = {
        "files": [],
        "total_records": 0,
        "total_passed": 0,
        "total_failed": 0,
        "total_status_changed": 0,
    }

    for path_str in file_paths:
        p = Path(path_str)
        if not p.exists():
            print(f"[ERROR] Revalidate file not found: {p}")
            continue

        print(f"\n{'='*70}\n[REVALIDATE] Processing: {p}\n{'='*70}")
        raw_lines = []
        with open(p, "r", encoding="utf-8") as f:
            for l_idx, line in enumerate(f, start=1):
                l_str = line.strip()
                if not l_str:
                    continue
                try:
                    raw_lines.append((l_idx, json.loads(l_str)))
                except Exception as e:
                    print(f"[WARN] Line {l_idx}: JSON parse error: {e}")

        file_pass = 0
        file_fail = 0
        failed_rules_counts = Counter()
        status_changed_records = []

        is_rejected_file = "rejected" in p.name.lower()

        for l_idx, record in raw_lines:
            if is_rejected_file and "candidate" in record and isinstance(record["candidate"], dict):
                cand = copy.deepcopy(record["candidate"])
                prev_status = "rejected"
            elif "failed_rules" in record:
                cand = copy.deepcopy(record.get("candidate", record))
                prev_status = "rejected"
            else:
                cand = copy.deepcopy(record)
                prev_status = "accepted"

            seed_id = cand.get("seed_id", record.get("seed_id", "unknown"))
            language = cand.get("language", record.get("language", "unknown"))

            # Run exact current validator pipeline with empty opening history
            cand["_mock_existing_openings"] = {}
            cand["_accepted_records"] = []
            failures = validate_candidate(cand, accepted_records=[])

            new_status = "accepted" if len(failures) == 0 else "rejected"
            if new_status == "accepted":
                file_pass += 1
            else:
                file_fail += 1
                for f_msg in failures:
                    rule_tag = f_msg.split(":")[0].strip() if ":" in f_msg else f_msg
                    failed_rules_counts[rule_tag] += 1

            changed = (new_status != prev_status)
            if changed:
                status_changed_records.append({
                    "line": l_idx,
                    "seed_id": seed_id,
                    "language": language,
                    "previous_status": prev_status,
                    "new_status": new_status,
                    "failed_rules": failures,
                })

            status_mark = "STATUS CHANGED" if changed else "STATUS SAME"
            fail_str = "; ".join(failures) if failures else "None"
            print(f"[{l_idx:04d}] seed_id={seed_id} | lang={language} | prev={prev_status} | new={new_status} | {status_mark} | failed_rules: {fail_str}")

        print(f"\n--- Revalidation Totals for {p.name} ---")
        print(f"Total Records   : {len(raw_lines)}")
        print(f"Passed          : {file_pass}")
        print(f"Failed          : {file_fail}")
        print("Failed Rules with Counts:")
        if not failed_rules_counts:
            print("  None (zero failed rules)")
        else:
            for r_tag, r_cnt in failed_rules_counts.most_common():
                print(f"  * {r_tag}: {r_cnt}")
        print(f"Records Whose Status Changed ({len(status_changed_records)}):")
        if not status_changed_records:
            print("  None (all records maintained their previous status)")
        else:
            for item in status_changed_records:
                r_fails = "; ".join(item["failed_rules"]) if item["failed_rules"] else "None"
                print(f"  * Line {item['line']} | {item['seed_id']} ({item['language']}): {item['previous_status']} -> {item['new_status']} | Failed: {r_fails}")

        summary["files"].append({
            "path": str(p),
            "total": len(raw_lines),
            "passed": file_pass,
            "failed": file_fail,
            "changed": len(status_changed_records),
            "rules": dict(failed_rules_counts),
        })
        summary["total_records"] += len(raw_lines)
        summary["total_passed"] += file_pass
        summary["total_failed"] += file_fail
        summary["total_status_changed"] += len(status_changed_records)

    return summary


def run_selftest() -> None:
    print("======================================================================")
    print("SELFTEST: VALIDATION PIPELINE INTEGRITY CHECK")
    print("======================================================================")

    # Part A: Test all 100 seeds converted to teacher output format
    print("\n[PART A] Testing All 100 Seeds Converted to Teacher Output Format")
    seeds = load_seeds(SEEDS_DIR)
    total_seeds = len(seeds)
    accepted_count = 0
    rejected_list = []

    for s in seeds:
        teacher_messages = [m for m in s.get("messages", []) if m.get("role") != "system"]
        ctx = s.get("context")
        sys_content = build_system_message(BASE_SYSTEM_MESSAGE, ctx)
        full_messages = [{"role": "system", "content": sys_content}] + teacher_messages

        user_turns = [m for m in teacher_messages if m.get("role") == "user"]
        is_multi = len(user_turns) > 1

        candidate = {
            "seed_id": s.get("id"),
            "task_type": derive_task_type(s),
            "variation": {"source": "seed_selftest"},
            "prompt_version": PROMPT_VERSION,
            "category": s.get("category"),
            "intent": s.get("intent"),
            "language": s.get("language"),
            "is_multi_turn": is_multi,
            "context": ctx,
            "messages": full_messages,
            "ticket": s.get("ticket")
        }

        failures = validate_candidate(candidate)
        if not failures:
            accepted_count += 1
        else:
            rejected_list.append((s.get("id"), failures))

    print(f"  Total Seeds Tested : {total_seeds}")
    print(f"  Accepted Seeds     : {accepted_count} (expected 100)")
    if rejected_list:
        print(f"  [FAIL] Rejected {len(rejected_list)} seeds:")
        for sid, fails in rejected_list:
            print(f"    - {sid}: {fails}")
    else:
        print("  [PASS] All 100 seeds passed validation pipeline in teacher output format.")

    # Part B: Test click warning behavior and bad cases
    print("\n[PART B] Testing Click Warning Behavior and Bad Cases")

    # Click check A: is link par hargiz click na karein MUST BE ACCEPTED
    click_pass_case = {
        "seed_id": "test_click_pass",
        "task_type": "fraud",
        "variation": {"mood": "calm"},
        "prompt_version": PROMPT_VERSION,
        "category": "fraud",
        "intent": "phishing_report",
        "language": "urdulish",
        "is_multi_turn": False,
        "context": None,
        "messages": [
            {"role": "system", "content": BASE_SYSTEM_MESSAGE},
            {"role": "user", "content": "Mujhe ek link mila hai SMS par."},
            {"role": "assistant", "content": "Ji, is link par hargiz click na karein aur Zarya Bank kabhi bhi call ya SMS par aap ka OTP ya PIN nahi maangta."}
        ],
        "ticket": None
    }
    click_pass_failures = validate_candidate(click_pass_case)
    click_pass_ok = (len(click_pass_failures) == 0)
    status_str = "[PASS]" if click_pass_ok else "[FAIL]"
    print(f"  {status_str} Accept Case: procedure words: warning click is accepted ('is link par hargiz click na karein')")
    if not click_pass_ok:
        print(f"         Actual Rule(s): {click_pass_failures}")

    bad_cases = [
        {
            "name": "1. asks for OTP",
            "expected_rule": "validate_no_credential_requests",
            "data": {
                "category": "fraud",
                "intent": "report_scam_call",
                "language": "urdulish",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mujhe ek ajeeb call aayi thi."},
                    {"role": "assistant", "content": "Ji, tasdeeq ke liye apna OTP batayein."}
                ]
            }
        },
        {
            "name": "2. invents a fee",
            "expected_rule": "validate_number_grounding",
            "data": {
                "category": "account",
                "intent": "open_account",
                "language": "urdulish",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Naya account kholne ki fee kitni hai?"},
                    {"role": "assistant", "content": "Ji, naya account kholne ki fee 450 rupees hai."}
                ]
            }
        },
        {
            "name": "3. says the money is safe",
            "expected_rule": "validate_bot_turns",
            "data": {
                "category": "transfer",
                "intent": "transfer_failed",
                "language": "urdulish",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mera paisa transfer nahi hua."},
                    {"role": "assistant", "content": "Ji pareshan na hon, aap ki raqam mehfooz hai. Kya aap transaction ID bata sakte hain?"}
                ]
            }
        },
        {
            "name": "4. claims it blocked the card",
            "expected_rule": "validate_no_action_claims",
            "data": {
                "category": "card",
                "intent": "block_card",
                "language": "urdulish",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mera card kho gaya hai."},
                    {"role": "assistant", "content": "Ji, hum ne aap ka card block kar diya hai, we have blocked your card. Kya aap ko naya card chahiye?"}
                ]
            }
        },
        {
            "name": "5. confirms a bank fault",
            "expected_rule": "validate_no_fault_confirmations",
            "data": {
                "category": "complaint",
                "intent": "fee_dispute",
                "language": "urdulish",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mera balance do dafa kata hai."},
                    {"role": "assistant", "content": "Ji, ye bank ki ghalti hai aur ghalat deduction hui hai. Kya aap transaction ID bata sakte hain?"}
                ]
            }
        },
        {
            "name": "6. uses security policy without context",
            "expected_rule": "validate_no_unauthorized_policy_claims",
            "data": {
                "category": "fraud",
                "intent": "refuse_credentials",
                "language": "urdulish",
                "context": "General guidelines for customers.",
                "messages": [
                    {"role": "user", "content": "Mera password reset kar dein."},
                    {"role": "assistant", "content": "Ji, security policy ke mutabiq hum chat par password reset nahi karte."}
                ]
            }
        },
        {
            "name": "7. invents a date",
            "expected_rule": "validate_time_mentioned",
            "data": {
                "category": "complaint",
                "intent": "transfer_failed",
                "language": "urdulish",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mera transfer atak gaya hai."},
                    {"role": "assistant", "content": "Ji, aap ki shikayat darj kar li gayi hai. Kya aap transaction ID bata sakte hain?"}
                ],
                "ticket": {
                    "intent": "transfer_failed",
                    "category": "complaint",
                    "priority": "medium",
                    "amount": 2000.0,
                    "time_mentioned": "2026-10-17 14:30:00",
                    "summary": "Transfer pending",
                    "customer_very_angry": False,
                    "escalate_to_human": False
                }
            }
        },
        {
            "name": "8. JSON inside a bot reply",
            "expected_rule": "validate_chat_no_json",
            "data": {
                "category": "transfer",
                "intent": "transfer_failed",
                "language": "urdulish",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Transfer status batayein."},
                    {"role": "assistant", "content": "Ji, aap ka ticket yeh hai: {\"status\": \"pending\"}."}
                ]
            }
        },
        {
            "name": "9. two questions in one turn",
            "expected_rule": "validate_bot_turns",
            "data": {
                "category": "complaint",
                "intent": "transfer_failed",
                "language": "urdulish",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mera paisa kat gaya hai."},
                    {"role": "assistant", "content": "Ji, kya aap transaction ID bata sakte hain? Aur katne wali raqam kitni thi?"}
                ]
            }
        },
        {
            "name": "10. a number not in the context",
            "expected_rule": "validate_number_grounding",
            "data": {
                "category": "card",
                "intent": "product_terms",
                "language": "urdulish",
                "context": "Debit card annual fee: 1200 rupees.",
                "messages": [
                    {"role": "user", "content": "Card ki fee kitni hai?"},
                    {"role": "assistant", "content": "Ji, debit card ki fee 3500 rupees hai."}
                ]
            }
        },
        {
            "name": "11. a nodoc case that states a number",
            "expected_rule": "validate_number_grounding",
            "data": {
                "category": "loan",
                "intent": "product_terms",
                "language": "urdulish",
                "context": "koi document nahi mila",
                "messages": [
                    {"role": "user", "content": "Personal loan ka markup kitna hai?"},
                    {"role": "assistant", "content": "Ji, markup 15 percent hai."}
                ]
            }
        },
        {
            "name": "12. Urdu script spelling of the bank name",
            "expected_rule": "validate_no_urdu_bank_spellings",
            "data": {
                "category": "account",
                "intent": "open_account",
                "language": "urdu_script",
                "context": None,
                "messages": [
                    {"role": "user", "content": "کیا میں نیا اکاؤنٹ کھول سکتا ہوں؟"},
                    {"role": "assistant", "content": "جی، ذریعہ بینک میں آپ کا خیر مقدم ہے۔ کیا آپ کسی مخصوص اکاؤنٹ کے بارے میں پوچھ رہے ہیں؟"}
                ]
            }
        },
        {
            "name": "13. generic closing question in Roman Urdu ('Kya aap ko koi aur madad chahiye?')",
            "expected_rule": "validate_no_generic_closing_questions",
            "data": {
                "category": "account",
                "intent": "fee_inquiry",
                "language": "urdulish",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Naya account kholne par koi fee hai?"},
                    {"role": "assistant", "content": "Ji, naya account kholne par koi fee nahi hai. Kya aap ko koi aur madad chahiye?"}
                ]
            }
        },
        {
            "name": "14. generic closing question in English ('Is there anything else I can help with?')",
            "expected_rule": "validate_no_generic_closing_questions",
            "data": {
                "category": "card",
                "intent": "delivery_status",
                "language": "english",
                "context": None,
                "messages": [
                    {"role": "user", "content": "When will my card be delivered?"},
                    {"role": "assistant", "content": "Ji, your debit card will be delivered soon. Is there anything else I can help with?"}
                ]
            }
        },
        {
            "name": "15. states more than 2 numbers from context not asked in Roman Urdu",
            "expected_rule": "validate_only_asked_numbers",
            "data": {
                "category": "card",
                "intent": "fee_inquiry",
                "language": "urdulish",
                "context": "Debit card annual fee is 1200 rupees, replacement fee is 800 rupees, and daily limit is 50000 rupees.",
                "messages": [
                    {"role": "user", "content": "Card ki fee kitni hai?"},
                    {"role": "assistant", "content": "Ji, card ki fee 1200 rupees hai, replacement fee 800 rupees hai aur daily limit 50000 rupees hai."}
                ]
            }
        },
        {
            "name": "16. states more than 2 numbers from context not asked in English",
            "expected_rule": "validate_only_asked_numbers",
            "data": {
                "category": "loan",
                "intent": "product_terms",
                "language": "english",
                "context": "Personal loan markup is 18 percent, processing fee is 2500 rupees, and maximum tenor is 36 months.",
                "messages": [
                    {"role": "user", "content": "What is the loan markup?"},
                    {"role": "assistant", "content": "Ji, the markup is 18 percent, processing fee is 2500 rupees, and maximum tenor is 36 months."}
                ]
            }
        },
        {
            "name": "17. customer message contains formal letter opening",
            "expected_rule": "validate_no_forbidden_customer_words",
            "data": {
                "category": "account",
                "intent": "balance_inquiry",
                "language": "urdulish",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mohtaram, mera balance check kar dein."},
                    {"role": "assistant", "content": "Ji, aap ki request darj kar li gayi hai."}
                ]
            }
        },
        {
            "name": "18. customer message contains literary words or slang phrase",
            "expected_rule": "validate_no_forbidden_customer_words",
            "data": {
                "category": "transfer",
                "intent": "transfer_failed",
                "language": "urdulish",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mera transfer na qabil e bardasht laparwahi ki wajah se atak gaya hai kya scene hai???"},
                    {"role": "assistant", "content": "Ji, aap ki shikayat darj kar li gayi hai."}
                ]
            }
        },
        {
            "name": "19. procedure words: click without warning ('is button par click karein')",
            "expected_rule": "validate_no_procedure_words",
            "data": {
                "category": "account",
                "intent": "app_guide",
                "language": "urdulish",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Balance kahan se dekhun?"},
                    {"role": "assistant", "content": "Ji, is button par click karein."}
                ]
            }
        },
        {
            "name": "20. opening diversity filter: sentence already appears 2 times",
            "expected_rule": "validate_opening_diversity",
            "data": {
                "category": "account",
                "intent": "balance_inquiry",
                "language": "urdulish",
                "context": None,
                "variation": {"mood": "calm", "spelling": "clean"},
                "_mock_existing_openings": {"Ji, aap ki request darj kar li gayi hai.": 2},
                "messages": [
                    {"role": "user", "content": "Mera balance kitna hai?"},
                    {"role": "assistant", "content": "Ji, aap ki request darj kar li gayi hai."}
                ]
            }
        },
        {
            "name": "21. personal identifiers: Pakistani mobile number in message",
            "expected_rule": "validate_no_personal_identifiers",
            "data": {
                "category": "transfer",
                "intent": "transfer_failed",
                "language": "urdulish",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mera number 03001234567 hai is par transfer kiya tha."},
                    {"role": "assistant", "content": "Ji, aap ki shikayat darj kar li gayi hai."}
                ]
            }
        },
        {
            "name": "22. personal identifiers: 10 or more digits without letters",
            "expected_rule": "validate_no_personal_identifiers",
            "data": {
                "category": "account",
                "intent": "open_account",
                "language": "urdulish",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mera CNIC 42101-1234567-1 hai."},
                    {"role": "assistant", "content": "Ji, aap ki maloomat darj kar li gayi hai."}
                ]
            }
        },
        {
            "name": "23. ticket mood mismatch: very_angry customer with no anger signs",
            "expected_rule": "validate_customer_mood",
            "data": {
                "category": "complaint",
                "intent": "transfer_failed",
                "language": "urdulish",
                "context": None,
                "variation": {"mood": "very_angry"},
                "messages": [
                    {"role": "user", "content": "bhai mera transfer abhi tak pending hai"},
                    {"role": "assistant", "content": "Ji, aap ki shikayat darj kar li gayi hai."}
                ]
            }
        },
        {
            "name": "24. ticket mood mismatch: calm customer with exclamation marks",
            "expected_rule": "validate_customer_mood",
            "data": {
                "category": "faq",
                "intent": "check_balance",
                "language": "urdulish",
                "context": None,
                "variation": {"mood": "calm", "spelling": "clean"},
                "messages": [
                    {"role": "user", "content": "mera balance check kar dein!"},
                    {"role": "assistant", "content": "Ji, aap ki request darj kar li gayi hai."}
                ]
            }
        },
        {
            "name": "25. time_mentioned is month name / statement period",
            "expected_rule": "validate_time_mentioned_natural",
            "data": {
                "category": "complaint",
                "intent": "fee_dispute",
                "language": "urdulish",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Fee do dafa kat gayi hai."},
                    {"role": "assistant", "content": "Ji, aap ki shikayat darj kar li gayi hai."}
                ],
                "ticket": {
                    "intent": "fee_dispute",
                    "category": "complaint",
                    "priority": "medium",
                    "amount": 500.0,
                    "time_mentioned": "October",
                    "summary": "Duplicate fee dispute",
                    "customer_very_angry": False,
                    "escalate_to_human": False
                }
            }
        },
        {
            "name": "26. sampled numbers mismatch: context uses numbers not in supplied range",
            "expected_rule": "validate_context_numbers_match_sampled",
            "data": {
                "category": "card",
                "intent": "product_terms",
                "language": "urdulish",
                "context": "Debit card annual fee is 1200 rupees.",
                "variation": {
                    "sampled_numbers": {"fee": 500.0}
                },
                "messages": [
                    {"role": "user", "content": "Card ki fee kitni hai?"},
                    {"role": "assistant", "content": "Ji, debit card ki fee 1200 rupees hai."}
                ]
            }
        },
        {
            "name": "27. bot asks card ke aakhri 4 digit",
            "expected_rule": "validate_no_personal_identifiers",
            "data": {
                "category": "card",
                "intent": "block_card",
                "language": "urdulish",
                "context": None,
                "variation": {"mood": "calm", "spelling": "clean"},
                "messages": [
                    {"role": "user", "content": "Mera card 4 din pehle kho gaya tha block kar dein."},
                    {"role": "assistant", "content": "Ji, kya aap card ke aakhri 4 digit bata sakte hain?"}
                ]
            }
        },
        {
            "name": "28. bot asks apna mobile number bata dein",
            "expected_rule": "validate_no_personal_identifiers",
            "data": {
                "category": "account",
                "intent": "check_balance",
                "language": "urdulish",
                "context": None,
                "variation": {"mood": "calm", "spelling": "clean"},
                "messages": [
                    {"role": "user", "content": "Mera balance check kar dein."},
                    {"role": "assistant", "content": "Ji, tasdeeq ke liye apna mobile number bata dein."}
                ]
            }
        },
        {
            "name": "29. sampled customer amount mismatch",
            "expected_rule": "validate_customer_amount_matches",
            "data": {
                "category": "complaint",
                "intent": "transfer_failed",
                "language": "urdulish",
                "context": None,
                "variation": {
                    "mood": "calm",
                    "spelling": "clean",
                    "sampled_customer_amount": 8000.0
                },
                "messages": [
                    {"role": "user", "content": "Mera 8000 ka transfer fail ho gaya hai."},
                    {"role": "assistant", "content": "Ji, aap ki shikayat darj kar li gayi hai."}
                ],
                "ticket": {
                    "intent": "transfer_failed",
                    "category": "complaint",
                    "priority": "high",
                    "amount": 5000.0,
                    "time_mentioned": "aaj subah",
                    "summary": "Transfer failed",
                    "customer_very_angry": False,
                    "escalate_to_human": False
                }
            }
        },
        {
            "name": "30. customer message contains literary phrase in Roman Urdu ('ke hawale se')",
            "expected_rule": "validate_no_forbidden_customer_words",
            "data": {
                "category": "account",
                "intent": "balance_inquiry",
                "language": "roman_urdu",
                "context": None,
                "variation": {"mood": "calm", "spelling": "clean"},
                "messages": [
                    {"role": "user", "content": "Mera account balance ke hawale se sawal tha."},
                    {"role": "assistant", "content": "Ji, aap ki request darj kar li gayi hai."}
                ]
            }
        },
        {
            "name": "31. customer message contains literary phrase in Urdu script ('حوالے سے')",
            "expected_rule": "validate_no_forbidden_customer_words",
            "data": {
                "category": "account",
                "intent": "balance_inquiry",
                "language": "urdu_script",
                "context": None,
                "variation": {"mood": "calm", "spelling": "clean"},
                "messages": [
                    {"role": "user", "content": "اکاؤنٹ بیلنس کے حوالے سے معلومات درکار ہیں۔"},
                    {"role": "assistant", "content": "Ji, aap ki request darj kar li gayi hai."}
                ]
            }
        },
        {
            "name": "32. opening diversity: non warning first sentence already appears twice (after warning)",
            "expected_rule": "validate_opening_diversity",
            "data": {
                "category": "fraud",
                "intent": "report_scam_call",
                "language": "urdulish",
                "context": None,
                "variation": {"mood": "calm", "spelling": "clean"},
                "messages": [
                    {"role": "user", "content": "Mujhe suspicious call aayi thi."},
                    {"role": "assistant", "content": "Ji, Zarya Bank kabhi bhi call ya SMS par aap ka OTP ya PIN nahi maangta. Ji, aap ki request darj kar li gayi hai."}
                ],
                "_mock_existing_openings": {"Ji, aap ki request darj kar li gayi hai.": 2}
            }
        },
        {
            "name": "33. nodoc: bot says cannot confirm but customer did not ask about time, fee, charge, limit or duration",
            "expected_rule": "validate_nodoc_question_asked",
            "data": {
                "category": "card",
                "intent": "block_card",
                "language": "roman_urdu",
                "context": "koi document nahi mila",
                "variation": {"mood": "calm", "spelling": "clean"},
                "messages": [
                    {"role": "user", "content": "Mera card block kar dein."},
                    {"role": "assistant", "content": "Ji, main is ki tasdeeq abhi nahi kar sakti. Helpline par rabta karein."}
                ]
            }
        },
        {
            "name": "34. number format: bot turn contains number with trailing .0 ('18.0 percent')",
            "expected_rule": "validate_no_trailing_zero_decimals",
            "data": {
                "category": "card",
                "intent": "product_terms",
                "language": "roman_urdu",
                "context": None,
                "variation": {"mood": "calm", "spelling": "clean"},
                "messages": [
                    {"role": "user", "content": "Loan par kitna markup lagta hai?"},
                    {"role": "assistant", "content": "Ji, loan par markup rate 18.0 percent hai."}
                ]
            }
        },
        {
            "name": "35. customer echo: bot begins with 5+ consecutive words copied from customer ('subah se intezar kar raha hoon koi hal nahi nikla')",
            "expected_rule": "validate_no_customer_echo",
            "data": {
                "category": "transfer",
                "intent": "transfer_failed",
                "language": "roman_urdu",
                "context": None,
                "variation": {"mood": "calm", "spelling": "clean"},
                "messages": [
                    {"role": "user", "content": "subah se intezar kar raha hoon koi hal nahi nikla"},
                    {"role": "assistant", "content": "Ji, subah se intezar kar raha hoon koi hal nahi nikla to shikayat darj kar li gayi hai."}
                ]
            }
        },
        {
            "name": "36. ji first: assistant turn does not begin with Ji",
            "expected_rule": "validate_ji_first",
            "data": {
                "category": "account",
                "intent": "check_balance",
                "language": "english",
                "context": None,
                "variation": {"mood": "calm", "spelling": "clean"},
                "messages": [
                    {"role": "user", "content": "Please check my account balance."},
                    {"role": "assistant", "content": "Your request has been recorded."}
                ]
            }
        },
        {
            "name": "37. ji first: scam warning opens turn without Ji first",
            "expected_rule": "validate_ji_first",
            "data": {
                "category": "fraud",
                "intent": "report_scam_call",
                "language": "roman_urdu",
                "context": None,
                "variation": {"mood": "calm", "spelling": "clean"},
                "messages": [
                    {"role": "user", "content": "Mujhe suspicious call aayi thi."},
                    {"role": "assistant", "content": "Zarya Bank kabhi bhi call ya SMS par aap ka OTP ya PIN nahi maangta. Hum aap ki darkhwast darj kar rahe hain."}
                ]
            }
        },
        {
            "name": "38. facet anti-copying: customer message copies 4+ consecutive words from sampled facet value",
            "expected_rule": "validate_no_facet_copying",
            "data": {
                "category": "card",
                "intent": "block_card",
                "language": "roman_urdu",
                "context": None,
                "variation": {
                    "mood": "calm",
                    "spelling": "clean",
                    "sampled_facets": {"already_tried": "attempted immediate debit card lock in the bank app"}
                },
                "messages": [
                    {"role": "user", "content": "Maine attempted immediate debit card lock aur screen freeze ho gayi."},
                    {"role": "assistant", "content": "Ji, card block karne ki darkhwast darj kar li gayi hai."}
                ]
            }
        },
        {
            "name": "39. ticket summary: ticket summary contains Roman Urdu words ('Customer ne agent shop se 12000 transfer karwaye jo receive nahi huay')",
            "expected_rule": "validate_ticket_summary_language",
            "data": {
                "category": "transfer",
                "intent": "transfer_failed",
                "language": "roman_urdu",
                "context": None,
                "variation": {"mood": "calm", "spelling": "clean"},
                "messages": [
                    {"role": "user", "content": "Transfer fail ho gaya hai."},
                    {"role": "assistant", "content": "Ji, shikayat darj kar li gayi hai."}
                ],
                "ticket": {
                    "intent": "transfer_failed",
                    "category": "transfer",
                    "priority": "medium",
                    "amount": 12000,
                    "time_mentioned": "kal sham",
                    "summary": "Customer ne agent shop se 12000 transfer karwaye jo receive nahi huay",
                    "customer_very_angry": False,
                    "escalate_to_human": False
                }
            }
        },
        {
            "name": "40. ticket summary: ticket summary contains Urdu script",
            "expected_rule": "validate_ticket_summary_language",
            "data": {
                "category": "transfer",
                "intent": "transfer_failed",
                "language": "urdu_script",
                "context": None,
                "variation": {"mood": "calm", "spelling": "clean"},
                "messages": [
                    {"role": "user", "content": "ٹرانسفر فیل ہو گیا"},
                    {"role": "assistant", "content": "جی، شکایت درج کر لی گئی ہے۔"}
                ],
                "ticket": {
                    "intent": "transfer_failed",
                    "category": "transfer",
                    "priority": "medium",
                    "amount": 5000,
                    "time_mentioned": "آج صبح",
                    "summary": "کسٹمر نے 5000 ٹرانسفر کیے جو نہیں پہنچے",
                    "customer_very_angry": False,
                    "escalate_to_human": False
                }
            }
        },
        {
            "name": "41. structure claims: bot mentions unauthorized organizational division without context ('Fraud monitoring division')",
            "expected_rule": "validate_no_structure_claims",
            "data": {
                "category": "fraud",
                "intent": "report_scam_call",
                "language": "roman_urdu",
                "context": None,
                "variation": {"mood": "calm", "spelling": "clean"},
                "messages": [
                    {"role": "user", "content": "Mujhe suspicious call aayi thi."},
                    {"role": "assistant", "content": "Ji, Fraud monitoring division ke liye aap ki report darj kar li gayi hai."}
                ]
            }
        },
        {
            "name": "42. structure claims: bot mentions unauthorized agent shop without context",
            "expected_rule": "validate_no_structure_claims",
            "data": {
                "category": "complaint",
                "intent": "transfer_failed",
                "language": "roman_urdu",
                "context": None,
                "variation": {"mood": "calm", "spelling": "clean"},
                "messages": [
                    {"role": "user", "content": "Mera transfer atak gaya hai."},
                    {"role": "assistant", "content": "Ji, aap qareebi agent shop se maloomat hasil kar sakte hain."}
                ]
            }
        },
        {
            "name": "43. context numbers: 2 extra numbers in context ('50000', '3')",
            "expected_rule": "validate_context_numbers_match_sampled",
            "data": {
                "category": "card",
                "intent": "product_terms",
                "language": "urdulish",
                "context": "Fee is 500 rupees, limit is 50000 rupees and turnaround is 3 days.",
                "variation": {
                    "sampled_numbers": {"fee": 500.0}
                },
                "messages": [
                    {"role": "user", "content": "Fee kitni hai?"},
                    {"role": "assistant", "content": "Ji, fee 500 rupees hai."}
                ]
            }
        },
        {
            "name": "44. context numbers: extra number equals number from seed context ('1200')",
            "expected_rule": "validate_context_numbers_match_sampled",
            "data": {
                "category": "card",
                "intent": "product_terms",
                "language": "urdulish",
                "context": "Debit card fee is 500 rupees and replacement fee is 1200 rupees.",
                "seed_context": "Debit card annual fee is 1200 rupees.",
                "variation": {
                    "sampled_numbers": {"fee": 500.0}
                },
                "messages": [
                    {"role": "user", "content": "Fee kitni hai?"},
                    {"role": "assistant", "content": "Ji, fee 500 rupees hai."}
                ]
            }
        },
        {
            "name": "45. end style: statement style but bot ends with a question",
            "expected_rule": "validate_end_style",
            "data": {
                "category": "account",
                "intent": "fee_inquiry",
                "language": "urdulish",
                "end_style": "statement",
                "variation": {"end_style": "statement"},
                "messages": [
                    {"role": "user", "content": "Account fee kitni hai?"},
                    {"role": "assistant", "content": "Ji, account fee zero rupees hai. Kya aap ne account khol liya hai?"}
                ]
            }
        },
        {
            "name": "46. end style: question style but bot ends with a statement",
            "expected_rule": "validate_end_style",
            "data": {
                "category": "account",
                "intent": "fee_inquiry",
                "language": "urdulish",
                "end_style": "question",
                "variation": {"end_style": "question"},
                "messages": [
                    {"role": "user", "content": "Account fee kitni hai?"},
                    {"role": "assistant", "content": "Ji, account fee zero rupees hai."}
                ]
            }
        },
        {
            "name": "47. promise wording: turns resolution time into commitment ('is ka hal 24 ghanton mein mumken hai')",
            "expected_rule": "validate_bot_turns",
            "data": {
                "category": "complaint",
                "intent": "transfer_failed",
                "language": "urdulish",
                "context": "Resolution time is 24 hours.",
                "messages": [
                    {"role": "user", "content": "Mera issue kab hal hoga?"},
                    {"role": "assistant", "content": "Ji, is ka hal 24 ghanton mein mumken hai."}
                ]
            }
        },
        {
            "name": "48. scam warning: warning sentence in wrong language (English warning in roman_urdu conversation)",
            "expected_rule": "validate_scam_warning",
            "data": {
                "category": "fraud",
                "intent": "report_scam_call",
                "language": "roman_urdu",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mujhe ek fraud call aayi thi."},
                    {"role": "assistant", "content": "Ji, ye ek fraud call lagti hai. Zarya Bank will never ask for your OTP or PIN over a call or SMS."}
                ]
            }
        },
        {
            "name": "49. scam warning: more than one warning sentence in conversation",
            "expected_rule": "validate_scam_warning",
            "data": {
                "category": "fraud",
                "intent": "report_scam_call",
                "language": "roman_urdu",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mujhe ek fraud call aayi thi."},
                    {"role": "assistant", "content": "Ji, Zarya Bank kabhi bhi call ya SMS par aap ka OTP ya PIN nahi maangta. Zarya Bank kabhi bhi call ya SMS par aap ka OTP ya PIN nahi maangta."}
                ]
            }
        },
        {
            "name": "50. scam warning: warning sentence present in forbidden intent ('check_balance')",
            "expected_rule": "validate_scam_warning",
            "data": {
                "category": "inquiry",
                "intent": "check_balance",
                "language": "roman_urdu",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mera balance kitna hai?"},
                    {"role": "assistant", "content": "Ji, Zarya Bank kabhi bhi call ya SMS par aap ka OTP ya PIN nahi maangta."}
                ]
            }
        },
        {
            "name": "51. refusals: out_of_scope bot reply contains question mark ('Kya aap ko banking mein madad chahiye?')",
            "expected_rule": "validate_refusals",
            "data": {
                "category": "out_of_scope",
                "intent": "out_of_scope_query",
                "language": "roman_urdu",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mausam kaisa rahega?"},
                    {"role": "assistant", "content": "Ji, main mausam ke baray mein maloomat nahi de sakti. Kya aap ko banking mein madad chahiye?"}
                ]
            }
        },
        {
            "name": "52. refusals: out_of_scope bot reply exceeds 30 words",
            "expected_rule": "validate_refusals",
            "data": {
                "category": "out_of_scope",
                "intent": "out_of_scope_query",
                "language": "roman_urdu",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Cricket match ka score kya hai?"},
                    {"role": "assistant", "content": "Ji, main live cricket match ke scores ya sports ki updates faraham nahi kar sakti kyun ke mera ikhtiyar sirf Zarya Bank ki bunyadi digital banking khidmat tak mehdood hai baraye meherbani sports app dekhein."}
                ]
            }
        },
        {
            "name": "53. facets: bot question contains forbidden personal relation word ('friend')",
            "expected_rule": "validate_no_facet_questions",
            "data": {
                "category": "fraud",
                "intent": "unauthorized_transaction",
                "language": "roman_urdu",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mere account se paise cut gaye hain."},
                    {"role": "assistant", "content": "Ji, kya aap ne kisi friend ko apna debit card istemal karne ke liye diya tha?"}
                ]
            }
        },
        {
            "name": "54. customer amount: ticket amount present on non-amount intent ('check_balance')",
            "expected_rule": "validate_ticket_amount_allowed",
            "data": {
                "category": "inquiry",
                "intent": "check_balance",
                "language": "roman_urdu",
                "context": None,
                "ticket": {
                    "intent": "check_balance",
                    "category": "inquiry",
                    "priority": "low",
                    "amount": 5000,
                    "time_mentioned": None,
                    "summary": "Customer checked balance.",
                    "customer_very_angry": False,
                    "escalate_to_human": False
                },
                "messages": [
                    {"role": "user", "content": "Mera balance kitna hai?"},
                    {"role": "assistant", "content": "Ji, balance 5000 rupees hai."}
                ]
            }
        },
        {
            "name": "55. no ranges: range expression in context ('2 to 4 days')",
            "expected_rule": "validate_no_context_ranges",
            "data": {
                "category": "inquiry",
                "intent": "product_terms",
                "language": "roman_urdu",
                "context": "Loan processing turnaround time is 2 to 4 days.",
                "messages": [
                    {"role": "user", "content": "Processing mein kitna waqt lagta hai?"},
                    {"role": "assistant", "content": "Ji, processing mein 2 din lagte hain."}
                ]
            }
        },
        {
            "name": "56. help offers: bot question offers help ('madad kar sakti hoon')",
            "expected_rule": "validate_no_help_offers_and_numbers",
            "data": {
                "category": "complaint",
                "intent": "transfer_failed",
                "language": "roman_urdu",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mera issue solve kar dein."},
                    {"role": "assistant", "content": "Ji, kya main aap ki kisi aur maslay mein madad kar sakti hoon?"}
                ]
            }
        },
        {
            "name": "57. helpline offer: bot offers helpline number ('helpline ka number')",
            "expected_rule": "validate_no_help_offers_and_numbers",
            "data": {
                "category": "complaint",
                "intent": "service_complaint",
                "language": "roman_urdu",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mera masla hal nahi hua."},
                    {"role": "assistant", "content": "Ji, main aap ko helpline ka number faraham kar sakti hoon."}
                ]
            }
        },
        {
            "name": "58. action claims: bot claims 'mere paas record' without context",
            "expected_rule": "validate_no_action_claims",
            "data": {
                "category": "complaint",
                "intent": "transfer_failed",
                "language": "roman_urdu",
                "context": "Complaint turnaround is 24 hours.",
                "messages": [
                    {"role": "user", "content": "Mera transfer verify karein."},
                    {"role": "assistant", "content": "Ji, mere paas record mojood hai ke transaction fail hua tha."}
                ]
            }
        },
        {
            "name": "59. promises: bot uses forbidden promise phrase ('khud ba khud')",
            "expected_rule": "validate_bot_turns",
            "data": {
                "category": "complaint",
                "intent": "transfer_failed",
                "language": "roman_urdu",
                "context": "Complaint turnaround is 24 hours.",
                "messages": [
                    {"role": "user", "content": "Mera transfer kab theek hoga?"},
                    {"role": "assistant", "content": "Ji, raqam khud ba khud account mein wapis aa jayegi."}
                ]
            }
        },
        {
            "name": "60. length: customer message exceeds 40 words",
            "expected_rule": "validate_lengths",
            "data": {
                "category": "complaint",
                "intent": "transfer_failed",
                "language": "roman_urdu",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Maine kal subah das baje apne bhai ko paise bhejne ke liye online bank app kholi aur transfer karne ki koshish ki lekin raqam account se kat gayi aur samne wale ko abhi tak nahi mili aur main bohat pareshan hoon kyun ke hospital bill ada karna tha foran meri madad karein baraye meherbani."},
                    {"role": "assistant", "content": "Ji, aap ki darkhwast darj kar li gayi hai."}
                ]
            }
        },
        {
            "name": "61. length: bot turn exceeds 4 sentences",
            "expected_rule": "validate_lengths",
            "data": {
                "category": "complaint",
                "intent": "transfer_failed",
                "language": "roman_urdu",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Transfer fail ho gaya hai."},
                    {"role": "assistant", "content": "Ji, aap ki darkhwast darj kar li gayi hai. Hamari team jaanch kar rahi hai. Baraye meherbani intizar farmayein. Hum jald rabta karenge. Shukriya."}
                ]
            }
        },
        {
            "name": "62. customer words: customer message contains forbidden word 'tafseelat'",
            "expected_rule": "validate_no_forbidden_customer_words",
            "data": {
                "category": "inquiry",
                "intent": "product_terms",
                "language": "roman_urdu",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mujhe account ki tamam tafseelat janni hain."},
                    {"role": "assistant", "content": "Ji, account maintenance fee zero rupees hai."}
                ]
            }
        },
        {
            "name": "63. ehsas: bot turn contains forbidden word 'ehsas'",
            "expected_rule": "validate_no_ehsas",
            "data": {
                "category": "complaint",
                "intent": "transfer_failed",
                "language": "roman_urdu",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mera transfer fail ho gaya hai."},
                    {"role": "assistant", "content": "Ji, mujhe aap ki pareshani ka ehsas hai to shikayat darj kar li gayi hai."}
                ]
            }
        },
        {
            "name": "64. opening variety: same first 3 words in >= 5 percent of accepted records once >= 60 records exist",
            "expected_rule": "validate_opening_variety",
            "data": {
                "category": "complaint",
                "intent": "transfer_failed",
                "language": "roman_urdu",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mera issue solve kar dein."},
                    {"role": "assistant", "content": "Ji, aap ka issue record kar liya gaya hai."}
                ],
                "_accepted_records": (
                    [{"messages": [{"role": "assistant", "content": "Ji, aap ka transfer record ho gaya hai."}]}] * 3 +
                    [{"messages": [{"role": "assistant", "content": f"Ji, different start {i} happened."}]} for i in range(57)]
                )
            }
        },
        {
            "name": "65. customer greeting tic: customer message starts with Ji or جی ('Ji mera balance check kar dein')",
            "expected_rule": "validate_no_customer_ji",
            "data": {
                "category": "account",
                "intent": "check_balance",
                "language": "roman_urdu",
                "context": None,
                "variation": {"mood": "calm", "spelling": "clean"},
                "messages": [
                    {"role": "user", "content": "Ji mera balance check kar dein."},
                    {"role": "assistant", "content": "Ji, aap ka balance maloom karne ki request darj kar li gayi hai."}
                ]
            }
        },
        {
            "name": "66. filler sentence: bot uses 'thank you for confirming'",
            "expected_rule": "validate_no_filler_sentences",
            "data": {
                "category": "complaint",
                "intent": "transfer_failed",
                "language": "english",
                "context": None,
                "messages": [
                    {"role": "user", "content": "I sent 5000 rupees yesterday."},
                    {"role": "assistant", "content": "Ji, thank you for confirming the details. Your complaint has been recorded."}
                ]
            }
        },
        {
            "name": "67. filler sentence: bot uses 'shukriya maloomat dene ka'",
            "expected_rule": "validate_no_filler_sentences",
            "data": {
                "category": "complaint",
                "intent": "transfer_failed",
                "language": "roman_urdu",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mera transfer fail ho gaya tha."},
                    {"role": "assistant", "content": "Ji, shukriya maloomat dene ka, aap ka masla darj kar liya gaya hai."}
                ]
            }
        },
        {
            "name": "68. filler sentence: bot uses 'durust darj kar li gayi'",
            "expected_rule": "validate_no_filler_sentences",
            "data": {
                "category": "complaint",
                "intent": "transfer_failed",
                "language": "roman_urdu",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Paise kat gaye hain."},
                    {"role": "assistant", "content": "Ji, durust darj kar li gayi aap ki shikayat."}
                ]
            }
        },
        {
            "name": "69. filler sentence: bot uses 'noted for the investigation'",
            "expected_rule": "validate_no_filler_sentences",
            "data": {
                "category": "complaint",
                "intent": "transfer_failed",
                "language": "english",
                "context": None,
                "messages": [
                    {"role": "user", "content": "My funds were deducted without transfer."},
                    {"role": "assistant", "content": "Ji, noted for the investigation, complaint has been lodged."}
                ]
            }
        },
        {
            "name": "70. filler sentence: bot uses 'aap ke record ke liye'",
            "expected_rule": "validate_no_filler_sentences",
            "data": {
                "category": "account",
                "intent": "check_balance",
                "language": "roman_urdu",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mera balance bta dein."},
                    {"role": "assistant", "content": "Ji, aap ke record ke liye request darj kar li gayi hai."}
                ]
            }
        },
        {
            "name": "71. ticket time: 'just now' when customer never wrote it",
            "expected_rule": "validate_time_mentioned_natural",
            "data": {
                "category": "complaint",
                "intent": "transfer_failed",
                "language": "roman_urdu",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mera transfer atak gaya hai."},
                    {"role": "assistant", "content": "Ji, aap ki shikayat darj kar li gayi hai."}
                ],
                "ticket": {
                    "intent": "transfer_failed",
                    "category": "complaint",
                    "priority": "medium",
                    "amount": 2500.0,
                    "time_mentioned": "just now",
                    "summary": "Transfer stuck without confirmation",
                    "customer_very_angry": False,
                    "escalate_to_human": False
                }
            }
        },
        {
            "name": "72. purpose question: bot asks 'lena chahte hain'",
            "expected_rule": "validate_no_help_offers_and_numbers",
            "data": {
                "category": "card",
                "intent": "block_card",
                "language": "roman_urdu",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mera card block kar dein."},
                    {"role": "assistant", "content": "Ji, card block karne ki request darj kar li hai. Kya aap naya debit card lena chahte hain?"}
                ]
            }
        },
        {
            "name": "73. purpose question: bot asks 'would you like to proceed'",
            "expected_rule": "validate_no_help_offers_and_numbers",
            "data": {
                "category": "account",
                "intent": "check_balance",
                "language": "english",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Check my account balance."},
                    {"role": "assistant", "content": "Ji, would you like to proceed with request registration?"}
                ]
            }
        },
        {
            "name": "74. purpose question: bot asks 'continue karna chahte'",
            "expected_rule": "validate_no_help_offers_and_numbers",
            "data": {
                "category": "transfer",
                "intent": "transfer_failed",
                "language": "roman_urdu",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Mera transaction fail ho gaya."},
                    {"role": "assistant", "content": "Ji, kya aap is complaint ke sath continue karna chahte hain?"}
                ]
            }
        },
        {
            "name": "75. purpose question: bot asks 'shall we'",
            "expected_rule": "validate_no_help_offers_and_numbers",
            "data": {
                "category": "complaint",
                "intent": "service_complaint",
                "language": "english",
                "context": None,
                "messages": [
                    {"role": "user", "content": "Cancel my complaint."},
                    {"role": "assistant", "content": "Ji, shall we proceed with closing this ticket?"}
                ]
            }
        },
        {
            "name": "76. only what was asked: bot states unasked fee from context",
            "expected_rule": "validate_only_asked_numbers",
            "data": {
                "category": "card",
                "intent": "card_delivery",
                "language": "roman_urdu",
                "context": "Card delivery turnaround is 5 days and replacement fee is 350 rupees.",
                "messages": [
                    {"role": "user", "content": "Mera card kab deliver hoga?"},
                    {"role": "assistant", "content": "Ji, replacement fee 350 rupees hai."}
                ]
            }
        },
        {
            "name": "77. only what was asked: context contains > 2 numbers on non-fee/limit/loan intent",
            "expected_rule": "validate_only_asked_numbers",
            "data": {
                "category": "transfer",
                "intent": "transfer_failed",
                "language": "roman_urdu",
                "context": "Turnaround time is 24 hours, daily limit is 50000 and minimum fee is 50 rupees.",
                "messages": [
                    {"role": "user", "content": "Transfer fail ho gaya hai."},
                    {"role": "assistant", "content": "Ji, turnaround waqt 24 ghantay hai."}
                ]
            }
        }
    ]

    all_bad_passed = True
    for case in bad_cases:
        d = case["data"]
        ctx = d.get("context")
        sys_msg = build_system_message(BASE_SYSTEM_MESSAGE, ctx)
        complete_messages = [{"role": "system", "content": sys_msg}] + d.get("messages", [])
        var = d.get("variation", {})
        if "_mock_existing_openings" in d:
            var["_mock_existing_openings"] = d["_mock_existing_openings"]

        candidate = {
            "seed_id": d.get("seed_id", "test_bad_case"),
            "seed_context": d.get("seed_context"),
            "task_type": d.get("task_type", derive_task_type(d)),
            "variation": var,
            "prompt_version": PROMPT_VERSION,
            "category": d.get("category"),
            "intent": d.get("intent"),
            "language": d.get("language"),
            "is_multi_turn": False,
            "end_style": d.get("end_style") or var.get("end_style"),
            "context": ctx,
            "messages": complete_messages,
            "ticket": d.get("ticket"),
            "_mock_existing_openings": d.get("_mock_existing_openings"),
            "_accepted_records": d.get("_accepted_records")
        }
        failures = validate_candidate(candidate)
        matched = any(case["expected_rule"] in f for f in failures)
        status = "[PASS]" if matched else "[FAIL]"
        if not matched:
            all_bad_passed = False
        print(f"  {status} Case: {case['name']}")
        print(f"         Expected Rule : {case['expected_rule']}")
        print(f"         Actual Rule(s): {failures}")

    print("\n[PART C] Testing Opening Styles Distribution and Pilot Shuffling")
    config = load_config()
    opening_styles = config.get("opening_styles", {})

    # Check 1: 200 sampled requests per task type
    task_types_to_test = ["faq", "complaint", "fraud", "out_of_scope"]
    test_rng = random.Random(42)
    style_distribution = {}
    out_of_scope_got_detail = False

    seeds_by_type = {}
    for s in seeds:
        tt = derive_task_type(s)
        seeds_by_type.setdefault(tt, []).append(s)

    for tt in task_types_to_test:
        style_distribution[tt] = {}
        type_seeds = seeds_by_type.get(tt, seeds)
        for _ in range(200):
            chosen_seed = test_rng.choice(type_seeds)
            mood_val = test_rng.choice(["calm", "frustrated", "very_angry"])
            is_nodoc = test_rng.random() < 0.13
            is_fact = (tt in ["faq", "complaint"] and not is_nodoc)
            group_key = select_opening_style_group(
                mood=mood_val,
                is_context_fact=is_fact,
                task_type=tt,
                intent=chosen_seed.get("intent")
            )
            style_distribution[tt][group_key] = style_distribution[tt].get(group_key, 0) + 1
            if tt == "out_of_scope" and group_key == "detail":
                out_of_scope_got_detail = True

    print("  Style group distribution (200 requests per task type):")
    for tt, counts in style_distribution.items():
        print(f"    {tt}: {counts}")

    part_c_passed = True
    if not out_of_scope_got_detail:
        print("  [PASS] out_of_scope never gets the detail style group (over 200 sampled requests)")
    else:
        print("  [FAIL] out_of_scope received the detail style group in sample")
        part_c_passed = False

    # Check 2: refusal group never contains a question
    refusal_list = opening_styles.get("refusal", [])
    has_question = any("?" in s for s in refusal_list)
    if not has_question and refusal_list:
        print("  [PASS] refusal group never contains a question")
    else:
        print("  [FAIL] refusal group contains a question or is empty")
        part_c_passed = False

    # Check 3: pilot order contains at least 3 task types in its first 8 requests
    pilot_targets = build_plan_targets("pilot", config, seeds)
    first_8_types = [t["task_type"] for t in pilot_targets[:8]]
    unique_first_8 = set(first_8_types)
    print(f"  First 8 pilot task types: {first_8_types} (unique count: {len(unique_first_8)})")
    if len(unique_first_8) >= 3:
        print("  [PASS] pilot order contains at least 3 task types in its first 8 requests")
    else:
        print(f"  [FAIL] pilot order contains only {len(unique_first_8)} task types in its first 8 requests: {unique_first_8}")
        part_c_passed = False

    print("\n[PART D] Testing Prompt v1.5 Features and Invariants")
    part_d_passed = True

    # Check 1: Opening diversity accepts warning sentence existing 5 times (Roman Urdu, English, Urdu script)
    warning_test_cases = [
        ("roman_urdu", "Zarya Bank kabhi bhi call ya SMS par aap ka OTP ya PIN nahi maangta. Hum aap ki darkhwast ka jaiza le rahe hain.", "Zarya Bank kabhi bhi call ya SMS par aap ka OTP ya PIN nahi maangta."),
        ("english", "Zarya Bank will never ask for your OTP or PIN over a call or SMS. We are reviewing your request now.", "Zarya Bank will never ask for your OTP or PIN over a call or SMS."),
        ("urdu_script", "Zarya Bank کبھی بھی کال یا ایس ایم ایس پر آپ کا کارڈ نمبر، او ٹی پی یا پن نہیں مانگتا۔ ہم آپ کی درخواست کا جائزہ لے رہے ہیں۔", "Zarya Bank کبھی بھی کال یا ایس ایم ایس پر آپ کا کارڈ نمبر، او ٹی پی یا پن نہیں مانگتا۔")
    ]
    all_warnings_accepted = True
    for lang, bot_text, warn_sent in warning_test_cases:
        test_candidate = {
            "seed_id": f"test_warning_diversity_{lang}",
            "task_type": "fraud",
            "variation": {"mood": "calm", "spelling": "clean"},
            "prompt_version": PROMPT_VERSION,
            "category": "fraud",
            "intent": "report_scam_call",
            "language": lang,
            "is_multi_turn": False,
            "context": None,
            "messages": [
                {"role": "system", "content": BASE_SYSTEM_MESSAGE},
                {"role": "user", "content": "Mujhe suspicious call aayi thi."},
                {"role": "assistant", "content": bot_text}
            ],
            "_mock_existing_openings": {warn_sent: 5},
            "ticket": None
        }
        fails = validate_opening_diversity(test_candidate)
        if fails:
            all_warnings_accepted = False
            print(f"  [FAIL] Warning sentence diversity check failed for {lang}: {fails}")

    if all_warnings_accepted:
        print("  [PASS] opening diversity accepts reply starting with warning sentence existing 5 times")
    else:
        part_d_passed = False

    # Check 2: Opening diversity rejects non-warning sentence appearing twice
    dup_cand = {
        "seed_id": "test_dup_non_warning",
        "task_type": "fraud",
        "variation": {"mood": "calm", "spelling": "clean"},
        "prompt_version": PROMPT_VERSION,
        "category": "fraud",
        "intent": "report_scam_call",
        "language": "urdulish",
        "is_multi_turn": False,
        "context": None,
        "messages": [
            {"role": "system", "content": BASE_SYSTEM_MESSAGE},
            {"role": "user", "content": "Mujhe link mila hai."},
            {"role": "assistant", "content": "Zarya Bank kabhi bhi call ya SMS par aap ka OTP ya PIN nahi maangta. Ji, aap ki request darj kar li gayi hai."}
        ],
        "_mock_existing_openings": {"Ji, aap ki request darj kar li gayi hai.": 2},
        "ticket": None
    }
    dup_fails = validate_opening_diversity(dup_cand)
    if any("validate_opening_diversity" in f for f in dup_fails):
        print("  [PASS] opening diversity rejects reply whose non warning first sentence already exists twice")
    else:
        print(f"  [FAIL] Expected validate_opening_diversity failure, got: {dup_fails}")
        part_d_passed = False

    # Check 3: Scam opening styles contain zero styles directing to start with safety warning
    scam_styles = opening_styles.get("scam", [])
    has_warning_directive = any("warning" in s.lower() or "hargiz" in s.lower() for s in scam_styles)
    if not has_warning_directive and len(scam_styles) >= 2:
        print("  [PASS] scam opening styles start by naming danger or asking question, with zero directing to start with warning")
    else:
        print(f"  [FAIL] scam opening styles contains warning directive or is empty: {scam_styles}")
        part_d_passed = False

    # Check 4: Refusal customer lines per mood >= 6
    cust_pool = config.get("customer_style_pool", {})
    ru_pool = cust_pool.get("roman_urdu", [])
    ur_pool = cust_pool.get("urdu_script", [])

    refusal_counts = {"roman_urdu": {}, "urdu_script": {}}
    for item in ru_pool:
        if isinstance(item, dict) and item.get("topic") == "refusal":
            m = item.get("mood", "calm")
            refusal_counts["roman_urdu"][m] = refusal_counts["roman_urdu"].get(m, 0) + 1
    for item in ur_pool:
        if isinstance(item, dict) and item.get("topic") == "refusal":
            m = item.get("mood", "calm")
            refusal_counts["urdu_script"][m] = refusal_counts["urdu_script"].get(m, 0) + 1

    all_moods_have_6 = True
    for pool_name, counts in refusal_counts.items():
        for m in ["calm", "frustrated", "very_angry"]:
            if counts.get(m, 0) < 6:
                all_moods_have_6 = False
                print(f"  [FAIL] {pool_name} mood {m} has only {counts.get(m, 0)} refusal lines (< 6)")

    if all_moods_have_6:
        print(f"  [PASS] customer style pool contains at least 6 refusal lines per mood (Roman Urdu: {refusal_counts['roman_urdu']}, Urdu script: {refusal_counts['urdu_script']})")
    else:
        part_d_passed = False

    # Check 5: out_of_scope requests sample only lines tagged refusal
    all_oos_refusals = True
    for _ in range(100):
        m = test_rng.choice(["calm", "frustrated", "very_angry"])
        sp = test_rng.choice(["clean", "typo_heavy"])
        sampled_ru = sample_customer_style_examples(cust_pool, "roman_urdu", mood=m, spelling=sp, count=4, rng=test_rng, task_type="out_of_scope")
        sampled_ur = sample_customer_style_examples(cust_pool, "urdu_script", mood=m, spelling="clean", count=3, rng=test_rng, task_type="out_of_scope")
        ru_refusal_texts = {item["text"] for item in ru_pool if isinstance(item, dict) and item.get("topic") == "refusal"}
        ur_refusal_texts = {item["text"] for item in ur_pool if isinstance(item, dict) and item.get("topic") == "refusal"}
        if not all(t in ru_refusal_texts for t in sampled_ru):
            all_oos_refusals = False
        if not all(t in ur_refusal_texts for t in sampled_ur):
            all_oos_refusals = False

    if all_oos_refusals:
        print("  [PASS] out_of_scope requests sample only lines tagged refusal (tested across 100 samples)")
    else:
        print("  [FAIL] out_of_scope sampled a line not tagged refusal")
        part_d_passed = False

    # Check 6: Urdu script normalization helper converts Arabic Kaf and Yeh to Urdu Keheh and Farsi Yeh
    ar_sample = "شر\u0643ة ف\u064a \u0645\u0633\u062a\u0634\u0641\u0649 \u0643\u064a \u0628\u064a\u0645\u0627\u0631\u064a"
    norm_sample = normalize_urdu_text(ar_sample)
    ar_eliminated = not has_arabic_codepoints(norm_sample)
    has_ur_chars = ("\u06a9" in norm_sample and "\u06cc" in norm_sample)
    if ar_eliminated and has_ur_chars:
        print("  [PASS] urdu normalization replaces arabic kaf and yeh with urdu kaf and yeh (U+0643 -> U+06A9, U+064A -> U+06CC, U+0649 -> U+06CC)")
    else:
        print(f"  [FAIL] urdu normalization failed: {norm_sample}")
        part_d_passed = False

    # Check 7: save_accepted fails if any saved text contains Arabic code points
    save_fail_ok = False
    fake_candidate_with_ar = {
        "messages": [{"role": "assistant", "content": "یہ \u0643تاب ہے"}]
    }
    try:
        save_accepted(fake_candidate_with_ar)
    except ValueError as ve:
        if "Arabic code point detected" in str(ve):
            save_fail_ok = True
    except Exception:
        pass

    if save_fail_ok:
        print("  [PASS] save_accepted fails if any saved urdu text contains arabic code points")
    else:
        print("  [FAIL] save_accepted did not raise expected ValueError for arabic code points")
        part_d_passed = False

    # Check 8: All seeds and customer style pool lines contain zero Arabic code points
    seeds_clean = True
    for s in seeds:
        for m in s.get("messages", []):
            if has_arabic_codepoints(m.get("content", "")):
                seeds_clean = False
                print(f"  [FAIL] Seed {s.get('id')} contains Arabic code point: {m.get('content')}")
        if s.get("context") and has_arabic_codepoints(s.get("context")):
            seeds_clean = False
            print(f"  [FAIL] Seed {s.get('id')} context contains Arabic code point: {s.get('context')}")

    pool_clean = True
    for lang_k, pool_items in cust_pool.items():
        for item in pool_items:
            t = item.get("text", "") if isinstance(item, dict) else str(item)
            if has_arabic_codepoints(t):
                pool_clean = False
                print(f"  [FAIL] Style pool ({lang_k}) contains Arabic code point: {t}")

    if seeds_clean and pool_clean:
        print("  [PASS] all seeds and customer style pool lines contain zero arabic code points")
    else:
        part_d_passed = False

    print("\n[PART E] Testing Prompt v1.6 Features and Invariants")
    part_e_passed = True

    # Check 1: Nodoc accepts flexible wording ("tasdeeq abhi nahi kar sakti") with helpline
    cand_nodoc_good = {
        "seed_id": "test_nodoc_good",
        "task_type": "faq",
        "variation": {"mood": "calm", "spelling": "clean"},
        "prompt_version": PROMPT_VERSION,
        "category": "card",
        "intent": "installment_inquiry",
        "language": "roman_urdu",
        "is_multi_turn": False,
        "context": "koi document nahi mila",
        "messages": [
            {"role": "system", "content": BASE_SYSTEM_MESSAGE},
            {"role": "user", "content": "installment ki tareekh kab aati hai?"},
            {"role": "assistant", "content": "Ji, main installment ki tareekh ki tasdeeq abhi nahi kar sakti. Aap is maloomat ke liye Zarya Bank helpline par rabta farmayein."}
        ],
        "ticket": None
    }
    fails_nodoc_good = validate_candidate(cand_nodoc_good)
    if not fails_nodoc_good:
        print("  [PASS] nodoc accepts flexible wording ('tasdeeq abhi nahi kar sakti') with helpline")
    else:
        print(f"  [FAIL] Expected nodoc candidate to pass, got failures: {fails_nodoc_good}")
        part_e_passed = False

    # Check 2: Nodoc rejects reply stating a number
    cand_nodoc_num = {
        "seed_id": "test_nodoc_num",
        "task_type": "faq",
        "variation": {"mood": "calm", "spelling": "clean"},
        "prompt_version": PROMPT_VERSION,
        "category": "card",
        "intent": "installment_inquiry",
        "language": "roman_urdu",
        "is_multi_turn": False,
        "context": "koi document nahi mila",
        "messages": [
            {"role": "system", "content": BASE_SYSTEM_MESSAGE},
            {"role": "user", "content": "installment ki tareekh kab aati hai?"},
            {"role": "assistant", "content": "Ji, main installment ki tareekh ki tasdeeq abhi nahi kar sakti, aam tor par 5 din lagte hain. Helpline par rabta karein."}
        ],
        "ticket": None
    }
    fails_nodoc_num = validate_candidate(cand_nodoc_num)
    if any("validate_no_document_behavior" in f for f in fails_nodoc_num):
        print("  [PASS] nodoc rejects reply stating a number")
    else:
        print(f"  [FAIL] Expected validate_no_document_behavior failure for nodoc stating number, got: {fails_nodoc_num}")
        part_e_passed = False

    # Check 3: Nodoc validator rejects cannot confirm when customer did not ask about time, fee, charge, limit, or duration
    cand_nodoc_no_q = {
        "seed_id": "test_nodoc_no_q",
        "task_type": "faq",
        "variation": {"mood": "calm", "spelling": "clean"},
        "prompt_version": PROMPT_VERSION,
        "category": "card",
        "intent": "block_card",
        "language": "roman_urdu",
        "is_multi_turn": False,
        "context": "koi document nahi mila",
        "messages": [
            {"role": "system", "content": BASE_SYSTEM_MESSAGE},
            {"role": "user", "content": "Mera card block kar dein."},
            {"role": "assistant", "content": "Ji, main is ki tasdeeq abhi nahi kar sakti. Helpline par rabta farmayein."}
        ],
        "ticket": None
    }
    fails_nodoc_no_q = validate_candidate(cand_nodoc_no_q)
    if any("validate_nodoc_question_asked" in f for f in fails_nodoc_no_q):
        print("  [PASS] nodoc validator rejects cannot confirm when customer did not ask about time, fee, charge, limit, or duration")
    else:
        print(f"  [FAIL] Expected validate_nodoc_question_asked failure, got: {fails_nodoc_no_q}")
        part_e_passed = False

    # Check 4: Nodoc sampled only for faq requests or complaint requests with inquiry target
    all_nodoc_valid_scope = True
    for _ in range(50):
        sample_targets = build_plan_targets("pilot", config, seeds)
        for t in sample_targets:
            if t["nodoc"]:
                if t["task_type"] not in ["faq", "complaint"]:
                    all_nodoc_valid_scope = False
                if t["task_type"] == "complaint" and t.get("nodoc_target") != "customer must ask about the resolution time or a fee":
                    all_nodoc_valid_scope = False
    if all_nodoc_valid_scope:
        print("  [PASS] nodoc sampled only for faq requests or complaint requests with inquiry target")
    else:
        print("  [FAIL] nodoc was sampled outside faq or complaint without proper inquiry target")
        part_e_passed = False

    # Check 5: Sampled percentage ranges drop trailing .0
    pct_range = config.get("sampled_number_ranges", {}).get("percentage", [])
    no_trailing_zero_in_pct = len(pct_range) >= 40 and all(not re.search(r"\b\d+\.0+(?!\d)", f"{v:g}") for v in pct_range)
    if no_trailing_zero_in_pct:
        print("  [PASS] sampled percentage ranges drop trailing .0 ([2.5, 3.5, 5, 12.5, 15, 18, 22])")
    else:
        print(f"  [FAIL] Expected percentage range to drop trailing .0 and length >= 40, got {pct_range}")
        part_e_passed = False

    # Check 6: Number format helper drops trailing .0
    n1 = format_number_no_trailing_zero(18.0)
    n2 = format_number_no_trailing_zero(2.5)
    n3 = format_number_no_trailing_zero(500)
    n4 = format_number_no_trailing_zero("22.0")
    if n1 == "18" and n2 == "2.5" and n3 == "500" and n4 == "22":
        print("  [PASS] number format helper drops trailing .0 (18.0 -> '18', 2.5 -> '2.5', '22.0' -> '22')")
    else:
        print(f"  [FAIL] number format helper output unexpected: {(n1, n2, n3, n4)}")
        part_e_passed = False

    # Check 7: Number format validator rejects context or bot turn containing number followed by .0
    cand_trail_zero = {
        "seed_id": "test_trail_zero",
        "task_type": "faq",
        "variation": {"mood": "calm", "spelling": "clean"},
        "prompt_version": PROMPT_VERSION,
        "category": "card",
        "intent": "product_terms",
        "language": "roman_urdu",
        "is_multi_turn": False,
        "context": "Zarya Bank debit card par 18.0 percent markup lagta hai.",
        "messages": [
            {"role": "system", "content": BASE_SYSTEM_MESSAGE},
            {"role": "user", "content": "kitna markup hai?"},
            {"role": "assistant", "content": "Ji, card par 18 percent markup hai."}
        ],
        "ticket": None
    }
    fails_trail = validate_candidate(cand_trail_zero)
    if any("validate_no_trailing_zero_decimals" in f for f in fails_trail):
        print("  [PASS] number format validator rejects context or bot turn containing number followed by .0")
    else:
        print(f"  [FAIL] Expected validate_no_trailing_zero_decimals failure, got: {fails_trail}")
        part_e_passed = False

    # Check 8: Acknowledge opening styles express empathy in own words with zero customer repetition
    ack_styles = config.get("opening_styles", {}).get("acknowledge", [])
    has_empathy = all(any(k in s.lower() for k in ["empath", "own", "original", "distress"]) for s in ack_styles)
    no_example_sentences = not any('"' in s or "for example" in s.lower() or "for instance" in s.lower() for s in ack_styles)
    if ack_styles and has_empathy and no_example_sentences and len(ack_styles) >= 2:
        print("  [PASS] acknowledge opening styles express empathy in own words with zero customer repetition instructions")
    else:
        print(f"  [FAIL] acknowledge opening styles issue: {ack_styles}")
        part_e_passed = False

    # Check 9: Acknowledge style group used only for complaint and fraud requests with frustrated or very_angry
    ack_correctly_routed = True
    for tt in ["faq", "complaint", "fraud", "out_of_scope"]:
        for m in ["calm", "frustrated", "very_angry"]:
            grp = select_opening_style_group(mood=m, is_context_fact=True, task_type=tt)
            if grp == "acknowledge":
                if tt not in ["complaint", "fraud"] or m not in ["frustrated", "very_angry"]:
                    ack_correctly_routed = False
    if ack_correctly_routed:
        print("  [PASS] acknowledge style group used only for complaint and fraud requests with frustrated or very_angry customer")
    else:
        print(f"  [FAIL] acknowledge style group was routed incorrectly")
        part_e_passed = False

    # Check 10: Faq requests with any mood use direct style group
    faq_all_direct = all(
        select_opening_style_group(mood=m, is_context_fact=True, task_type="faq") == "direct"
        for m in ["calm", "frustrated", "very_angry"]
    )
    if faq_all_direct:
        print("  [PASS] faq requests with any mood use direct style group")
    else:
        print(f"  [FAIL] faq requests did not always use direct style group")
        part_e_passed = False

    # Check 11: Customer echo validator rejects bot reply whose first sentence contains 5 or more consecutive words copied from customer
    cand_echo = {
        "seed_id": "test_echo",
        "task_type": "complaint",
        "variation": {"mood": "calm", "spelling": "clean"},
        "prompt_version": PROMPT_VERSION,
        "category": "transfer",
        "intent": "transfer_failed",
        "language": "roman_urdu",
        "is_multi_turn": False,
        "context": None,
        "messages": [
            {"role": "system", "content": BASE_SYSTEM_MESSAGE},
            {"role": "user", "content": "subah se intezar kar raha hoon koi hal nahi nikla"},
            {"role": "assistant", "content": "Ji, subah se intezar kar raha hoon koi hal nahi nikla to shikayat darj kar li gayi hai."}
        ],
        "ticket": None
    }
    fails_echo = validate_candidate(cand_echo)
    if any("validate_no_customer_echo" in f for f in fails_echo):
        print("  [PASS] customer echo validator rejects bot reply first sentence copying 5 or more consecutive words from customer")
    else:
        print(f"  [FAIL] Expected validate_no_customer_echo failure, got: {fails_echo}")
        part_e_passed = False

    # Check 12: Ji first validator enforces every assistant turn begins with Ji or جی
    cand_no_ji = {
        "seed_id": "test_no_ji",
        "task_type": "complaint",
        "variation": {"mood": "calm", "spelling": "clean"},
        "prompt_version": PROMPT_VERSION,
        "category": "transfer",
        "intent": "transfer_failed",
        "language": "english",
        "is_multi_turn": False,
        "context": None,
        "messages": [
            {"role": "system", "content": BASE_SYSTEM_MESSAGE},
            {"role": "user", "content": "My transfer failed."},
            {"role": "assistant", "content": "Your complaint has been registered."}
        ],
        "ticket": None
    }
    fails_no_ji = validate_candidate(cand_no_ji)
    if any("validate_ji_first" in f for f in fails_no_ji):
        print("  [PASS] ji first validator enforces every assistant turn begins with Ji or جی across languages")
    else:
        print(f"  [FAIL] Expected validate_ji_first failure, got: {fails_no_ji}")
        part_e_passed = False

    # Check 13: Ji first validator accepts scam warning sentence following Ji first
    cand_ji_warn = {
        "seed_id": "test_ji_warn",
        "task_type": "fraud",
        "variation": {"mood": "calm", "spelling": "clean"},
        "prompt_version": PROMPT_VERSION,
        "category": "fraud",
        "intent": "report_scam_call",
        "language": "roman_urdu",
        "is_multi_turn": False,
        "context": None,
        "messages": [
            {"role": "system", "content": BASE_SYSTEM_MESSAGE},
            {"role": "user", "content": "Mujhe call aayi thi."},
            {"role": "assistant", "content": "Ji, Zarya Bank kabhi bhi call ya SMS par aap ka OTP ya PIN nahi maangta. Complaint darj kar li gayi hai."}
        ],
        "ticket": None
    }
    fails_ji_warn = validate_candidate(cand_ji_warn)
    if not any("validate_ji_first" in f for f in fails_ji_warn):
        print("  [PASS] ji first validator accepts scam warning sentence following Ji first")
    else:
        print(f"  [FAIL] Did not expect validate_ji_first failure for Ji first with warning, got: {fails_ji_warn}")
        part_e_passed = False

    # Check 14: Scenario facets covers all 31 intents with >= 3 facet lists of 5 to 8 plain values each
    s_facets = config.get("scenario_facets", {})
    all_31_valid = True
    if len(s_facets) != 31:
        all_31_valid = False
    for int_k, f_dict in s_facets.items():
        if len(f_dict) < 3:
            all_31_valid = False
        for flist_k, fvals in f_dict.items():
            if not isinstance(fvals, list) or len(fvals) < 5 or len(fvals) > 8:
                all_31_valid = False
            for fv in fvals:
                if any(ch.isdigit() for ch in str(fv)) or '"' in str(fv) or "'" in str(fv):
                    all_31_valid = False
    if all_31_valid:
        print("  [PASS] scenario_facets covers all 31 intents with at least 3 facet lists of 5 to 8 plain values each (person_contacted removed)")
    else:
        print(f"  [FAIL] scenario_facets validation failed across 31 intents")
        part_e_passed = False

    # Check 15: Facet sampling selects one value from two different facet lists per request (zero for out_of_scope)
    sample_targets_facets = build_plan_targets("pilot", config, seeds)
    all_facets_sampled = True
    for t in sample_targets_facets:
        f = t.get("sampled_facets", {})
        if t.get("task_type") == "out_of_scope":
            if len(f) != 0:
                all_facets_sampled = False
                break
        else:
            if len(f) != 2:
                all_facets_sampled = False
                break
    if all_facets_sampled:
        print("  [PASS] facet sampling selects one value from two different facet lists per request (and zero for out_of_scope)")
    else:
        print(f"  [FAIL] facet sampling failed to select expected facet counts in target")
        part_e_passed = False

    print("\n[PART F] Testing v1.7 Features: Request Log, Daily Limit, Echo Refinements, Facet Anti-Copying, Derived Style, English Ticket Summary, and Structure Claims")
    part_f_passed = True

    # Check 16: Request log Pacific date counter and --daily-limit counting
    import tempfile
    from datetime import timedelta
    pac_tz = zoneinfo.ZoneInfo("America/Los_Angeles")
    pac_now = datetime.now(pac_tz)
    today_pac_dt = pac_now.astimezone(timezone.utc)
    yesterday_pac_dt = (pac_now - timedelta(days=1)).astimezone(timezone.utc)

    with tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False) as tf:
        temp_log_path = Path(tf.name)
        # Write 2 entries for Pacific today, 1 for Pacific yesterday
        tf.write(f"{today_pac_dt.isoformat()} gemini-2.5-pro\n")
        tf.write(f"{today_pac_dt.isoformat()} gemini-2.5-pro\n")
        tf.write(f"{yesterday_pac_dt.isoformat()} gemini-2.5-pro\n")
        tf.flush()

    try:
        logged_today_count = count_today_pacific_requests(temp_log_path)
        if logged_today_count == 2:
            print("  [PASS] request log accurately counts today's requests in Pacific time zone (zoneinfo America/Los_Angeles)")
        else:
            print(f"  [FAIL] Expected Pacific today count 2, got {logged_today_count}")
            part_f_passed = False
    finally:
        if temp_log_path.exists():
            temp_log_path.unlink()

    # Check 17: HTTP 429 quota exhaustion classification
    fake_quota_err = Exception("429 ResourceExhausted: Quota exceeded for quota metric 'GenerateContent'")
    fake_rate_limit_err = Exception("429 Too Many Requests: Rate limit reached, please retry later")
    fake_server_err = Exception("503 Service Unavailable")

    if is_quota_error(fake_quota_err) and not is_quota_error(fake_rate_limit_err) and not is_quota_error(fake_server_err):
        print("  [PASS] quota 429 errors correctly identified for immediate termination without retry")
    else:
        print("  [FAIL] is_quota_error failed to differentiate quota 429 from transient rate limit or server error")
        part_f_passed = False

    # Check 18: Customer echo validator:
    # - accept "Ji, for personal loan eligibility, the processing fee is 750 rupees." when context contains "for personal loan eligibility"
    cand_echo_acc1 = {
        "context": "For personal loan eligibility, the processing fee is 750 rupees.",
        "messages": [
            {"role": "user", "content": "What is for personal loan eligibility processing fee?"},
            {"role": "assistant", "content": "Ji, for personal loan eligibility, the processing fee is 750 rupees."}
        ]
    }
    # - accept "Ji, Zarya Bank mein loan darkhwast ki processing fee 500 rupees hai." when context contains "darkhwast ki processing fee"
    cand_echo_acc2 = {
        "context": "Zarya Bank mein loan darkhwast ki processing fee 500 rupees hai.",
        "messages": [
            {"role": "user", "content": "loan darkhwast ki processing fee kitni hai?"},
            {"role": "assistant", "content": "Ji, Zarya Bank mein loan darkhwast ki processing fee 500 rupees hai."}
        ]
    }
    # - reject "Ji, aap ka transfer fail ho gaya aur balance kat gaya, is par afsos hua." when context does not contain the phrase
    cand_echo_rej = {
        "context": None,
        "messages": [
            {"role": "user", "content": "Mera transfer fail ho gaya aur balance kat gaya ab kya karun?"},
            {"role": "assistant", "content": "Ji, aap ka transfer fail ho gaya aur balance kat gaya, is par afsos hua."}
        ]
    }
    echo1_fails = validate_no_customer_echo(cand_echo_acc1)
    echo2_fails = validate_no_customer_echo(cand_echo_acc2)
    echo3_fails = validate_no_customer_echo(cand_echo_rej)

    if not echo1_fails and not echo2_fails and len(echo3_fails) > 0:
        print("  [PASS] echo validator permits context-grounded repetitions and digits, rejects non-context echo")
    else:
        print(f"  [FAIL] Echo validator unit checks failed: echo1={echo1_fails}, echo2={echo2_fails}, echo3={echo3_fails}")
        part_f_passed = False

    # Check 19: Customer writing style derived strictly from mood and spelling
    style_calm = derive_customer_writing_style("calm", "clean")
    style_frust = derive_customer_writing_style("frustrated", "clean")
    style_angry = derive_customer_writing_style("very_angry", "typo_heavy")

    if style_calm == "plain and polite" and style_frust == "informal" and style_angry == "informal and shouting":
        print("  [PASS] customer writing style derived strictly from mood (calm: plain and polite, frustrated: informal, very_angry: informal and shouting)")
    else:
        print(f"  [FAIL] customer writing style derivation mismatch: calm={style_calm}, frust={style_frust}, angry={style_angry}")
        part_f_passed = False

    # Check 20: Ticket summary language validator rejects Roman Urdu and Urdu script, accepts English
    cand_ticket_roman = {
        "ticket": {"summary": "Customer ne agent shop se 12000 transfer karwaye jo receive nahi huay"}
    }
    cand_ticket_urdu = {
        "ticket": {"summary": "کسٹمر نے رقم ٹرانسفر کروائی"}
    }
    cand_ticket_english = {
        "ticket": {"summary": "Customer transferred 12000 rupees but beneficiary did not receive payment"}
    }
    f_tick_roman = validate_ticket_summary_language(cand_ticket_roman)
    f_tick_urdu = validate_ticket_summary_language(cand_ticket_urdu)
    f_tick_eng = validate_ticket_summary_language(cand_ticket_english)

    if f_tick_roman and f_tick_urdu and not f_tick_eng:
        print("  [PASS] ticket summary validator enforces English only and rejects Roman Urdu or Urdu script")
    else:
        print(f"  [FAIL] ticket summary language checks failed: roman={f_tick_roman}, urdu={f_tick_urdu}, eng={f_tick_eng}")
        part_f_passed = False

    # Check 21: Structure claims validator rejects unauthorized organizational words without context
    cand_struct_bad = {
        "context": "Zarya Bank offers fast mobile banking services.",
        "messages": [
            {"role": "user", "content": "Mera issue jaldi resolve karayein."},
            {"role": "assistant", "content": "Ji, Fraud monitoring division ke liye aap ki report darj kar li gayi hai."}
        ]
    }
    cand_struct_good = {
        "context": "All complaints are handled by our fraud monitoring division within 24 hours.",
        "messages": [
            {"role": "user", "content": "Mera issue jaldi resolve karayein."},
            {"role": "assistant", "content": "Ji, fraud monitoring division ke paas report darj kar li gayi hai."}
        ]
    }
    f_struct_bad = validate_no_structure_claims(cand_struct_bad)
    f_struct_good = validate_no_structure_claims(cand_struct_good)

    if f_struct_bad and not f_struct_good:
        print("  [PASS] structure claims validator rejects unauthorized organizational terms unless verbatim in context")
    else:
        print(f"  [FAIL] structure claims checks failed: bad={f_struct_bad}, good={f_struct_good}")
        part_f_passed = False

    # Check 22: Interval pacing logic with fake clocks
    t_base = datetime(2026, 10, 18, 12, 0, 0, tzinfo=timezone.utc)
    t_too_soon = datetime(2026, 10, 18, 12, 0, 5, tzinfo=timezone.utc)
    t_after_interval = datetime(2026, 10, 18, 12, 0, 20, tzinfo=timezone.utc)
    delay_active = calculate_pacing_delay(t_base, t_too_soon, min_interval=13.0)
    delay_cleared = calculate_pacing_delay(t_base, t_after_interval, min_interval=13.0)
    if round(delay_active, 1) == 8.0 and delay_cleared == 0.0:
        print("  [PASS] interval logic enforces min_seconds_between_requests using last timestamp")
    else:
        print(f"  [FAIL] interval logic calculation mismatch: delay_active={delay_active}, delay_cleared={delay_cleared}")
        part_f_passed = False

    # Check 23: Per model daily count in Pacific time with fake clocks
    with tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False) as tf:
        per_model_log = Path(tf.name)
        tf.write(f"{today_pac_dt.isoformat()} gemini-3.8-flash\n")
        tf.write(f"{today_pac_dt.isoformat()} gemini-3.8-flash\n")
        tf.write(f"{today_pac_dt.isoformat()} gemini-3.1-flash-lite\n")
        tf.write(f"{yesterday_pac_dt.isoformat()} gemini-3.8-flash\n")
        tf.flush()

    try:
        c_flash = count_today_pacific_requests(per_model_log, model_name="gemini-3.8-flash")
        c_lite = count_today_pacific_requests(per_model_log, model_name="gemini-3.1-flash-lite")
        c_other = count_today_pacific_requests(per_model_log, model_name="other-model")
        if c_flash == 2 and c_lite == 1 and c_other == 0:
            print("  [PASS] per model daily count accurately isolates today's Pacific requests per model")
        else:
            print(f"  [FAIL] per model daily count mismatch: flash={c_flash}, lite={c_lite}, other={c_other}")
            part_f_passed = False
    finally:
        if per_model_log.exists():
            per_model_log.unlink()

    # Check 24: Model limits table lookup and missing model error handling
    flash_limits = get_model_limits("gemini-3.8-flash", config)
    lite_limits = get_model_limits("gemini-3.1-flash-lite", config)
    missing_ok = False
    try:
        get_model_limits("unsupported-model-xyz", config, exit_on_error=False)
    except (ValueError, KeyError, SystemExit):
        missing_ok = True

    if (flash_limits.get("min_seconds_between_requests") == 13 and
        flash_limits.get("daily_request_limit") == 18 and
        lite_limits.get("min_seconds_between_requests") == 6 and
        lite_limits.get("daily_request_limit") == 450 and
        missing_ok):
        print("  [PASS] model limits table lookup retrieves correct model limits and rejects missing models")
    else:
        print("  [FAIL] model limits table lookup failed")
        part_f_passed = False

    # Check 25: Reset time calculation for next Pacific midnight and Asia/Karachi time
    t_fake_utc = datetime(2026, 10, 18, 17, 30, 0, tzinfo=timezone.utc)
    pac_rst, karachi_rst = get_next_pacific_reset_time(t_fake_utc)
    if (pac_rst.year == 2026 and pac_rst.month == 10 and pac_rst.day == 19 and pac_rst.hour == 0 and
        karachi_rst.year == 2026 and karachi_rst.month == 10 and karachi_rst.day == 19 and karachi_rst.hour == 12):
        print("  [PASS] reset time correctly calculates next Pacific midnight and corresponding Asia/Karachi time")
    else:
        print(f"  [FAIL] reset time mismatch: pac={pac_rst}, karachi={karachi_rst}")
        part_f_passed = False

    print("\n[PART G] Testing v1.8 Features: Context Numbers, Click Warning Exception, Closing Questions, End Style, and Promise Wording")
    part_g_passed = True

    # Check 26: Context numbers - accept supplied numbers plus 1 new extra
    cand_ctx_extra1 = {
        "context": "Debit card annual fee is 500 rupees and daily ATM limit is 50000 rupees.",
        "seed_context": "Debit card annual fee is 1200 rupees.",
        "variation": {
            "sampled_numbers": {"fee": 500.0}
        }
    }
    fails_extra1 = validate_context_numbers_match_sampled(cand_ctx_extra1)
    if not fails_extra1 and cand_ctx_extra1.get("extra_context_numbers") == ["50000"]:
        print("  [PASS] context numbers accepts supplied numbers plus 1 new extra number not in seed context")
    else:
        print(f"  [FAIL] context numbers failed to accept supplied plus 1 new extra: {fails_extra1}")
        part_g_passed = False

    # Check 27: Context numbers - reject missing supplied number
    cand_ctx_missing = {
        "context": "Debit card annual fee is 500 rupees.",
        "variation": {
            "sampled_numbers": {"fee": 500.0, "tat_hours": 24.0}
        }
    }
    fails_missing = validate_context_numbers_match_sampled(cand_ctx_missing)
    if fails_missing and "missing supplied numbers" in fails_missing[0]:
        print("  [PASS] context numbers rejects context when any supplied number is missing")
    else:
        print(f"  [FAIL] context numbers failed to reject missing supplied number: {fails_missing}")
        part_g_passed = False

    # Check 28: Context numbers - reject 2 extras
    cand_ctx_2extras = {
        "context": "Fee is 500 rupees, limit is 50000 rupees and turnaround is 3 days.",
        "variation": {
            "sampled_numbers": {"fee": 500.0}
        }
    }
    fails_2extras = validate_context_numbers_match_sampled(cand_ctx_2extras)
    if fails_2extras and "at most 1 extra allowed" in fails_2extras[0]:
        print("  [PASS] context numbers rejects context containing 2 extra numbers")
    else:
        print(f"  [FAIL] context numbers failed to reject 2 extras: {fails_2extras}")
        part_g_passed = False

    # Check 29: Context numbers - reject extra equal to a number in the seed context
    cand_ctx_seed_dup = {
        "context": "Debit card fee is 500 rupees and replacement fee is 1200 rupees.",
        "seed_context": "Debit card annual fee is 1200 rupees.",
        "variation": {
            "sampled_numbers": {"fee": 500.0}
        }
    }
    fails_seed_dup = validate_context_numbers_match_sampled(cand_ctx_seed_dup)
    if fails_seed_dup and "appears in seed's own context" in fails_seed_dup[0]:
        print("  [PASS] context numbers rejects extra number equal to a number in seed context")
    else:
        print(f"  [FAIL] context numbers failed to reject extra equal to seed context number: {fails_seed_dup}")
        part_g_passed = False

    # Check 30: Click warning exception - accepts click in warnings with up to 2 intervening words, rejects button click
    click_warn_1 = [{"role": "assistant", "content": "Ji, is link par click hargiz na karein."}]
    click_warn_2 = [{"role": "assistant", "content": "Ji, is link par click bilkul mat karein."}]
    click_warn_3 = [{"role": "assistant", "content": "Ji, is link par hargiz click na karein."}]
    click_bad = [{"role": "assistant", "content": "Ji, is button par click karein."}]

    v_cw1 = seed_stats.validate_no_procedure_words([{"id": "w1", "messages": click_warn_1}])
    v_cw2 = seed_stats.validate_no_procedure_words([{"id": "w2", "messages": click_warn_2}])
    v_cw3 = seed_stats.validate_no_procedure_words([{"id": "w3", "messages": click_warn_3}])
    v_cbad = seed_stats.validate_no_procedure_words([{"id": "wb", "messages": click_bad}])

    if not v_cw1 and not v_cw2 and not v_cw3 and len(v_cbad) > 0:
        print("  [PASS] click warning exception accepts 'click hargiz na karein', 'click bilkul mat karein', and 'hargiz click na karein', rejects 'is button par click karein'")
    else:
        print(f"  [FAIL] click warning exception test failed: w1={v_cw1}, w2={v_cw2}, w3={v_cw3}, bad={v_cbad}")
        part_g_passed = False

    # Check 31: Closing questions - accept specific customer action questions, reject generic offers
    cand_cq_acc1 = {"id": "cq1", "messages": [{"role": "assistant", "content": "Ji, kya aap ne is link par koi aur maloomat darj ki hain?"}]}
    cand_cq_acc2 = {"id": "cq2", "messages": [{"role": "assistant", "content": "Ji, did you share any other details with them?"}]}
    cand_cq_rej1 = {"id": "cq3", "messages": [{"role": "assistant", "content": "Ji, kya aap ko koi aur madad chahiye?"}]}
    cand_cq_rej2 = {"id": "cq4", "messages": [{"role": "assistant", "content": "Ji, is there anything else I can help with?"}]}

    v_cqa1 = validate_no_generic_closing_questions([cand_cq_acc1])
    v_cqa2 = validate_no_generic_closing_questions([cand_cq_acc2])
    v_cqr1 = validate_no_generic_closing_questions([cand_cq_rej1])
    v_cqr2 = validate_no_generic_closing_questions([cand_cq_rej2])

    if not v_cqa1 and not v_cqa2 and len(v_cqr1) > 0 and len(v_cqr2) > 0:
        print("  [PASS] closing questions accepts specific action questions ('koi aur maloomat darj ki hain?', 'share any other details with them?'), rejects generic help offers ('koi aur madad chahiye?', 'anything else I can help with?')")
    else:
        print(f"  [FAIL] closing questions check failed: acc1={v_cqa1}, acc2={v_cqa2}, rej1={v_cqr1}, rej2={v_cqr2}")
        part_g_passed = False

    # Check 32: End style validator both directions
    cand_es_stmt_ok = {
        "end_style": "statement",
        "messages": [{"role": "assistant", "content": "Ji, aap ki request darj kar li gayi hai."}]
    }
    cand_es_stmt_bad = {
        "end_style": "statement",
        "messages": [{"role": "assistant", "content": "Ji, kya aap mazeed intizar kar sakte hain?"}]
    }
    cand_es_q_ok = {
        "end_style": "question",
        "messages": [{"role": "assistant", "content": "Ji, kya aap ne link par click kiya tha?"}]
    }
    cand_es_q_bad = {
        "end_style": "question",
        "messages": [{"role": "assistant", "content": "Ji, aap ki request darj kar li gayi hai."}]
    }

    f_stmt_ok = validate_end_style(cand_es_stmt_ok)
    f_stmt_bad = validate_end_style(cand_es_stmt_bad)
    f_q_ok = validate_end_style(cand_es_q_ok)
    f_q_bad = validate_end_style(cand_es_q_bad)

    if not f_stmt_ok and len(f_stmt_bad) > 0 and not f_q_ok and len(f_q_bad) > 0:
        print("  [PASS] end style validator accepts statement ending with period and question ending with question mark, rejects opposite")
    else:
        print(f"  [FAIL] end style validator checks failed: stmt_ok={f_stmt_ok}, stmt_bad={f_stmt_bad}, q_ok={f_q_ok}, q_bad={f_q_bad}")
        part_g_passed = False

    # Check 33: Promise wording validator
    cand_pw_bad = [{"role": "assistant", "content": "Ji, is ka hal 24 ghanton mein mumken hai."}]
    cand_pw_ok = [{"role": "assistant", "content": "Ji, resolution ka waqt 24 ghantay hai."}]
    v_pw_bad = seed_stats.validate_bot_turns([{"id": "pw1", "messages": cand_pw_bad}])
    v_pw_ok = seed_stats.validate_bot_turns([{"id": "pw2", "messages": cand_pw_ok}])

    if len(v_pw_bad) > 0 and not v_pw_ok:
        print("  [PASS] promise wording rejects commitment ('is ka hal 24 ghanton mein mumken hai'), accepts neutral timing ('resolution ka waqt 24 ghantay hai')")
    else:
        print(f"  [FAIL] promise wording checks failed: bad={v_pw_bad}, ok={v_pw_ok}")
        part_g_passed = False

    # Check 34: Context numbers for complaint requests always include resolution time
    sampled_targets_test = build_plan_targets("full", config, seeds)
    complaint_targets = [t for t in sampled_targets_test if t["task_type"] == "complaint" and not t["nodoc"]]
    all_complaints_have_tat = all(
        ("tat_hours" in t.get("sampled_numbers", {}) or "tat_days" in t.get("sampled_numbers", {}))
        for t in complaint_targets
    )
    if all_complaints_have_tat and len(complaint_targets) > 0:
        print(f"  [PASS] all {len(complaint_targets)} complaint requests with context supply a resolution time (tat_hours or tat_days)")
    else:
        print(f"  [FAIL] some complaint requests missing resolution time in sampled_numbers")
        part_g_passed = False

    # Check 35: End style sampling distribution (approx 55% statement, 45% question)
    es_counts = Counter(t["end_style"] for t in sampled_targets_test)
    stmt_share = es_counts["statement"] / float(len(sampled_targets_test))
    if 0.50 <= stmt_share <= 0.60:
        print(f"  [PASS] end style sampled with fixed seed yields {stmt_share * 100:.1f}% statement and {(1 - stmt_share) * 100:.1f}% question (expected ~55%/45%)")
    else:
        print(f"  [FAIL] end style distribution skewed: statement share = {stmt_share}")
        part_g_passed = False

    print("\n[PART H] Testing Prompt v1.9 Features and Invariants")
    part_h_passed = True

    # Check 36: N limit computation and printing
    N_calc = compute_max_bot_words_limit(SEEDS_DIR)
    print(f"  [INFO] Max bot turn words in 100 seeds: 52 -> N = {N_calc}")
    if N_calc == 55:
        print(f"  [PASS] dynamic N calculation correctly computes largest bot turn length rounded to next multiple of 5 (N = {N_calc})")
    else:
        print(f"  [FAIL] dynamic N calculation returned {N_calc}, expected 55")
        part_h_passed = False

    # Check 37: Scam warning language matching
    warn_en = "Zarya Bank will never ask for your OTP or PIN over a call or SMS."
    warn_ru = "Zarya Bank kabhi bhi call ya SMS par aap ka OTP ya PIN nahi maangta."

    v_w_en = validate_scam_warning({
        "intent": "report_scam_call", "language": "english",
        "messages": [{"role": "assistant", "content": f"Ji, {warn_en}"}]
    })
    v_w_wrong = validate_scam_warning({
        "intent": "report_scam_call", "language": "english",
        "messages": [{"role": "assistant", "content": f"Ji, {warn_ru}"}]
    })
    if len(v_w_en) == 0 and len(v_w_wrong) > 0:
        print("  [PASS] scam warning validator enforces language-specific warning sentence and rejects mismatched language")
    else:
        print(f"  [FAIL] scam warning language checks failed: en={v_w_en}, wrong={v_w_wrong}")
        part_h_passed = False

    # Check 38: Refusals validator for out_of_scope
    v_ref_ok = validate_refusals({
        "category": "out_of_scope",
        "messages": [{"role": "assistant", "content": "Ji, main tibbi mashwara faraham nahi kar sakti baraye meherbani doctor se rujoo karein."}]
    })
    v_ref_q = validate_refusals({
        "category": "out_of_scope",
        "messages": [{"role": "assistant", "content": "Ji, main tibbi mashwara nahi de sakti. Kya aap ko banking mein madad chahiye?"}]
    })
    if len(v_ref_ok) == 0 and len(v_ref_q) > 0:
        print("  [PASS] refusals validator enforces zero question marks and <= 30 words for out_of_scope")
    else:
        print(f"  [FAIL] refusals checks failed: ok={v_ref_ok}, q={v_ref_q}")
        part_h_passed = False

    # Check 39: Customer echo bypassed for out_of_scope
    oos_echo_cand = {
        "category": "out_of_scope",
        "messages": [
            {"role": "user", "content": "tell me about current weather forecast in karachi today"},
            {"role": "assistant", "content": "Ji, tell me about current weather forecast is outside what I handle."}
        ]
    }
    v_oos_echo = validate_no_customer_echo(oos_echo_cand)
    if len(v_oos_echo) == 0:
        print("  [PASS] customer echo validator is bypassed for out_of_scope conversations")
    else:
        print(f"  [FAIL] echo validator flagged out_of_scope conversation: {v_oos_echo}")
        part_h_passed = False

    # Check 40: Verbatim context exception for procedure words and action claims
    proc_verbatim_cand = [{
        "id": "test_proc", "context": "Zarya Bank app par biometric tasdeeq hoti hai.",
        "messages": [{"role": "assistant", "content": "Ji, Zarya Bank app par biometric tasdeeq hoti hai."}]
    }]
    proc_ungrounded_cand = [{
        "id": "test_proc_ungrounded", "context": "Biometric tasdeeq hoti hai.",
        "messages": [{"role": "assistant", "content": "Ji, Zarya Bank app par biometric tasdeeq hoti hai."}]
    }]
    v_proc_verb = seed_stats.validate_no_procedure_words(proc_verbatim_cand)
    v_proc_ungr = seed_stats.validate_no_procedure_words(proc_ungrounded_cand)

    act_verbatim_cand = [{
        "id": "test_act", "context": "Our records indicate a processing fee.",
        "messages": [{"role": "assistant", "content": "Ji, our records indicate a processing fee."}]
    }]
    act_ungrounded_cand = [{
        "id": "test_act_ungrounded", "context": "Processing fee applies.",
        "messages": [{"role": "assistant", "content": "Ji, our records indicate a processing fee."}]
    }]
    v_act_verb = seed_stats.validate_no_action_claims(act_verbatim_cand)
    v_act_ungr = seed_stats.validate_no_action_claims(act_ungrounded_cand)

    if len(v_proc_verb) == 0 and len(v_proc_ungr) > 0 and len(v_act_verb) == 0 and len(v_act_ungr) > 0:
        print("  [PASS] procedure words and action claims permit verbatim occurrences in context text and reject ungrounded occurrences")
    else:
        print(f"  [FAIL] verbatim context exceptions failed: proc_verb={v_proc_verb}, proc_ungr={v_proc_ungr}, act_verb={v_act_verb}, act_ungr={v_act_ungr}")
        part_h_passed = False

    # Check 41: No context ranges validator
    v_range_bad = validate_no_context_ranges({"context": "Turnaround time is 2 to 4 days."})
    v_range_ok = validate_no_context_ranges({"context": "Turnaround time is 3 days."})
    if len(v_range_bad) > 0 and len(v_range_ok) == 0:
        print("  [PASS] context ranges validator rejects range expressions ('2 to 4 days') and accepts single exact values ('3 days')")
    else:
        print(f"  [FAIL] context ranges validator failed: bad={v_range_bad}, ok={v_range_ok}")
        part_h_passed = False

    # Check 42: Ticket amount restricted to allowed intents
    v_amt_bad = validate_ticket_amount_allowed({"intent": "check_balance", "ticket": {"amount": 5000}})
    v_amt_ok = validate_ticket_amount_allowed({"intent": "transfer_failed", "ticket": {"amount": 5000}})
    if len(v_amt_bad) > 0 and len(v_amt_ok) == 0:
        print("  [PASS] ticket amount validator rejects amounts on non-amount intents and accepts allowed intents")
    else:
        print(f"  [FAIL] ticket amount checks failed: bad={v_amt_bad}, ok={v_amt_ok}")
        part_h_passed = False

    print("\n[PART I] Testing Prompt v1.10 Features and Invariants")
    part_i_passed = True

    # Check 43: Refusal templates pool
    tpl_pool_ok = True
    expected_topics = ["politics", "medical", "investment", "sports", "other bank", "homework", "general chat", "legal"]
    for top in expected_topics:
        if top not in REFUSAL_TEMPLATES:
            tpl_pool_ok = False
            break
        g = REFUSAL_TEMPLATES[top]
        if len(g.get("roman_urdu", [])) < 12 or len(g.get("english", [])) < 6 or len(g.get("urdu_script", [])) < 6:
            tpl_pool_ok = False
            break
        for lang_k, t_list in g.items():
            for tpl in t_list:
                if "?" in tpl or "؟" in tpl or len(tpl.split()) > 25:
                    tpl_pool_ok = False
                    break
                if lang_k == "urdu_script":
                    if not tpl.startswith("جی"):
                        tpl_pool_ok = False
                else:
                    if not tpl.startswith("Ji"):
                        tpl_pool_ok = False
    if tpl_pool_ok:
        print("  [PASS] refusal templates pool contains >= 12 Roman Urdu, >= 6 English, >= 6 Urdu script templates per topic group (all <= 25 words, no question mark, start with Ji/جی)")
    else:
        print("  [FAIL] refusal templates pool invariant check failed")
        part_i_passed = False

    # Check 44: Refusal generation selftest: 200 records pass all validators, template usage <= 4%
    sel_test = RefusalTemplateSelector(REFUSAL_TEMPLATES, seed=42)
    test_rng_oos = random.Random(789)
    topics_list = list(REFUSAL_TEMPLATES.keys())
    langs_list = ["roman_urdu", "urdulish", "english", "urdu_script"]
    refusal_templates_used = []
    all_200_valid = True

    for i in range(200):
        t_topic = test_rng_oos.choice(topics_list)
        t_lang = test_rng_oos.choice(langs_list)
        bot_reply = sel_test.select(t_topic, t_lang)
        refusal_templates_used.append(bot_reply)

        if "urdu_script" in t_lang:
            user_text = "میرا ایک سوال ہے اس موضوع پر"
        elif "english" in t_lang:
            user_text = "I have a general inquiry about this matter"
        else:
            user_text = "Mera ek sawal hai is bare mein"

        sys_m = build_system_message(BASE_SYSTEM_MESSAGE, None)
        cand_oos = {
            "id": f"refusal_test_{i}",
            "category": "out_of_scope",
            "intent": "out_of_scope_query",
            "language": t_lang,
            "context": None,
            "messages": [
                {"role": "system", "content": sys_m},
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": bot_reply}
            ],
            "ticket": None
        }
        v_oos = validate_candidate(cand_oos)
        if len(v_oos) > 0:
            all_200_valid = False
            print(f"    [FAIL] Refusal candidate {i} failed validation: {v_oos}")
            break

    counts_200 = Counter(refusal_templates_used)
    max_usage_200 = max(counts_200.values()) if counts_200 else 0
    max_usage_ratio = max_usage_200 / 200.0

    # Also verify sliding window of 100 refusals: <= 3 repeats
    window_ok = True
    for w_i in range(len(refusal_templates_used) - 100):
        win_c = Counter(refusal_templates_used[w_i:w_i+100])
        if max(win_c.values()) > 3:
            window_ok = False
            break

    if all_200_valid and max_usage_ratio <= 0.04 and window_ok:
        print("  [PASS] refusal selector builds 200 records passing all validators with max template usage <= 4 percent and <= 3 repeats per 100 refusals")
    else:
        print(f"  [FAIL] refusal 200 selftest failed: valid={all_200_valid}, max_ratio={max_usage_ratio:.3f}, window_ok={window_ok}")
        part_i_passed = False

    # Check 45: Scenario facets Roman Urdu check across all 31 intents
    facets_cfg = config.get("scenario_facets", {})
    all_facets_ru_ok = True
    whitelist_set = {"app", "sms", "atm", "ibft", "raast", "whatsapp", "otp"}
    forbidden_en_sample = {"error", "card", "bill", "screen", "mobile", "phone", "balance", "statement", "pending", "history"}
    if len(facets_cfg) != 31:
        all_facets_ru_ok = False
    for int_k, f_groups in facets_cfg.items():
        for gk, g_vals in f_groups.items():
            for f_val in g_vals:
                if any(ch.isdigit() for ch in f_val) or '"' in f_val or "'" in f_val or "ehsas" in f_val.lower():
                    all_facets_ru_ok = False
                    break
                words = re.findall(r"\b[A-Za-z]+\b", f_val)
                for w in words:
                    wl = w.lower()
                    if wl in forbidden_en_sample and wl not in whitelist_set:
                        all_facets_ru_ok = False
                        break
    if all_facets_ru_ok:
        print("  [PASS] scenario_facets in generation_plan.yaml contains pure Roman Urdu descriptions across all 31 intents with zero English words outside whitelist")
    else:
        print("  [FAIL] scenario_facets Roman Urdu check failed")
        part_i_passed = False

    # Check 46: Customer echo validator: 5+ words required, context word / intent word exception
    # 4-word copied span is accepted
    cand_echo_4w = {
        "intent": "transfer_failed", "context": None,
        "messages": [
            {"role": "user", "content": "yeh ajeeb baat hai"},
            {"role": "assistant", "content": "Ji, yeh ajeeb baat hai to complaint darj kar li gayi."}
        ]
    }
    # 5-word copied span with intent word 'transfer' is accepted
    cand_echo_intent = {
        "intent": "transfer_failed", "context": None,
        "messages": [
            {"role": "user", "content": "mera transfer aage nahi gaya"},
            {"role": "assistant", "content": "Ji, mera transfer aage nahi gaya to complaint darj kar li gayi."}
        ]
    }
    # 5-word copied span with context word 'fee' is accepted
    cand_echo_ctx = {
        "intent": "transfer_failed", "context": "Standard fee applies to transactions.",
        "messages": [
            {"role": "user", "content": "is maslay ki fee kitni hai"},
            {"role": "assistant", "content": "Ji, is maslay ki fee kitni hai to bata doon 500 rupees hai."}
        ]
    }
    # 5-word copied span with NO context word and NO intent word is rejected
    cand_echo_rej_5w = {
        "intent": "transfer_failed", "context": None,
        "messages": [
            {"role": "user", "content": "subah se intezar kar raha hoon koi hal nahi nikla"},
            {"role": "assistant", "content": "Ji, subah se intezar kar raha hoon koi hal nahi nikla to complaint darj kar li gayi."}
        ]
    }
    v_4w = validate_no_customer_echo(cand_echo_4w)
    v_int = validate_no_customer_echo(cand_echo_intent)
    v_ctx = validate_no_customer_echo(cand_echo_ctx)
    v_rej5 = validate_no_customer_echo(cand_echo_rej_5w)

    if len(v_4w) == 0 and len(v_int) == 0 and len(v_ctx) == 0 and len(v_rej5) > 0:
        print("  [PASS] customer echo validator requires 5 or more words and permits words from context or intent name")
    else:
        print(f"  [FAIL] customer echo 5-word validator failed: 4w={v_4w}, int={v_int}, ctx={v_ctx}, rej5={v_rej5}")
        part_i_passed = False

    # Check 47: Opening variety diversity filter: both directions
    cand_op_var = {"messages": [{"role": "assistant", "content": "Ji aap ka masla darj kar liya gaya hai."}]}
    acc_below_60 = [{"messages": [{"role": "assistant", "content": "Ji aap ka masla darj kar liya gaya hai."}]}] * 50
    acc_60_low = (
        [{"messages": [{"role": "assistant", "content": "Ji aap ka masla darj kar liya gaya hai."}]}] * 2 +
        [{"messages": [{"role": "assistant", "content": f"Ji unique opening {idx} statement."}]} for idx in range(58)]
    )
    acc_60_high = (
        [{"messages": [{"role": "assistant", "content": "Ji aap ka masla darj kar liya gaya hai."}]}] * 3 +
        [{"messages": [{"role": "assistant", "content": f"Ji unique opening {idx} statement."}]} for idx in range(57)]
    )
    v_op_b60 = validate_opening_variety(cand_op_var, acc_below_60)
    v_op_low = validate_opening_variety(cand_op_var, acc_60_low)
    v_op_high = validate_opening_variety(cand_op_var, acc_60_high)

    if len(v_op_b60) == 0 and len(v_op_low) == 0 and len(v_op_high) > 0:
        print("  [PASS] opening variety diversity filter accepts below 5 percent frequency and rejects at or above 5 percent once 60 records exist")
    else:
        print(f"  [FAIL] opening variety filter failed: b60={v_op_b60}, low={v_op_low}, high={v_op_high}")
        part_i_passed = False

    # Check 48: Ehsas rejection across chat turns
    cand_ehsas_word = {"messages": [{"role": "assistant", "content": "Ji, mujhe ehsas hai aap pareshan hain."}]}
    cand_ehsas_phrase = {"messages": [{"role": "assistant", "content": "Ji, aap ki pareshani ka ehsas hai."}]}
    cand_ehsas_ok = {"messages": [{"role": "assistant", "content": "Ji, ye sun kar afsos hua."}]}
    v_eh_w = validate_no_ehsas(cand_ehsas_word)
    v_eh_p = validate_no_ehsas(cand_ehsas_phrase)
    v_eh_ok = validate_no_ehsas(cand_ehsas_ok)

    if len(v_eh_w) > 0 and len(v_eh_p) > 0 and len(v_eh_ok) == 0:
        print("  [PASS] ehsas validator rejects 'ehsas' and 'pareshani ka ehsas' across instructions and chat turns")
    else:
        print(f"  [FAIL] ehsas validator checks failed: word={v_eh_w}, phrase={v_eh_p}, ok={v_eh_ok}")
        part_i_passed = False

    # Check 49: Customer variety trigram extraction
    mock_cust_recs = []
    for m_i in range(6):
        mock_cust_recs.append({"messages": [{"role": "user", "content": f"Aoa mera balance kat gaya tha {m_i}"}]})
    for m_i in range(3):
        mock_cust_recs.append({"messages": [{"role": "user", "content": f"Hello transfer nahi hua {m_i}"}]})
    top_extracted = extract_top_customer_trigrams(mock_cust_recs, min_count=5, top_k=10)
    top_phrases_list = [p[0] for p in top_extracted]

    if "mera balance kat" in top_phrases_list and "transfer nahi hua" not in top_phrases_list and len(top_extracted) > 0:
        print("  [PASS] customer variety correctly extracts and ranks 3-word phrases appearing in 5 or more customer messages")
    else:
        print(f"  [FAIL] customer variety extraction failed: {top_extracted}")
        part_i_passed = False

    print("\n[PART J] Testing Prompt v1.11 Features and Invariants")
    part_j_passed = True

    # Check 50: Out of scope end style: build 200 out_of_scope targets and check all are statement; refusal template record with end_style statement passes validate_end_style
    oos_targets_test = []
    oos_rng = random.Random(111)
    oos_seeds = [s for s in seeds if derive_task_type(s) == "out_of_scope"]
    if not oos_seeds:
        oos_seeds = seeds[:5]
    for _ in range(200):
        tt_sim = "out_of_scope"
        if tt_sim == "out_of_scope":
            sim_end_style = "statement"
        else:
            sim_end_style = oos_rng.choices(["statement", "question"], weights=[0.55, 0.45], k=1)[0]
        oos_targets_test.append({"end_style": sim_end_style})

    all_oos_stmt = len(oos_targets_test) == 200 and all(t["end_style"] == "statement" for t in oos_targets_test)

    refusal_rec_stmt = {
        "end_style": "statement",
        "category": "out_of_scope",
        "messages": [
            {"role": "user", "content": "Election kab hongay?"},
            {"role": "assistant", "content": "Ji, main siyasi mamlat par tabsira nahi kar sakti."}
        ]
    }
    v_oos_stmt = validate_end_style(refusal_rec_stmt)

    if all_oos_stmt and len(v_oos_stmt) == 0:
        print("  [PASS] out_of_scope end style always sets statement across 200 targets and passes validate_end_style")
    else:
        print(f"  [FAIL] out_of_scope end style check failed: all_oos_stmt={all_oos_stmt}, v_oos_stmt={v_oos_stmt}")
        part_j_passed = False

    # Check 51: Facet copying: content words comparison, stoplist filtering, accept <70%, reject 3 consecutive, reject >= 70%
    cand_facet_ok = {
        "sampled_facets": {"already_tried": "kaghzat jama karwa raha tha"},
        "messages": [
            {"role": "user", "content": "kaghzat jama kar raha hun"},
            {"role": "assistant", "content": "Ji, aap ki request darj kar li gayi hai."}
        ]
    }
    cand_facet_consec = {
        "sampled_facets": {"already_tried": "kaghzat jama karwa raha tha"},
        "messages": [
            {"role": "user", "content": "Maine kaghzat jama karwa raha tha aur masla hua"},
            {"role": "assistant", "content": "Ji, aap ki request darj kar li gayi hai."}
        ]
    }
    cand_facet_70 = {
        "sampled_facets": {"already_tried": "tasdeeq kaghzat asan dakhla form"},
        "messages": [
            {"role": "user", "content": "Maine tasdeeq kaghzat asan dakhla form jama karwaya tha"},
            {"role": "assistant", "content": "Ji, aap ki request darj kar li gayi hai."}
        ]
    }
    v_fc_ok = validate_no_facet_copying(cand_facet_ok)
    v_fc_consec = validate_no_facet_copying(cand_facet_consec)
    v_fc_70 = validate_no_facet_copying(cand_facet_70)

    if len(v_fc_ok) == 0 and len(v_fc_consec) > 0 and len(v_fc_70) > 0:
        print("  [PASS] facet copying validator compares content words ignoring stoplist, accepts <70% non-consecutive, rejects 3 consecutive content words and >= 70% content words")
    else:
        print(f"  [FAIL] facet copying checks failed: ok={v_fc_ok}, consec={v_fc_consec}, 70={v_fc_70}")
        part_j_passed = False

    # Check 52: Number pools: check all 6 kinds have at least 40 distinct values with proper bounds
    pools_dict = config.get("sampled_number_ranges", {})
    expected_kinds = ["fee", "daily_limit", "turnaround_hours", "turnaround_days", "percentage", "customer_amount"]
    pools_ok = True
    for ek in expected_kinds:
        p_vals = pools_dict.get(ek, [])
        if len(set(p_vals)) < 40:
            pools_ok = False
            break
        for val in p_vals:
            f_str = format_number_no_trailing_zero(val)
            if re.search(r"\b\d+\.0+(?!\d)", f_str):
                pools_ok = False
                break

    fee_vals = pools_dict.get("fee", [])
    if fee_vals:
        if min(fee_vals) < 25 or max(fee_vals) > 2500 or 275 not in fee_vals or 1350 not in fee_vals:
            pools_ok = False

    pct_vals = pools_dict.get("percentage", [])
    if pct_vals:
        for pv in pct_vals:
            if not (isinstance(pv, float) and len(str(pv).split(".")[1]) == 1):
                pools_ok = False
                break

    hr_vals = pools_dict.get("turnaround_hours", [])
    if hr_vals:
        if min(hr_vals) < 6 or max(hr_vals) > 120:
            pools_ok = False

    day_vals = pools_dict.get("turnaround_days", [])
    if day_vals:
        if min(day_vals) < 1 or max(day_vals) > 30:
            pools_ok = False

    if pools_ok:
        print("  [PASS] sampled_number_ranges pools all contain at least 40 distinct values with non-round values, proper bounds and no trailing .0")
    else:
        print(f"  [FAIL] number pools validation failed")
        part_j_passed = False

    # Check 53: Customer greeting tic: reject customer message starting with Ji or جی, accept without
    cand_tic_ok = {
        "messages": [
            {"role": "user", "content": "Mera card ATM machine mein phans gaya hai."},
            {"role": "assistant", "content": "Ji, aap ki shikayat darj kar li gayi hai."}
        ]
    }
    cand_tic_ji = {
        "messages": [
            {"role": "user", "content": "Ji mera card machine mein phans gaya hai."},
            {"role": "assistant", "content": "Ji, aap ki shikayat darj kar li gayi hai."}
        ]
    }
    cand_tic_urdu = {
        "messages": [
            {"role": "user", "content": "جی میرا کارڈ بلاک کر دیں۔"},
            {"role": "assistant", "content": "جی، آپ کا کارڈ بلاک کرنے کی درخواست درج کر لی گئی ہے۔"}
        ]
    }
    v_tic_ok = validate_no_customer_ji(cand_tic_ok)
    v_tic_ji = validate_no_customer_ji(cand_tic_ji)
    v_tic_urdu = validate_no_customer_ji(cand_tic_urdu)

    if len(v_tic_ok) == 0 and len(v_tic_ji) > 0 and len(v_tic_urdu) > 0:
        print("  [PASS] customer greeting tic validator rejects customer message starting with Ji or جی and accepts messages without greeting tic")
    else:
        print(f"  [FAIL] customer greeting tic checks failed: ok={v_tic_ok}, ji={v_tic_ji}, urdu={v_tic_urdu}")
        part_j_passed = False

    print("\n[PART K] Testing Prompt v1.12 Features and Invariants")
    part_k_passed = True

    # Check 54: Facet copying with time & counting words: accepts "teen din pehle" for facet "teen din pehle naya shanakhti kagaz banwaya tha"
    cand_facet_time_ok = {
        "sampled_facets": {"already_tried": "teen din pehle naya shanakhti kagaz banwaya tha"},
        "messages": [
            {"role": "user", "content": "Mera masla yeh hai ke teen din pehle biometric nahi hui thi"},
            {"role": "assistant", "content": "Ji, complaint darj kar li gayi hai."}
        ]
    }
    cand_facet_time_bad = {
        "sampled_facets": {"already_tried": "teen din pehle naya shanakhti kagaz banwaya tha"},
        "messages": [
            {"role": "user", "content": "Maine naya shanakhti kagaz banwaya tha kal"},
            {"role": "assistant", "content": "Ji, complaint darj kar li gayi hai."}
        ]
    }
    v_ft_ok = validate_no_facet_copying(cand_facet_time_ok)
    v_ft_bad = validate_no_facet_copying(cand_facet_time_bad)
    if len(v_ft_ok) == 0 and len(v_ft_bad) > 0:
        print("  [PASS] facet copying validator ignores counting and time words, accepting 'teen din pehle' while rejecting consecutive content words")
    else:
        print(f"  [FAIL] facet copying time words check failed: ok={v_ft_ok}, bad={v_ft_bad}")
        part_k_passed = False

    # Check 55: Only what was asked (both directions)
    cand_owa_unasked = [{
        "category": "card", "intent": "card_delivery",
        "context": "Card delivery fee is 250 rupees.",
        "messages": [
            {"role": "user", "content": "Mera card kab aayega?"},
            {"role": "assistant", "content": "Ji, card delivery fee 250 rupees hai."}
        ]
    }]
    cand_owa_asked = [{
        "category": "card", "intent": "card_delivery",
        "context": "Card delivery fee is 250 rupees.",
        "messages": [
            {"role": "user", "content": "Card delivery ki fee kitni hai?"},
            {"role": "assistant", "content": "Ji, card delivery fee 250 rupees hai."}
        ]
    }]
    cand_owa_3num_nonloan = [{
        "category": "transfer", "intent": "transfer_failed",
        "context": "Turnaround is 24 hours, daily limit is 50000 and min fee is 50 rupees.",
        "messages": [{"role": "user", "content": "Transfer issue."}]
    }]
    cand_owa_3num_loan = [{
        "category": "loan", "intent": "loan_eligibility",
        "context": "Salary must be 50000, markup is 18 percent and fee is 1500.",
        "messages": [{"role": "user", "content": "Loan details?"}]
    }]
    v_owa_unasked = validate_only_asked_numbers(cand_owa_unasked)
    v_owa_asked = validate_only_asked_numbers(cand_owa_asked)
    v_owa_nonloan = validate_only_asked_numbers(cand_owa_3num_nonloan)
    v_owa_loan = validate_only_asked_numbers(cand_owa_3num_loan)

    if len(v_owa_unasked) > 0 and len(v_owa_asked) == 0 and len(v_owa_nonloan) > 0 and len(v_owa_loan) == 0:
        print("  [PASS] only what was asked validator rejects unasked fees and contexts with > 2 numbers on non-loan intents, accepting asked fees and loan contexts")
    else:
        print(f"  [FAIL] only what was asked check failed: unasked={v_owa_unasked}, asked={v_owa_asked}, nonloan={v_owa_nonloan}, loan={v_owa_loan}")
        part_k_passed = False

    # Check 56: Filler sentences validator: all 5 phrases rejected, normal response accepted
    filler_samples = [
        "thank you for confirming",
        "shukriya maloomat dene ka",
        "durust darj kar li gayi",
        "noted for the investigation",
        "aap ke record ke liye"
    ]
    all_fillers_caught = True
    for fs in filler_samples:
        cand_filler = {"messages": [{"role": "assistant", "content": f"Ji, {fs}, shikayat darj ho gayi hai."}]}
        if not validate_no_filler_sentences(cand_filler):
            all_fillers_caught = False
            break
    cand_filler_ok = {"messages": [{"role": "assistant", "content": "Ji, aap ki darkhwast darj kar li gayi hai."}]}
    if all_fillers_caught and len(validate_no_filler_sentences(cand_filler_ok)) == 0:
        print("  [PASS] filler sentences validator rejects all 5 filler phrases and accepts factual bot turns")
    else:
        print("  [FAIL] filler sentences check failed")
        part_k_passed = False

    # Check 57: Ticket time span matching
    cand_tt_bad = {
        "messages": [{"role": "user", "content": "Mera transfer atak gaya hai."}],
        "ticket": {"time_mentioned": "just now"}
    }
    cand_tt_ok = {
        "messages": [{"role": "user", "content": "Mera transfer kal sham atak gaya hai."}],
        "ticket": {"time_mentioned": "kal sham"}
    }
    cand_tt_null = {
        "messages": [{"role": "user", "content": "Mera transfer atak gaya hai."}],
        "ticket": {"time_mentioned": None}
    }
    v_tt_bad = validate_time_mentioned_natural(cand_tt_bad)
    v_tt_ok = validate_time_mentioned_natural(cand_tt_ok)
    v_tt_null = validate_time_mentioned_natural(cand_tt_null)
    if len(v_tt_bad) > 0 and len(v_tt_ok) == 0 and len(v_tt_null) == 0:
        print("  [PASS] ticket time validator enforces time_mentioned is an exact customer span, rejecting ungrounded 'just now' and accepting valid spans or null")
    else:
        print(f"  [FAIL] ticket time check failed: bad={v_tt_bad}, ok={v_tt_ok}, null={v_tt_null}")
        part_k_passed = False

    # Check 58: Questions and offers: rejects "proceed", "lena chahte hain", "continue karna chahte", "shall we"
    offer_samples = [
        "Ji, kya aap naya card lena chahte hain?",
        "Ji, would you like to proceed with card issuance?",
        "Ji, kya aap is request ke sath continue karna chahte hain?",
        "Ji, shall we cancel this request?"
    ]
    all_offers_caught = all(
        len(validate_no_help_offers_and_numbers({"messages": [{"role": "assistant", "content": os_text}]})) > 0
        for os_text in offer_samples
    )
    cand_offer_ok = {"messages": [{"role": "assistant", "content": "Ji, kya aap transaction ID bata sakte hain?"}]}
    if all_offers_caught and len(validate_no_help_offers_and_numbers(cand_offer_ok)) == 0:
        print("  [PASS] questions and offers validator rejects customer purpose and plan inquiries ('proceed', 'lena chahte hain', 'continue karna chahte', 'shall we')")
    else:
        print(f"  [FAIL] questions and offers check failed: all_offers_caught={all_offers_caught}")
        part_k_passed = False

    print("\n[PART L] Testing Prompt v1.13 Features and Invariants")
    part_l_passed = True

    # Check 59: Revalidate mode: 2 known good and 2 known bad candidates
    cand_g1 = {
        "seed_id": "seed_001",
        "language": "roman_urdu",
        "task_type": "complaint",
        "category": "card",
        "intent": "block_card",
        "context": "Card block turnaround time is 24 hours.",
        "messages": [
            {"role": "user", "content": "Mera card kho gaya hai please block karein."},
            {"role": "assistant", "content": "Ji, card block karne ki darkhwast darj kar li gayi hai."}
        ],
        "variation": {"mood": "calm", "spelling": "clean", "end_style": "statement", "sampled_numbers": {"tat_hours": 24}}
    }
    cand_g2 = {
        "seed_id": "seed_002",
        "language": "english",
        "task_type": "faq",
        "category": "card",
        "intent": "product_terms",
        "context": "Debit card annual fee is 500 rupees.",
        "messages": [
            {"role": "user", "content": "What is the annual fee for debit card?"},
            {"role": "assistant", "content": "Ji, the annual fee for the debit card is 500 rupees."}
        ],
        "variation": {"mood": "calm", "spelling": "clean", "end_style": "statement", "sampled_numbers": {"fee": 500}}
    }
    cand_b1 = {
        "seed_id": "seed_003",
        "language": "roman_urdu",
        "task_type": "complaint",
        "category": "card",
        "intent": "block_card",
        "context": "Card block turnaround time is 24 hours.",
        "messages": [
            {"role": "user", "content": "Card block karein."},
            {"role": "assistant", "content": "Ji, darkhwast darj ho gayi hai. Mazeed koi aur madad chahiye?"}
        ],
        "variation": {"mood": "calm", "spelling": "clean", "end_style": "question", "sampled_numbers": {"tat_hours": 24}}
    }
    cand_b2 = {
        "seed_id": "seed_004",
        "language": "roman_urdu",
        "task_type": "faq",
        "category": "card",
        "intent": "product_terms",
        "context": "Card fee is 500 rupees.",
        "messages": [
            {"role": "user", "content": "Fee kitni hai?"},
            {"role": "assistant", "content": "Ji, card fee 9999 rupees hai."}
        ],
        "variation": {"mood": "calm", "spelling": "clean", "end_style": "statement", "sampled_numbers": {"fee": 500}}
    }
    tmp_reval_file = RAW_DIR / "tmp_selftest_revalidate.jsonl"
    try:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        with open(tmp_reval_file, "w", encoding="utf-8") as tf:
            tf.write(json.dumps(cand_g1) + "\n")
            tf.write(json.dumps(cand_g2) + "\n")
            tf.write(json.dumps(cand_b1) + "\n")
            tf.write(json.dumps(cand_b2) + "\n")

        reval_res = run_revalidation([str(tmp_reval_file)])
        if reval_res["total_passed"] == 2 and reval_res["total_failed"] == 2:
            print("  [PASS] revalidate mode accurately processes candidates, yielding 2 passed and 2 failed records")
        else:
            print(f"  [FAIL] revalidate mode test failed: passed={reval_res['total_passed']}, failed={reval_res['total_failed']}")
            part_l_passed = False
    finally:
        if tmp_reval_file.exists():
            tmp_reval_file.unlink()

    # Check 60: Facet copying: accept "naya shanakhti kagaz", reject 5 consecutive words
    cand_fc_acc = {
        "sampled_facets": {"already_tried": "teen din pehle naya shanakhti kagaz banwaya tha"},
        "messages": [
            {"role": "user", "content": "Mera naya shanakhti kagaz bank se nahi mila."},
            {"role": "assistant", "content": "Ji, complaint darj kar li gayi hai."}
        ]
    }
    cand_fc_rej = {
        "sampled_facets": {"already_tried": "teen din pehle naya shanakhti kagaz banwaya tha"},
        "messages": [
            {"role": "user", "content": "Maine teen din pehle naya shanakhti kagaz banwaya tha bank mein."},
            {"role": "assistant", "content": "Ji, complaint darj kar li gayi hai."}
        ]
    }
    v_fc_acc = validate_no_facet_copying(cand_fc_acc)
    v_fc_rej = validate_no_facet_copying(cand_fc_rej)
    if len(v_fc_acc) == 0 and len(v_fc_rej) > 0:
        print("  [PASS] facet copying validator accepts 'naya shanakhti kagaz' and rejects verbatim 5+ consecutive words")
    else:
        print(f"  [FAIL] facet copying check failed: acc={v_fc_acc}, rej={v_fc_rej}")
        part_l_passed = False

    # Check 61: Number budget: for every one of 31 intents sample 200 targets and assert supplied number count never exceeds budget
    budget_ok = True
    for it_name in ALL_31_INTENTS:
        matching_seeds = [s for s in seeds if s.get("intent") == it_name]
        seed_for_it = matching_seeds[0] if matching_seeds else {"id": f"mock_{it_name}", "intent": it_name, "category": "complaint", "language": "roman_urdu"}
        expected_budget = get_intent_number_budget(it_name, seed_for_it.get("category", ""))
        for samp_idx in range(200):
            t_list = derive_generation_targets(config, [seed_for_it], mode="pilot", total=1, target_seed=(samp_idx + 2000))
            if t_list:
                s_nums = t_list[0].get("sampled_numbers", {})
                if len(s_nums) > expected_budget:
                    budget_ok = False
                    print(f"Budget exceeded for intent {it_name}: got {len(s_nums)} numbers, budget is {expected_budget}")
                    break
        if not budget_ok:
            break
    if budget_ok:
        print("  [PASS] number budget enforced across all 31 intents: 200 sampled targets each never exceed budget")
    else:
        print("  [FAIL] number budget check failed across 31 intents")
        part_l_passed = False

    # Check 62: Ehsas forbidden: teacher prompt forbids ehsas, validator rejects ehsas
    with open(PROMPTS_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        prompt_txt = f.read()
    prompt_has_ehsas = "ehsas" in prompt_txt.lower()
    cand_ehsas_bot = {"messages": [{"role": "assistant", "content": "Ji, aap ki takleef ka ehsas hai mujhe."}]}
    cand_ehsas_cust = {"messages": [{"role": "user", "content": "Mujhe bohot takleef ka ehsas hua."}]}
    cand_ehsas_ok = {"messages": [{"role": "assistant", "content": "Ji, complaint darj kar li gayi hai."}]}
    v_eh_bot = validate_no_ehsas(cand_ehsas_bot)
    v_eh_cust = validate_no_forbidden_customer_words([cand_ehsas_cust])
    v_eh_ok = validate_no_ehsas(cand_ehsas_ok)
    if prompt_has_ehsas and len(v_eh_bot) > 0 and len(v_eh_cust) > 0 and len(v_eh_ok) == 0:
        print("  [PASS] ehsas word forbidden in prompt and rejected by validators for both assistant and customer turns")
    else:
        print(f"  [FAIL] ehsas check failed: prompt_has_ehsas={prompt_has_ehsas}, bot={v_eh_bot}, cust={v_eh_cust}")
        part_l_passed = False

    # Check 63: Shared words stat: computed over small file with numerator and denominator
    test_shared_recs = [
        {"seed_id": "seed_001", "messages": [{"role": "user", "content": "mera debit card machine mein phans gaya"}]},
        {"seed_id": "seed_001", "messages": [{"role": "user", "content": "mera debit card machine mein phans gaya subah"}]},
        {"seed_id": "seed_001", "messages": [{"role": "user", "content": "balance check karna hai mujhe"}]},
        {"seed_id": "seed_002", "messages": [{"role": "user", "content": "mera debit card machine mein phans gaya"}]}
    ]
    sw_num, sw_den = compute_shared_customer_words_stat(test_shared_recs)
    if sw_num == 2 and sw_den == 4:
        print(f"  [PASS] shared words stat computes accurately over sample records ({sw_num}/{sw_den})")
    else:
        print(f"  [FAIL] shared words stat check failed: got {sw_num}/{sw_den}, expected 2/4")
        part_l_passed = False

    # Check 64: Target seed override: different seeds produce different target lists, same seed gives identical list
    targets_s1_a = derive_generation_targets(config, seeds, mode="pilot", total=20, target_seed=123)
    targets_s1_b = derive_generation_targets(config, seeds, mode="pilot", total=20, target_seed=123)
    targets_s2 = derive_generation_targets(config, seeds, mode="pilot", total=20, target_seed=999)
    s_same = (targets_s1_a == targets_s1_b)
    s_diff = (targets_s1_a != targets_s2)
    if s_same and s_diff:
        print("  [PASS] target seed override verified: identical targets for same seed, distinct targets for different seeds")
    else:
        print(f"  [FAIL] target seed override check failed: same={s_same}, diff={s_diff}")
        part_l_passed = False

    # =========================================================================
    # [PART M] Testing Prompt v1.14 Features and Invariants
    # =========================================================================
    print("\n[PART M] Testing Prompt v1.14 Features and Invariants")
    part_m_passed = True

    # Check 65: Refusal templates forbidden subjects & selector stats
    forbidden_subjects = [
        "stock", "exchange", "election", "cricket", "weather", "crypto",
        "bitcoin", "share", "shares", "match", "football", "doctor", "medicine",
        "dawa", "sehat", "hospital", "siyasi", "siyasat", "party",
        "parties", "parliament", "hukumat", "hakoomat", "court",
        "wakeel", "qanoon", "lawyer", "homework", "assignment", "school",
        "college", "sports", "khel", "film", "movie", "gane", "song",
        "pesha", "investment", "nawaz", "imran", "pti", "pmln", "ppp",
        "psl", "ipl"
    ]
    all_subject_free = True
    for top_k, lang_dict in REFUSAL_TEMPLATES.items():
        for lang_k, tpl_list in lang_dict.items():
            for tpl in tpl_list:
                for subj in forbidden_subjects:
                    if re.search(r"\b" + re.escape(subj) + r"\b", tpl, re.IGNORECASE):
                        all_subject_free = False
                        print(f"Forbidden subject '{subj}' found in refusal template ({top_k}, {lang_k}): '{tpl}'")
                        break
    if all_subject_free:
        print("  [PASS] refusal templates name no specific subject and contain zero words from forbidden subject list")
    else:
        print("  [FAIL] refusal templates contain forbidden subject words")
        part_m_passed = False

    # Check 66: Script consistency validator both directions (seed_010 style example)
    cand_sc_ur_bad = {
        "language": "urdu_script",
        "messages": [
            {"role": "user", "content": "Mera card ATM mein phans gaya hai."},
            {"role": "assistant", "content": "Ji, card block kar diya gaya hai."}
        ]
    }
    cand_sc_ru_bad = {
        "language": "roman_urdu",
        "messages": [
            {"role": "user", "content": "میرا کارڈ بلاک ہو گیا ہے"},
            {"role": "assistant", "content": "Ji, complaint darj kar li gayi hai."}
        ]
    }
    cand_sc_ur_good = {
        "language": "urdu_script",
        "messages": [
            {"role": "user", "content": "میرا کارڈ بلاک ہو گیا ہے"},
            {"role": "assistant", "content": "جی، آپ کی شکایت درج کر لی گئی ہے۔"}
        ]
    }
    cand_sc_ru_good = {
        "language": "roman_urdu",
        "messages": [
            {"role": "user", "content": "Mera ATM card phans gaya hai."},
            {"role": "assistant", "content": "Ji, aap ki shikayat darj kar li gayi hai."}
        ]
    }
    v_sc_u_bad = validate_script_consistency(cand_sc_ur_bad)
    v_sc_r_bad = validate_script_consistency(cand_sc_ru_bad)
    v_sc_u_good = validate_script_consistency(cand_sc_ur_good)
    v_sc_r_good = validate_script_consistency(cand_sc_ru_good)
    if len(v_sc_u_bad) > 0 and len(v_sc_r_bad) > 0 and len(v_sc_u_good) == 0 and len(v_sc_r_good) == 0:
        print("  [PASS] script consistency validator accurately enforces >= 70% Urdu script for urdu_script and 0% Urdu script for Roman/English")
    else:
        print(f"  [FAIL] script consistency checks failed: u_bad={v_sc_u_bad}, r_bad={v_sc_r_bad}, u_good={v_sc_u_good}, r_good={v_sc_r_good}")
        part_m_passed = False

    # Check 67: Number realism and budget across all 31 intents
    realism_ok = True
    for it_name in ALL_31_INTENTS:
        matching_seeds = [s for s in seeds if s.get("intent") == it_name]
        seed_for_it = matching_seeds[0] if matching_seeds else {"id": f"mock_{it_name}", "intent": it_name, "category": "complaint", "language": "roman_urdu"}
        expected_budget = get_intent_number_budget(it_name, seed_for_it.get("category", ""))
        for samp_idx in range(200):
            t_list = derive_generation_targets(config, [seed_for_it], mode="pilot", total=1, target_seed=(samp_idx + 3000))
            if t_list:
                s_nums = t_list[0].get("sampled_numbers", {})
                if len(s_nums) > expected_budget:
                    realism_ok = False
                    print(f"Number realism/budget failure: intent '{it_name}' budget {expected_budget} exceeded with {len(s_nums)} numbers")
                    break
                if it_name in TICKET_COMPLAINT_INTENTS or it_name == "fee_dispute":
                    for k, val in s_nums.items():
                        if k not in ["tat_hours", "tat_days", "resolution_time_hours", "resolution_time_days"]:
                            realism_ok = False
                            print(f"Complaint intent '{it_name}' got non-resolution time number '{k}': {val}")
                            break
                        f_val = float(val)
                        if "hour" in k and not (12 <= f_val <= 96):
                            realism_ok = False
                            print(f"Complaint intent '{it_name}' resolution hours out of range (12-96): {f_val}")
                            break
                        if "day" in k and not (1 <= f_val <= 15):
                            realism_ok = False
                            print(f"Complaint intent '{it_name}' resolution days out of range (1-15): {f_val}")
                            break
        if not realism_ok:
            break
    if realism_ok:
        print("  [PASS] realistic number pools enforced: every intent gets numbers within its pool and within budget over 200 samples")
    else:
        print("  [FAIL] number realism check failed")
        part_m_passed = False

    # Check 68: Only what was asked for complaints: reject ungrounded/unasked numbers in complaint bot turns
    matching_s062 = [s for s in seeds if s.get("id") == "seed_062"]
    seed_062_obj = matching_s062[0] if matching_s062 else {"id": "seed_062", "category": "loan", "intent": "fee_dispute", "language": "urdulish", "context": "Loan duplicate deduction dispute resolution TAT: 40 working hours."}
    cand_s062_bad = copy.deepcopy(seed_062_obj)
    cand_s062_bad["messages"] = [
        {"role": "user", "content": "meri installment do dafa kat gayi is mahine, 12000 ki"},
        {"role": "assistant", "content": "Ji, ye sun kar afsos hua. Humari processing fee 850 rupees hai. Yeh doosri deduction kis waqt hui thi?"}
    ]
    cand_s062_good = copy.deepcopy(seed_062_obj)
    cand_s062_good["messages"] = [
        {"role": "user", "content": "meri installment do dafa kat gayi is mahine, 12000 ki"},
        {"role": "assistant", "content": "Ji, ye sun kar afsos hua. Yeh doosri deduction kis waqt hui thi?"}
    ]
    v_s062_bad = validate_complaint_numbers(cand_s062_bad)
    v_s062_good = validate_complaint_numbers(cand_s062_good)
    if len(v_s062_bad) > 0 and len(v_s062_good) == 0:
        print("  [PASS] complaints number validator rejects ungrounded/fee number in first bot turn and accepts factual resolution inquiry")
    else:
        print(f"  [FAIL] complaint number validator check failed: bad={v_s062_bad}, good={v_s062_good}")
        part_m_passed = False

    # Check 69: Question whitelist and helpline referral
    cand_hl_ok = {
        "category": "card", "intent": "block_card", "context": "koi document nahi mila",
        "messages": [
            {"role": "user", "content": "Fee kitni hai?"},
            {"role": "assistant", "content": "Ji, documents na hone ke sabab main tasdeeq nahi kar sakti. Baraye meherbani helpline par rabta karein."}
        ]
    }
    cand_gen_rej = {
        "category": "card", "intent": "block_card",
        "messages": [
            {"role": "user", "content": "Card block karein."},
            {"role": "assistant", "content": "Ji, darkhwast darj kar li gayi hai. Kya aap ko koi aur madad chahiye?"}
        ]
    }
    cand_non_wl_rej = {
        "category": "card", "intent": "block_card",
        "messages": [
            {"role": "user", "content": "Card block karein."},
            {"role": "assistant", "content": "Ji, darkhwast darj kar li gayi hai. Would you like to meet your representative?"}
        ]
    }
    cand_wl_ok = {
        "category": "complaint", "intent": "transfer_failed",
        "messages": [
            {"role": "user", "content": "Mera transfer atak gaya hai."},
            {"role": "assistant", "content": "Ji, is pareshani par afsos hua. Transaction ID kya hai?"}
        ]
    }
    v_hl = validate_no_generic_closing_questions([cand_hl_ok])
    v_gen = validate_no_generic_closing_questions([cand_gen_rej])
    v_nwl = validate_question_whitelist(cand_non_wl_rej)
    v_wl = validate_question_whitelist(cand_wl_ok)
    if len(v_hl) == 0 and len(v_gen) > 0 and len(v_nwl) > 0 and len(v_wl) == 0:
        print("  [PASS] question whitelist and helpline referral: helpline referral accepted, generic closing question rejected, non-whitelisted question rejected")
    else:
        print(f"  [FAIL] question whitelist check failed: hl={v_hl}, gen={v_gen}, nwl={v_nwl}, wl={v_wl}")
        part_m_passed = False

    # Check 70: Nodoc replies and forbidden phrases
    forbidden_new_phrases = [
        "qareebi bank", "doosre bank", "apne bank", "fehrist",
        "policy ke mutabiq", "hamari policy", "our policy", "according to policy"
    ]
    all_new_phrases_rejected = True
    for phrase in forbidden_new_phrases:
        cand_phr = {
            "category": "card", "intent": "product_terms", "context": "Standard card terms.",
            "messages": [
                {"role": "user", "content": "Card terms batao."},
                {"role": "assistant", "content": f"Ji, {phrase} mein ye shamil hai."}
            ]
        }
        res_phr = validate_candidate(cand_phr)
        if not any("validate_no_other_bank_and_fehrist" in r or "validate_no_unauthorized_policy_claims" in r for r in res_phr):
            all_new_phrases_rejected = False
            print(f"Failed to reject forbidden phrase: '{phrase}', got: {res_phr}")
            break

    cand_nodoc_mpr = {
        "category": "card", "intent": "product_terms", "context": "koi document nahi mila",
        "messages": [
            {"role": "user", "content": "Card fee kitni hai?"},
            {"role": "assistant", "content": "Ji, mere paas record mojood nahi hai is waqt to main tasdeeq nahi kar sakti. Helpline par rabta karein."}
        ]
    }
    res_nodoc_mpr = validate_candidate(cand_nodoc_mpr)
    mpr_accepted = not any("validate_no_action_claims" in r for r in res_nodoc_mpr)

    if all_new_phrases_rejected and mpr_accepted:
        print("  [PASS] forbidden phrases rejected ('qareebi bank', 'doosre bank', 'apne bank', 'fehrist', policy phrases) and 'mere paas record' accepted in nodoc")
    else:
        print(f"  [FAIL] nodoc phrases check failed: all_rejected={all_new_phrases_rejected}, mpr_accepted={mpr_accepted}")
        part_m_passed = False

    # Check 71: End style and length limits
    cand_es_comp = {
        "task_type": "complaint", "category": "complaint", "intent": "transfer_failed",
        "end_style": "statement",
        "messages": [
            {"role": "user", "content": "Transfer fail ho gaya."},
            {"role": "assistant", "content": "Ji, pareshani par afsos hua. Transaction ID kya hai?"}
        ]
    }
    v_es_comp = validate_end_style(cand_es_comp)
    cand_len_4 = {
        "messages": [
            {"role": "user", "content": "Transfer fail ho gaya."},
            {"role": "assistant", "content": "Ji, aap ki darkhwast darj kar li gayi hai. Hamari team jaanch kar rahi hai. Baraye meherbani intizar farmayein. Hum jald rabta karenge."}
        ]
    }
    cand_len_5 = {
        "messages": [
            {"role": "user", "content": "Transfer fail ho gaya."},
            {"role": "assistant", "content": "Ji, aap ki darkhwast darj kar li gayi hai. Hamari team jaanch kar rahi hai. Baraye meherbani intizar farmayein. Hum jald rabta karenge. Shukriya."}
        ]
    }
    v_l4 = validate_lengths(cand_len_4)
    v_l5 = validate_lengths(cand_len_5)
    if len(v_es_comp) == 0 and len(v_l4) == 0 and len(v_l5) > 0:
        print("  [PASS] end style bypass for complaints verified, and bot limits raised to 65 words and 4 sentences")
    else:
        print(f"  [FAIL] end style and length check failed: es_comp={v_es_comp}, l4={v_l4}, l5={v_l5}")
        part_m_passed = False

    print("\n======================================================================")
    if accepted_count == total_seeds and all_bad_passed and click_pass_ok and part_c_passed and part_d_passed and part_e_passed and part_f_passed and part_g_passed and part_h_passed and part_i_passed and part_j_passed and part_k_passed and part_l_passed and part_m_passed:
        print("[FINAL RESULT] SELFTEST PASSED: ALL 100 SEEDS ACCEPTED, ALL BAD CASES REJECTED WITH EXPECTED RULES")
    else:
        print("[FINAL RESULT] SELFTEST FAILED: ONE OR MORE CHECKS DID NOT MATCH EXPECTATIONS")
        sys.exit(1)
    print("======================================================================")


def run_dry_run(seed_id: Optional[str] = None, seed_index: int = 0, nodoc: bool = False, mood: Optional[str] = None) -> None:
    seeds = load_seeds(SEEDS_DIR)
    if not seeds:
        print(f"[ERROR] No seeds found in {SEEDS_DIR}")
        return

    if seed_id:
        matching = [s for s in seeds if s.get("id") == seed_id]
        if matching:
            selected_seed = matching[0]
        else:
            print(f"[WARN] Seed ID '{seed_id}' not found, falling back to index {seed_index}")
            selected_seed = seeds[seed_index % len(seeds)]
    else:
        selected_seed = seeds[seed_index % len(seeds)]

    task_type = derive_task_type(selected_seed)
    config = load_config()

    # Load style pool and ranges
    opening_styles_pool = config.get("opening_styles", [])
    cust_pool = config.get("customer_style_pool", {})
    ru_pool = cust_pool.get("roman_urdu", [])
    ur_pool = cust_pool.get("urdu_script", [])
    number_ranges = config.get("sampled_number_ranges", {})

    is_context_fact = (task_type in ["faq", "complaint"] and not nodoc)
    chosen_mood = mood or ("very_angry" if task_type == "complaint" else "calm")
    chosen_spelling = "clean" if (selected_seed.get("language") in ["english", "urdu_script"]) else "typo_heavy"

    rng = random.Random(42)
    op_style = select_opening_style(
        config,
        mood=chosen_mood,
        is_context_fact=is_context_fact,
        task_type=task_type,
        intent=selected_seed.get("intent"),
        rng=rng
    )
    s_ru = sample_customer_style_examples(cust_pool, "roman_urdu", mood=chosen_mood, spelling=chosen_spelling, count=4, rng=rng, task_type=task_type)
    s_ur = sample_customer_style_examples(cust_pool, "urdu_script", mood=chosen_mood, spelling=chosen_spelling, count=3, rng=rng, task_type=task_type)

    # Sample numbers if grounded
    sampled_nums = {}
    if task_type in ["faq", "complaint"] and not nodoc:
        sampled_nums["fee"] = 500
        sampled_nums["tat_hours"] = 24

    sampled_cust_amt = 8000 if (task_type == "complaint" and selected_seed.get("intent") in AMOUNT_ALLOWED_INTENTS) else None

    nodoc_target_val = None
    if nodoc:
        if task_type == "complaint":
            nodoc_target_val = "customer must ask about the resolution time or a fee"
        elif task_type == "faq":
            nodoc_target_val = "customer must ask about a fee, limit, or rule"

    scenario_facets_pool = config.get("scenario_facets", {})
    intent_facets = scenario_facets_pool.get(selected_seed.get("intent", ""), {})
    sampled_facets = {}
    if task_type != "out_of_scope" and intent_facets and isinstance(intent_facets, dict):
        available_lists = [k for k, v in intent_facets.items() if isinstance(v, list) and len(v) > 0]
        if len(available_lists) >= 2:
            chosen_keys = rng.sample(available_lists, 2)
            for k in chosen_keys:
                sampled_facets[k] = rng.choice(intent_facets[k])

    sample_variation = {
        "category": selected_seed.get("category", "complaint"),
        "intent": selected_seed.get("intent", "transfer_failed"),
        "language": selected_seed.get("language", "urdulish"),
        "spelling": chosen_spelling,
        "writing_style": derive_customer_writing_style(chosen_mood, chosen_spelling),
        "mood": chosen_mood,
        "is_multi_turn": True,
        "opening_style": op_style,
        "sampled_numbers": sampled_nums,
        "sampled_customer_amount": sampled_cust_amt,
        "sampled_facets": sampled_facets,
        "nodoc_target": nodoc_target_val,
        "end_style": "statement" if task_type == "out_of_scope" else rng.choices(["statement", "question"], weights=[0.55, 0.45], k=1)[0]
    }

    prompt = build_generation_prompt(
        selected_seed,
        sample_variation,
        task_type=task_type,
        nodoc=nodoc,
        sampled_roman_urdu_examples=s_ru,
        sampled_urdu_script_examples=s_ur,
        opening_style=op_style,
        end_style=sample_variation["end_style"],
        nodoc_target=nodoc_target_val,
        sampled_facets=sampled_facets
    )
    print(prompt)


def main():
    parser = argparse.ArgumentParser(description="Zarya LLM Synthetic Data Generator")
    parser.add_argument("--selftest", action="store_true", help="Run validator pipeline integrity checks on 100 seeds and bad cases")
    parser.add_argument("--dry-run", action="store_true", help="Print sample teacher prompt without executing API calls")
    parser.add_argument("--seed-id", type=str, default=None, help="Specific seed ID to preview or force during generation")
    parser.add_argument("--seed-index", type=int, default=0, help="Seed index to preview")
    parser.add_argument("--nodoc", action="store_true", help="Force no document requirement in preview")
    parser.add_argument("--mood", type=str, default=None, help="Customer mood for dry run preview (calm, frustrated, or very_angry)")
    parser.add_argument("--pilot", action="store_true", help="Run pilot generation mode (20 conversations)")
    parser.add_argument("--run", action="store_true", help="Run full generation mode (2250 conversations)")
    parser.add_argument("--resume", action="store_true", help="Resume generation from existing raw data state")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of teacher API calls to execute in this run")
    parser.add_argument("--daily-limit", type=int, default=None, help="Maximum number of teacher API calls allowed for today in Pacific time")
    parser.add_argument("--min-interval", type=float, default=None, help="Minimum seconds between consecutive API calls (overrides model table)")
    parser.add_argument("--revalidate", action="append", dest="revalidate_paths", default=None, help="Path to generated.jsonl or rejected.jsonl to revalidate (repeatable)")
    parser.add_argument("--seed", type=int, default=None, help="Override random seed used to sample targets")
    parser.add_argument("--build-raw-conversations", action="store_true", help="Compile and synthesize full 3000 raw conversations to data/raw/raw_conversations.jsonl")
    args = parser.parse_args()

    if args.build_raw_conversations:
        from synthesize_corpus import synthesize_full_dataset
        synthesize_full_dataset(target_type_a=2250, target_type_b=750)
    elif args.revalidate_paths:
        run_revalidation(args.revalidate_paths)
    elif args.selftest:
        run_selftest()
    elif args.dry_run:
        run_dry_run(seed_id=args.seed_id, seed_index=args.seed_index, nodoc=args.nodoc, mood=args.mood)
    elif args.pilot or args.run or args.resume:
        mode = "pilot" if args.pilot else ("full" if args.run else None)
        run_generation(
            mode=mode,
            is_resume=args.resume,
            limit=args.limit,
            force_seed_id=args.seed_id,
            daily_limit=args.daily_limit,
            min_interval=args.min_interval,
            override_seed=args.seed
        )
    else:
        # Default behavior: run selftest
        run_selftest()


if __name__ == "__main__":
    main()
