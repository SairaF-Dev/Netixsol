# Architectural Decision Document: Zarya Digital Bank Assistant

## 1. Executive Summary

Zarya Digital Bank is an emerging digital financial institution in Pakistan serving more than two million active application users. The customer support department manages tens of thousands of customer inquiries daily across in application chat, WhatsApp, and telephone helplines. The majority of these interactions occur in UrduLish, an informal blend of Roman Urdu and English vocabulary common in everyday Pakistani digital communication.

Initial experimentation with external proprietary model APIs surfaced three critical barriers to production deployment:

1. Regulatory compliance and data privacy concerns under State Bank of Pakistan frameworks, which prohibit transmitting customer financial records and confidential inquiries to foreign cloud infrastructure.
2. Unacceptable operational expenditure, where commercial API token costs scale linearly with message volume and become unsustainable at peak traffic.
3. Suboptimal conversation quality, characterized by robotic UrduLish phrasing, persistent failure to maintain the respectful cultural persona of the bank, and frequent policy hallucinations regarding limits and fees.

This decision document evaluates four candidate architectures to establish the technical foundation for the banking assistant of Zarya Digital Bank. It justifies the selection of a fine tuning plus Retrieval Augmented Generation hybrid architecture, supported by a two layer defence in depth security framework.

## 2. Evaluation of Candidate Architectures

### Approach 1: Prompt Engineering Only

This approach relies on a general purpose base model paired with an extensive system prompt, few shot examples, and detailed instructions provided in the context window on every request.

Quality: General purpose models often struggle with informal UrduLish grammar, colloquial phrasing, and regional financial terminology. While few shot prompting can guide the model, long prompts frequently suffer from attention degradation, causing the assistant to drift from the required respectful tone or produce invalid JSON outputs during complex multi turn conversations.

Cost: Operational costs remain high. Every user interaction requires transmitting several thousand tokens of prompt instructions and examples, multiplying input token expenditure across all interactions.

Privacy: If implemented using commercial API endpoints hosted overseas, this approach violates State Bank of Pakistan data residency requirements. If hosted locally, the large context windows consume significant GPU memory, reducing overall serving throughput.

Latency: Processing massive system prompts and few shot demonstrations increases time to first token and limits total concurrent request handling capacity.

Effort: Minimal engineering effort is needed initially. The primary investment involves writing and iterating on system prompts.

Updatability: Extremely straightforward. Adjusting bank policies, fees, or operating rules only requires editing the prompt text in application configuration.

### Approach 2: Retrieval Augmented Generation Only

This approach pairs an off the shelf language model with a vector retrieval system. When a customer sends an inquiry, relevant banking documents, fee structures, and policy snippets are retrieved from a vector database and injected into the dynamic context window.

Quality: Grounding the model on retrieved documents dramatically reduces factual hallucinations regarding charges, turnaround times, and limits. However, the foundational model still lacks intrinsic UrduLish linguistic alignment, often generating stiff or unnatural translations of formal banking text. Formatting adherence for structured JSON tickets remains unreliable without model level fine tuning.

Cost: Moderate. While system prompts can be streamlined compared to pure prompt engineering, injecting retrieved context chunks into every turn increases the input token payload.

Privacy: Similar to prompt engineering, privacy hinges on deployment location. Running both the embedding pipeline, vector store, and model within local bank infrastructure satisfies data residency rules.

Latency: Latency includes embedding the customer query, executing similarity search in the vector store, building the augmented prompt, and generating the response. This multi stage process increases total response time.

Effort: Moderate engineering effort is required to chunk documents, generate embeddings, index vector collections, tune similarity thresholds, and maintain retrieval pipelines.

Updatability: Excellent. Updating fee tables, transaction ceilings, or processing windows requires only re indexing the modified documentation. The underlying model remains untouched.

### Approach 3: Fine Tuning Only

This approach takes an open source foundation model, specifically Qwen 2.5 3B Instruct, and performs supervised fine tuning using parameter efficient methods on thousands of curated banking dialogues in UrduLish. All bank knowledge, behavioral patterns, and JSON formatting requirements are learned into the model weights.

