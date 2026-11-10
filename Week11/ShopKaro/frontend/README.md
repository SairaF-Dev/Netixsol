# ShopKaro — Frontend Interfaces

This directory houses the user interfaces for customers, operations teams, and business executives.

---

## Intended Purpose & Architecture

The frontend provides interactive access to the ShopKaro intelligence platform across three primary user personas:

1. **Customer Shopping Portal:**
   - Interactive e-commerce catalog featuring real-time personalized recommendations.
   - Hybrid search interface (lexical + semantic).
   - Conversational UrduLish shopping assistant widget for conversational product discovery in Roman Urdu and English.

2. **Operations & Merchandising Dashboard:**
   - SKU-level demand forecast visualizations and probabilistic uncertainty bands.
   - Inventory intelligence console: real-time stock-out warnings, reorder point (ROP) recommendations, and overstock analysis.

3. **Management & Experimentation Console:**
   - Real-time business KPIs (conversion rates, average order value, cart abandonment).
   - A/B testing dashboard displaying live experiment variant allocations, statistical significance metrics (p-values, confidence intervals), and guardrail indicators.

---

## Technical Stack & Integration

- The frontend consumes backend capabilities strictly through the REST APIs defined in `src/shopkaro/api/`.
- Prototyping may utilize lightweight interactive frameworks (such as Streamlit or Gradio) for rapid validation, before modular web components are integrated.

