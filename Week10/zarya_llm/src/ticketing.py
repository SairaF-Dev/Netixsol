"""
ticketing.py
============
Week 10 Day 4 - Task 5: Core Banking Ticketing & Tool Orchestrator

Handles:
1. Automated SQLite/PostgreSQL compliant schema for customer complaints.
2. Generating unique banking ticket numbers (ZAR-YYYYMMDD-XXXX).
3. Mapping SBP mandated Turnaround Times (TAT).
4. Automatic human escalation logic:
   - Fraud / unauthorized transaction
   - Disputed financial loss > Rs. 50,000
   - Highly distressed / angry sentiment
5. Database operations (create, query, escalate, list).
"""

import os
import sys
import time
import json
import sqlite3
import random
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Workspace Paths
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "zarya_banking.db"

# State Bank of Pakistan Mandated TAT Mapping
TAT_RULES = {
    "ATM": {
        "hours": 72,
        "description": "2 to 3 business days (SBP BCPG Section 4)",
        "priority_default": "MEDIUM"
    },
    "IBFT": {
        "hours": 24,
        "description": "24 hours for 1LINK IBFT / 4 hours for Raast",
        "priority_default": "MEDIUM"
    },
    "CARD": {
        "hours": 168,
        "description": "7 business days for PayPak / 14 days for Visa disputes",
        "priority_default": "LOW"
    },
    "FRAUD": {
        "hours": 336,
        "description": "Immediate freeze within 5 mins; Investigation within 14 calendar days",
        "priority_default": "CRITICAL"
    },
    "ACCOUNT": {
        "hours": 48,
        "description": "2 business days",
        "priority_default": "LOW"
    },
    "GENERAL": {
        "hours": 24,
        "description": "24 hours",
        "priority_default": "LOW"
    }
}


