import yaml
from schema import (
    BankingTicket,
    TicketCategory,
    TicketPriority,
    BankingIntent,
    ConversationRecord,
    ChatMessage,
    get_large_amount_threshold,
    get_qwen_tokenizer,
)
from prompt_format import build_system_message


def test_specification_config():
    with open("configs/data_spec.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    total = cfg["total_examples"]
    assert total == 3000, "Total examples must equal 3000"

    task_mix = cfg["task_mix"]
    task_count_sum = sum(v["count"] for v in task_mix.values())
    task_pct_sum = sum(v["percentage"] for v in task_mix.values())
    assert task_count_sum == 3000, f"Task count sum {task_count_sum} != 3000"
    assert task_pct_sum == 100, f"Task percentage sum {task_pct_sum} != 100"

    lang_mix = cfg["language_mix"]
    lang_count_sum = sum(v["count"] for v in lang_mix.values())
    lang_pct_sum = sum(v["percentage"] for v in lang_mix.values())
    assert lang_count_sum == 3000, f"Language count sum {lang_count_sum} != 3000"
    assert lang_pct_sum == 100, f"Language percentage sum {lang_pct_sum} != 100"

    threshold = cfg.get("escalation", {}).get("large_amount_threshold")
    assert threshold is not None, "configs/data_spec.yaml must define escalation.large_amount_threshold"
    assert threshold == 50000.0, f"Expected 50000.0 placeholder threshold, got {threshold}"

    print(f"Step 2 Config Verification Passed: Exact 3000 total, 100% sums, and threshold {threshold} verified.")


def test_escalation_rules():
    threshold = get_large_amount_threshold()
    print(f"Testing escalation rules using dynamic threshold: {threshold}")

    # Case 1: Normal standard ticket (not fraud, amount < threshold, not angry)
    # Even if priority is high, escalate_to_human should be False
    normal_high_priority = BankingTicket(
        intent=BankingIntent.transfer_failed,
        category=TicketCategory.transfer,
        priority=TicketPriority.high,
        amount=1000.0,
        time_mentioned="kal sham",
        summary="Transfer delayed for bill payment",
        customer_very_angry=False,
        escalate_to_human=False
    )
    assert normal_high_priority.escalate_to_human is False
    print("  [PASS] High priority complaint alone does NOT force escalate_to_human")

    # Case 2: Condition (a) Category is fraud -> escalate_to_human must be True
    fraud_escalated = BankingTicket(
        intent=BankingIntent.report_scam_call,
        category=TicketCategory.fraud,
        priority=TicketPriority.high,
        amount=None,
        time_mentioned=None,
        summary="Customer received fake call asking for OTP",
        customer_very_angry=False,
        escalate_to_human=True
    )
    assert fraud_escalated.escalate_to_human is True

    fraud_caught = False
    try:
        BankingTicket(
            intent=BankingIntent.report_scam_call,
            category=TicketCategory.fraud,
            priority=TicketPriority.medium,
            amount=None,
            time_mentioned=None,
            summary="Fake caller asking for card PIN",
            customer_very_angry=False,
            escalate_to_human=False
        )
    except ValueError:
        fraud_caught = True
    assert fraud_caught, "Validation must enforce escalate_to_human=True when category is fraud"
    print("  [PASS] Condition (a) Fraud category enforces escalate_to_human=True")

    # Case 3: Condition (b) Amount >= large_amount_threshold -> escalate_to_human must be True
    large_amt_escalated = BankingTicket(
        intent=BankingIntent.transfer_failed,
        category=TicketCategory.transfer,
        priority=TicketPriority.medium,
        amount=threshold,
        time_mentioned="aaj subah",
        summary="High value transfer stuck",
        customer_very_angry=False,
        escalate_to_human=True
    )
    assert large_amt_escalated.escalate_to_human is True

    large_amt_caught = False
    try:
        BankingTicket(
            intent=BankingIntent.transfer_failed,
            category=TicketCategory.transfer,
            priority=TicketPriority.medium,
            amount=threshold + 10000.0,
            time_mentioned="aaj subah",
            summary="Very large transfer stuck",
            customer_very_angry=False,
            escalate_to_human=False
        )
    except ValueError:
        large_amt_caught = True
    assert large_amt_caught, f"Validation must enforce escalate_to_human=True when amount >= {threshold}"
    print(f"  [PASS] Condition (b) Amount >= {threshold} enforces escalate_to_human=True")

    # Case 4: Condition (c) customer_very_angry is True -> escalate_to_human must be True
    angry_escalated = BankingTicket(
        intent=BankingIntent.service_complaint,
        category=TicketCategory.complaint,
        priority=TicketPriority.medium,
        amount=500.0,
        time_mentioned="3 din se",
        summary="Customer shouting and furious over branch behavior",
        customer_very_angry=True,
        escalate_to_human=True
    )
    assert angry_escalated.escalate_to_human is True

    angry_caught = False
    try:
        BankingTicket(
            intent=BankingIntent.service_complaint,
            category=TicketCategory.complaint,
            priority=TicketPriority.medium,
            amount=500.0,
            time_mentioned="3 din se",
            summary="Customer furious and demanding supervisor",
            customer_very_angry=True,
            escalate_to_human=False
        )
    except ValueError:
        angry_caught = True
    assert angry_caught, "Validation must enforce escalate_to_human=True when customer_very_angry is True"
    print("  [PASS] Condition (c) customer_very_angry enforces escalate_to_human=True")


def test_qwen_chat_template():
    with open("configs/data_spec.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    exact_model_id = cfg["chat_format"]["model_id"]
    assert exact_model_id == "Qwen/Qwen2.5-3B-Instruct", f"Expected exact id Qwen/Qwen2.5-3B-Instruct, got {exact_model_id}"

    tokenizer = get_qwen_tokenizer(exact_model_id)
    print(f"Loaded tokenizer successfully for exact model_id: {exact_model_id}")

    sample_dialogue = [
        {
            "role": "system",
            "content": cfg["persona"]["system_message"]
        },
        {
            "role": "user",
            "content": "Mera Raast transfer fail ho gaya lekin paise kat gaye"
        },
        {
            "role": "assistant",
            "content": "Ji maazrat chahte hain aap ko pareshani hui. Kya aap transaction ID bata sakte hain?"
        }
    ]

    formatted_text = tokenizer.apply_chat_template(
        sample_dialogue,
        tokenize=False,
        add_generation_prompt=False
    )

    print("\n--- RENDERED CHAT TEMPLATE OUTPUT ---")
    print(formatted_text)
    print("--- END RENDERED CHAT TEMPLATE OUTPUT ---\n")

    assert "<|im_start|>system" in formatted_text
    assert "<|im_start|>user" in formatted_text
    assert "<|im_start|>assistant" in formatted_text
    assert "<|im_end|>" in formatted_text
    print("Step 2 Tokenizer Chat Template Passed: Qwen 2.5 3B ChatML template applied successfully.")


def test_qwen_chat_template_with_documents():
    with open("configs/data_spec.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    exact_model_id = cfg["chat_format"]["model_id"]
    tokenizer = get_qwen_tokenizer(exact_model_id)

    # 1. System message with grounded context documents
    grounded_sys_msg = build_system_message(
        cfg["persona"]["system_message"],
        "Raast transfer dispute resolution time: 24 working hours."
    )
    dialogue_with_context = [
        {"role": "system", "content": grounded_sys_msg},
        {"role": "user", "content": "Mera Raast transfer fail ho gaya lekin paise kat gaye"},
        {"role": "assistant", "content": "Ji shukriya. Aap ki shikayat darj kar li gayi hai, resolution ka TAT 24 working hours hai."}
    ]
    rendered_context = tokenizer.apply_chat_template(dialogue_with_context, tokenize=False)
    print("\n--- RENDERED CHAT TEMPLATE WITH DOCUMENTS ---")
    print(rendered_context)
    print("--- END RENDERED CHAT TEMPLATE WITH DOCUMENTS ---\n")

    assert "Documents: Raast transfer dispute resolution time: 24 working hours." in rendered_context
    assert "<|im_start|>system\n" in rendered_context
    assert "<|im_end|>\n<|im_start|>user\n" in rendered_context
    assert "<|im_end|>\n<|im_start|>assistant\n" in rendered_context

    # 2. System message with no-document token
    no_doc_sys_msg = build_system_message(
        cfg["persona"]["system_message"],
        "koi document nahi mila"
    )
    dialogue_no_doc = [
        {"role": "system", "content": no_doc_sys_msg},
        {"role": "user", "content": "Gold debit card ki annual fee kitni hai?"},
        {"role": "assistant", "content": "Ji, is waqt documents mein maloomat na hone ki wajah se main fee ki tasdeeq nahi kar sakti. Baraye meherbani maloomat ke liye helpline par rabta karein. Kya aap ko kisi aur cheez mein madad chahiye?"}
    ]
    rendered_no_doc = tokenizer.apply_chat_template(dialogue_no_doc, tokenize=False)
    assert "Documents: koi document nahi mila" in rendered_no_doc
    print("Step 2 Tokenizer With Documents Passed: System messages with grounded context and no-doc tokens render properly.")


if __name__ == "__main__":
    print("==================================================")
    print("STARTING FULL STEP 2 VALIDATION TEST SUITE")
    print("==================================================")
    test_specification_config()
    test_escalation_rules()
    test_qwen_chat_template()
    test_qwen_chat_template_with_documents()
    print("==================================================")
    print("ALL STEP 2 VALIDATION TESTS SUCCEEDED.")
    print("==================================================")
