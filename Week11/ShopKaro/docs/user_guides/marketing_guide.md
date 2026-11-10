# ShopKaro Marketing & Merchandising Operational Guide

## 1. Audience Segmentation Matrix
ShopKaro automatically clusters customers into 5 distinct behavioral segments via RFM + K-Means:

| Segment Name | Typical Behavior & Basket Size | Recommended Campaign Action | Push Channel |
| :--- | :--- | :--- | :--- |
| **VIP Luxury Buyers** | High monetary spend (>25,000 PKR), low price sensitivity, brand-loyal. | Early access to designer lawn, premium electronics previews, concierge VIP invites. | WhatsApp Concierge / SMS |
| **Eid & Festive Shoppers** | Spikes during Ramadan, Eid-ul-Fitr, Shaadi season; high lawn & apparel interest. | Pre-Chaand Raat countdown campaigns, curated modest 3-piece gift bundles. | In-App Banner & Email |
| **Bargain Hunters** | Sensitive to discounts, high cart abandonment, responds to promo codes. | Flash sales (Up to 40% OFF), limited-time vouchers, COD free shipping vouchers. | Push Notification |
| **Tech & Gadget Seekers** | High AOV, seeks PTA-approved devices, compares specs. | Bundle deals (Phones + Fast Chargers + Cases), installment plans (BNPL). | Search Highlight Rail |
| **Cold-Start New Visitors** | Zero purchase history, exploring trending items. | Showcase Top-5 trending Pakistani lawn, perfumes, and bestsellers with 10% first-order discount. | Homepage Hero Rail |

## 2. Merchandising Levers & Campaign Boosting
Marketing managers can adjust recommendation weights via the API or merchandising rules:
- **Festival Multiplier:** Boost festive categories (e.g., set `Women's Lawn & Unstitched` boost to `1.5x` during Ramadan).
- **Brand Diversity Cap:** Ensures no single designer brand monopolizes the recommendation feed (enforced cap: $\le 2$ items/brand).
- **Clearance Discount Boost:** Automatically elevate slow-moving seasonal inventory with $>20\%$ discounts to clear warehouse space.