class BankingTicketingSystem:
    """
    Manages complaint ticket lifecycle and automated human escalation.
    """
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """
        Initializes the complaints table in SQLite.
        """
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS complaint_tickets (
                    ticket_id TEXT PRIMARY KEY,
                    customer_id TEXT,
                    category TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    amount REAL DEFAULT 0.0,
                    summary TEXT NOT NULL,
                    details TEXT NOT NULL,
                    tat_hours INTEGER NOT NULL,
                    tat_description TEXT NOT NULL,
                    escalated_to_human INTEGER DEFAULT 0,
                    escalation_reason TEXT,
                    status TEXT DEFAULT 'OPEN',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def generate_ticket_id(self) -> str:
        """
        Generates standard banking ticket number: ZAR-YYYYMMDD-XXXX
        """
        today_str = datetime.datetime.now().strftime("%Y%m%d")
        rand_suffix = random.randint(1000, 9999)
        return f"ZAR-{today_str}-{rand_suffix}"

    def evaluate_escalation(
        self,
        category: str,
        priority: str,
        amount: float,
        sentiment: str
    ) -> Tuple[bool, str]:
        """
        Evaluates whether complaint requires immediate human agent escalation.
        Conditions:
        1. Fraud / Scam / Unauthorized debit -> CRITICAL -> Escalated
        2. Disputed financial amount > Rs. 50,000 -> Escalated
        3. Angry / High distress customer sentiment -> Escalated
        """
        cat_upper = category.upper()
        prio_upper = priority.upper()
        sent_lower = sentiment.lower()

        reasons = []
        if cat_upper == "FRAUD" or prio_upper == "CRITICAL":
            reasons.append("High-severity fraud or unauthorized activity reported")
        if amount >= 50000.0:
            reasons.append(f"High transaction dispute value (Rs. {amount:,.0f} >= Rs. 50,000 threshold)")
        if any(w in sent_lower for w in ["angry", "furious", "ghussa", "fraud", "court", "ombudsman"]):
            reasons.append("Distressed or aggressive customer sentiment detected")

        if reasons:
            return True, " | ".join(reasons)
        return False, "Standard automated workflow"

    def create_ticket(
        self,
        category: str,
        summary: str,
        details: str,
        customer_id: str = "CUST-90214",
        amount: float = 0.0,
        priority: Optional[str] = None,
        sentiment: str = "neutral"
    ) -> Dict[str, Any]:
        """
        Creates and persists a new complaint ticket in the database.
        """
        cat_key = category.upper() if category.upper() in TAT_RULES else "GENERAL"
        tat_spec = TAT_RULES[cat_key]

        assigned_priority = priority.upper() if priority else tat_spec["priority_default"]
        
        # Override priority to HIGH or CRITICAL if amount > 50,000 or fraud
        if cat_key == "FRAUD":
            assigned_priority = "CRITICAL"
        elif amount >= 50000.0 and assigned_priority != "CRITICAL":
            assigned_priority = "HIGH"

        escalated, escalation_reason = self.evaluate_escalation(
            category=cat_key,
            priority=assigned_priority,
            amount=amount,
            sentiment=sentiment
        )

        ticket_id = self.generate_ticket_id()
        now_iso = datetime.datetime.now().isoformat()
        status = "ESCALATED" if escalated else "OPEN"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO complaint_tickets (
                    ticket_id, customer_id, category, priority, amount,
                    summary, details, tat_hours, tat_description,
                    escalated_to_human, escalation_reason, status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticket_id, customer_id, cat_key, assigned_priority, amount,
                summary, details, tat_spec["hours"], tat_spec["description"],
                1 if escalated else 0, escalation_reason, status,
                now_iso, now_iso
            ))
            conn.commit()

        return {
            "ticket_id": ticket_id,
            "category": cat_key,
            "priority": assigned_priority,
            "amount": amount,
            "summary": summary,
            "tat": tat_spec["description"],
            "tat_hours": tat_spec["hours"],
            "escalated_to_human": escalated,
            "escalation_reason": escalation_reason,
            "status": status,
            "created_at": now_iso
        }

    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a ticket by ticket_id.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM complaint_tickets WHERE ticket_id = ?", (ticket_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def update_ticket_status(self, ticket_id: str, new_status: str) -> bool:
        """
        Updates the status of an existing complaint ticket (e.g. RESOLVED, CLOSED, IN_REVIEW).
        """
        now_iso = datetime.datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE complaint_tickets
                SET status = ?, updated_at = ?
                WHERE ticket_id = ?
            """, (new_status.upper(), now_iso, ticket_id))
            conn.commit()
            return cursor.rowcount > 0

    def list_tickets(self, limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lists stored tickets with optional status filtering.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if status:
                cursor.execute("SELECT * FROM complaint_tickets WHERE status = ? ORDER BY created_at DESC LIMIT ?", (status, limit))
            else:
                cursor.execute("SELECT * FROM complaint_tickets ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        
    print("=" * 70)
    print("ZARYA BANK LLM: DAY 4 - TASK 5: CORE BANKING TICKETING & TOOLS")
    print("=" * 70)
    
    ticketing = BankingTicketingSystem()
    print(f"Connected to database at: {ticketing.db_path}")

    # Test Case A: Standard Disputed ATM Cash Deduction
    print("\n--- Test Scenario 1: Disputed ATM Cash Deduction ---")
    t1 = ticketing.create_ticket(
        category="ATM",
        summary="ATM debited Rs. 10,000 but cash not dispensed",
        details="Customer tried to withdraw Rs. 10,000 from 1LINK ATM at F-10 Islamabad. Slip generated: cash error.",
        amount=10000.0,
        sentiment="neutral"
    )
    print(f"  * Ticket ID        : {t1['ticket_id']}")
    print(f"  * Category / Prio  : {t1['category']} | {t1['priority']}")
    print(f"  * TAT              : {t1['tat']}")
    print(f"  * Escalated Human  : {t1['escalated_to_human']} ({t1['escalation_reason']})")
    print(f"  * Status           : {t1['status']}")

    # Test Case B: High-Value Disputed Transfer > Rs. 50,000
    print("\n--- Test Scenario 2: High-Value Disputed Transfer (Rs. 85,000) ---")
    t2 = ticketing.create_ticket(
        category="IBFT",
        summary="Failed Raast transfer of Rs. 85,000",
        details="Sender account debited Rs. 85,000, recipient bank did not receive funds after 12 hours.",
        amount=85000.0,
        sentiment="concerned"
    )
    print(f"  * Ticket ID        : {t2['ticket_id']}")
    print(f"  * Category / Prio  : {t2['category']} | {t2['priority']}")
    print(f"  * TAT              : {t2['tat']}")
    print(f"  * Escalated Human  : {t2['escalated_to_human']} ({t2['escalation_reason']})")
    print(f"  * Status           : {t2['status']}")

    # Test Case C: Suspected Card Fraud / Phishing
    print("\n--- Test Scenario 3: Unauthorized Card Fraud / Phishing ---")
    t3 = ticketing.create_ticket(
        category="FRAUD",
        summary="Unauthorized international transaction on Visa card",
        details="Customer received OTP and SMS notification for Rs. 42,000 transaction on unknown merchant site.",
        amount=42000.0,
        sentiment="angry"
    )
    print(f"  * Ticket ID        : {t3['ticket_id']}")
    print(f"  * Category / Prio  : {t3['category']} | {t3['priority']}")
    print(f"  * TAT              : {t3['tat']}")
    print(f"  * Escalated Human  : {t3['escalated_to_human']} ({t3['escalation_reason']})")
    print(f"  * Status           : {t3['status']}")

    # Verify listing
    all_tickets = ticketing.list_tickets(limit=10)
    print(f"\nTotal Tickets in Database: {len(all_tickets)}")
    print("=" * 70)
    print("TASK 5 TICKETING VERIFICATION COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()