Quality: Supervised fine tuning achieves outstanding domain mastery. The model speaks fluent, culturally authentic UrduLish, consistently employs respectful honorifics like Ji and aap, reliably outputs syntactically valid JSON tickets, and rejects credential disclosure requests.

Cost: Highly cost effective at scale. Once fine tuned and deployed on self hosted infrastructure, the ongoing cost is limited to server electricity and hardware upkeep, decoupling operational expenditure from transaction volume.

Privacy: Complete data sovereignty. The model operates entirely on bank controlled servers, ensuring customer conversations, names, and transaction details never leave the secure corporate boundary.

Latency: Very low latency. Because instructions, persona rules, and structural schemas are embedded directly in the weights, system prompts remain concise, maximizing generation throughput.

Effort: Substantial initial effort. The team must engineer diverse synthetic datasets, implement rigorous cleaning pipelines, remove potential PII, establish evaluation harnesses, and execute hyperparameter optimization.

Updatability: Very poor for factual knowledge. Banking fees, transaction thresholds, and regulatory turnaround times change periodically. Storing factual figures in model weights causes hallucinations over time and necessitates recurring retraining cycles whenever policies change.

### Approach 4: Fine Tuning Plus RAG Hybrid

The hybrid architecture combines the distinct strengths of supervised fine tuning and retrieval augmentation. The base model is fine tuned on linguistic style, respectful persona, conversation flow, scam refusal behavior, and structured JSON output. A localized RAG pipeline dynamically supplies authoritative figures for fees, limits, product features, and turnaround times during inference.

Quality: Best in class. The model communicates with natural UrduLish fluency, adheres strictly to the persona of Zarya Digital Bank, produces valid JSON tickets, and grounds all policy assertions on authoritative retrieved documents.

Cost: Optimal balance. Model inference runs locally on affordable hardware using quantization techniques. Dynamic context injection is limited to concise factual snippets rather than verbose behavioral instructions.

Privacy: Fully compliant with State Bank of Pakistan regulations. Both the quantized model server and the vector retrieval engine run on the bank private network without external network exposure.

Latency: Fast and predictable. Compact system prompts combined with targeted retrieval snippets allow local serving engines like vLLM to deliver sub second responses.

Effort: High initial engineering effort. The architecture requires both dataset curation for model adaptation and the construction of an enterprise retrieval pipeline.

Updatability: Outstanding. Dynamic banking rules are modified instantly by updating policy documents, while behavioral guardrails and linguistic proficiency remain stable in the model weights.

## 3. Comparative Summary

<table>
<tr>
<th>Metric</th>
<th>Prompt Engineering Only</th>
<th>RAG Only</th>
<th>Fine Tuning Only</th>
<th>Fine Tuning Plus RAG Hybrid</th>
</tr>
<tr>
<td>Quality and Fluency</td>
<td>Moderate, sounds robotic</td>
<td>Good factual ground, unnatural tone</td>
<td>Excellent UrduLish, tone drift rare</td>
<td>Superior fluency, tone, and accuracy</td>
</tr>
<tr>
<td>Cost at Scale</td>
<td>High linear API costs</td>
<td>Moderate API or token costs</td>
<td>Low fixed infrastructure cost</td>
<td>Low fixed infrastructure cost</td>
</tr>
<tr>
<td>Data Privacy</td>
<td>High risk if external API used</td>
<td>Dependent on hosting setup</td>
<td>Complete on premises control</td>
<td>Complete on premises control</td>
</tr>
<tr>
<td>Inference Latency</td>
<td>High due to prompt length</td>
<td>Moderate due to retrieval overhead</td>
<td>Lowest latency and compact prompts</td>
<td>Low latency with focused context</td>
</tr>
<tr>
<td>Engineering Effort</td>
<td>Minimal upfront setup</td>
<td>Moderate vector setup</td>
<td>High training and data curation</td>
<td>Comprehensive implementation</td>
</tr>
<tr>
<td>Ease of Updating</td>
<td>Immediate prompt adjustment</td>
<td>Immediate document re indexing</td>
<td>Requires retraining for new facts</td>
<td>Immediate document re indexing</td>
</tr>
</table>

