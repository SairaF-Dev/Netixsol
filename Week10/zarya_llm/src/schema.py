from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator
import yaml


def get_large_amount_threshold() -> float:
    base_dir = Path(__file__).resolve().parent.parent
    config_path = base_dir / "configs" / "data_spec.yaml"
    if not config_path.exists():
        config_path = Path("configs/data_spec.yaml")

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return float(data.get("escalation", {}).get("large_amount_threshold", 50000.0))
    return 50000.0


def get_qwen_tokenizer(model_id: str = "Qwen/Qwen2.5-3B-Instruct"):
    try:
        from transformers import AutoTokenizer
        return AutoTokenizer.from_pretrained(model_id)
    except Exception:
        from transformers import Qwen2Tokenizer
        return Qwen2Tokenizer.from_pretrained(model_id)


class TicketCategory(str, Enum):
    account = "account"
    transfer = "transfer"
    card = "card"
    loan = "loan"
    complaint = "complaint"
    fraud = "fraud"
    out_of_scope = "out_of_scope"


class TicketPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class BankingIntent(str, Enum):
    check_balance = "check_balance"
    open_account = "open_account"
    account_statement = "account_statement"
    update_profile = "update_profile"
    dormant_account = "dormant_account"
    transfer_failed = "transfer_failed"
    wrong_transfer = "wrong_transfer"
    pending_transaction = "pending_transaction"
    bill_payment = "bill_payment"
    raast_inquiry = "raast_inquiry"
    block_card = "block_card"
    unblock_card = "unblock_card"
    card_declined = "card_declined"
    card_delivery = "card_delivery"
    atm_cash_dispense_issue = "atm_cash_dispense_issue"
    international_usage = "international_usage"
    loan_eligibility = "loan_eligibility"
    installment_inquiry = "installment_inquiry"
    product_terms = "product_terms"
    service_complaint = "service_complaint"
    fee_dispute = "fee_dispute"
    staff_complaint = "staff_complaint"
    tat_breach = "tat_breach"
    report_scam_call = "report_scam_call"
    unauthorized_transaction = "unauthorized_transaction"
    phishing_report = "phishing_report"
    sim_swap_report = "sim_swap_report"
    refuse_credentials = "refuse_credentials"
    out_of_scope_query = "out_of_scope_query"
    general_chit_chat = "general_chit_chat"
    investment_advice_refusal = "investment_advice_refusal"


class BankingTicket(BaseModel):
    intent: BankingIntent = Field(description="Customer specific intent")
    category: TicketCategory = Field(description="Operational category")
    priority: TicketPriority = Field(description="Urgency priority level")
    amount: Optional[float] = Field(default=None, description="Disputed or referenced currency sum")
    time_mentioned: Optional[str] = Field(
        default=None,
        description="Customer own words about when it happened (e.g. 'kal sham', 'aaj subah'), or null. Never a date or clock time."
    )
    summary: str = Field(min_length=3, max_length=200, description="Short summary of customer request")
    customer_very_angry: bool = Field(
        default=False,
        description="Internal flag used only by generator and validator, not shown to customer"
    )
    escalate_to_human: bool = Field(description="True if human intervention is required")

    @model_validator(mode="after")
    def verify_escalation_rules(self):
        threshold = get_large_amount_threshold()
        is_fraud = self.category == TicketCategory.fraud
        is_large_amount = self.amount is not None and self.amount >= threshold
        is_angry = bool(self.customer_very_angry)

        should_escalate = is_fraud or is_large_amount or is_angry

        if should_escalate != self.escalate_to_human:
            if should_escalate and not self.escalate_to_human:
                raise ValueError(
                    f"escalate_to_human must be true when category is fraud, amount >= {threshold}, or customer is very angry"
                )
            else:
                raise ValueError(
                    f"escalate_to_human must be false when category is not fraud, amount < {threshold}, and customer is not very angry"
                )
        return self


class ChatMessage(BaseModel):
    role: str
    content: str


class ConversationRecord(BaseModel):
    id: str
    category: TicketCategory
    intent: BankingIntent
    language: str
    is_multi_turn: bool
    messages: List[ChatMessage]
    ticket: Optional[BankingTicket] = None