## 4. Strategic Justification for the Hybrid Approach

The core technical justification for the hybrid architecture rests on the foundational separation between immutable behaviors and mutable facts.

In banking customer support, operational characteristics divide into two distinct categories:

1. Invariant Behaviors: Certain attributes of the assistant must never deviate under any circumstances. These include the polite Zarya Bank persona, respectful language using Ji and aap, asking only one question at a time, strictly refusing to request or accept confidential credentials such as OTP numbers or card PINs, recognizing social engineering attempts, and producing machine readable JSON tickets for ticket escalation. These permanent attributes belong in the model weights through supervised fine tuning.

2. Dynamic Facts: Banking parameters undergo constant operational and regulatory adjustments. Transaction fees, daily Raast limits, international card spending thresholds, foreign exchange markups, and turnaround times for dispute resolution change based on management decisions and central bank directives. Storing these dynamic values in fine tuned model weights leads to catastrophic policy hallucinations and unsustainable retraining schedules. These mutable facts belong exclusively in the dynamic RAG repository.

By fine tuning the model to recognize when a fact is required and grounding its responses strictly in retrieved documents using standardized placeholders during dataset construction, the bank achieves complete behavioral consistency without sacrificing factual agility.

## 5. Defence in Depth: Two Layer Security Architecture

Financial institutions face sophisticated social engineering, phishing campaigns, and adversarial prompt injections designed to defraud customers. A single layer of model level refusal is insufficient to safeguard retail banking clients. Zarya Digital Bank implements a defence in depth framework featuring two complementary security layers.

### Layer One: The Fine Tuned Model Safety Alignment

The primary layer operates within the fine tuned neural network. During supervised fine tuning and preference optimization, the model is trained on hundreds of fraud, scam, and credential harvesting scenarios. The model learns to:

1. Immediately identify requests involving OTP verification, ATM PIN entry, CVV disclosure, or online banking passwords.
2. Refuse to solicit or output sensitive financial identifiers.
3. Automatically set the escalate to human flag to true whenever a fraud or scam attempt is identified.
4. Respond with an informative explanation clarifying that official Zarya Bank personnel will never request one time passwords or security credentials under any circumstance.

Because this protective behavior is reinforced in the internal parameter representations, the model resists basic conversational jailbreaks and topic diversion attempts.

### Layer Two: Deterministic Pre Model Input Guardrail

Even the most robustly aligned language model retains a non zero probability of adversarial exploitation, hallucination under jailbreak prompts, or token generation latency during critical security incidents. Therefore, Layer Two establishes a deterministic input guardrail deployed ahead of the language model in the request pipeline.

When an inbound customer message enters the application gateway, the guardrail performs rapid pattern analysis before the language model receives the prompt:

1. Fast pattern matching and semantic classification scan the customer text for known fraud indicators, such as mentions of suspicious phone calls, unsolicited OTP requests, lottery prizes, SIM swap warnings, or account block threats.
2. If a scam indicator matches high confidence criteria, the guardrail immediately bypasses the language model entirely.
3. The guardrail directly returns a fixed, pre written, compliance approved scam warning: 'Zarya Bank kabhi bhi call ya SMS par aap ka OTP ya PIN nahi maangta. Yeh fraud ho sakta hai. Kisi ko na batayein aur foran helpline par report karein.'
4. Concurrently, the guardrail dispatches an immediate high priority fraud alert to the human security operations queue.

This two layer architecture ensures that even if an attacker crafts an intricate prompt injection intended to deceive the language model, the deterministic guardrail intercepts the threat before model execution. Conversely, if an ambiguous scenario bypasses the guardrail regex, the fine tuned model safety alignment serves as an intelligent second barrier.
