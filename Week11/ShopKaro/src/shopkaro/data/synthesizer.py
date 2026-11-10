"""
Pakistani E-Commerce Context & Synthetic Data Generator for ShopKaro.

Adapts RetailRocket clickstream items and Olist marketplace records to the
Pakistani commerce context (PKR prices, local categories, local brands,
moving Islamic festival calendar, 2-year daily sales history, and multilingual
English / Urdu / Roman Urdu customer reviews).

All generated records carry explicit provenance metadata (`is_synthetic`, `data_source`).
"""

from __future__ import annotations

import re

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from shopkaro.config.settings import settings


# ---------------------------------------------------------------------------
# 1. Pakistani Festival & Seasonal Calendar (2024 - 2026)
#    Note: Islamic hijri dates shift ~10-11 days earlier each Gregorian year.
# ---------------------------------------------------------------------------
PAKISTANI_FESTIVALS: list[dict[str, Any]] = [
    # 2024 Festivals
    {
        "festival_name": "Ramadan",
        "festival_type": "Islamic_Moving",
        "start_date": "2024-03-11",
        "end_date": "2024-04-09",
        "boost_categories": ["Women's Lawn & Unstitched", "Men's Kurta & Ethnic", "Groceries & Staples", "Beauty & Fragrances"],
        "demand_multiplier": 2.6,
    },
    {
        "festival_name": "Chaand Raat & Eid ul Fitr",
        "festival_type": "Islamic_Moving",
        "start_date": "2024-04-01",
        "end_date": "2024-04-13",
        "boost_categories": ["Women's Lawn & Unstitched", "Men's Kurta & Ethnic", "Footwear & Khussa", "Beauty & Fragrances", "Bridal & Formal Wear"],
        "demand_multiplier": 4.2,
    },
    {
        "festival_name": "Eid ul Adha",
        "festival_type": "Islamic_Moving",
        "start_date": "2024-06-08",
        "end_date": "2024-06-20",
        "boost_categories": ["Home & Kitchen Appliances", "Groceries & Staples", "Men's Kurta & Ethnic", "Women's Lawn & Unstitched"],
        "demand_multiplier": 3.1,
    },
    {
        "festival_name": "Azadi Sale (14 August)",
        "festival_type": "National_Fixed",
        "start_date": "2024-08-10",
        "end_date": "2024-08-16",
        "boost_categories": ["Women's Lawn & Unstitched", "Men's Kurta & Ethnic", "Smartphones & Accessories"],
        "demand_multiplier": 2.0,
    },
    {
        "festival_name": "Back to School Season",
        "festival_type": "Seasonal_Fixed",
        "start_date": "2024-08-15",
        "end_date": "2024-09-05",
        "boost_categories": ["Kids & School Supplies", "Footwear & Khussa", "Laptops & Computing"],
        "demand_multiplier": 2.8,
    },
    {
        "festival_name": "11.11 Mega Sale",
        "festival_type": "Commercial_Fixed",
        "start_date": "2024-11-08",
        "end_date": "2024-11-15",
        "boost_categories": ["Smartphones & Accessories", "Laptops & Computing", "Home & Kitchen Appliances", "Beauty & Fragrances"],
        "demand_multiplier": 3.5,
    },
    {
        "festival_name": "Blessed Friday (Black Friday)",
        "festival_type": "Commercial_Fixed",
        "start_date": "2024-11-25",
        "end_date": "2024-12-01",
        "boost_categories": ["Smartphones & Accessories", "Winter Wear & Jackets", "Footwear & Khussa", "Laptops & Computing"],
        "demand_multiplier": 2.9,
    },
    {
        "festival_name": "Wedding & Shaadi Season",
        "festival_type": "Seasonal_Fixed",
        "start_date": "2024-12-05",
        "end_date": "2024-12-28",
        "boost_categories": ["Bridal & Formal Wear", "Beauty & Fragrances", "Footwear & Khussa", "Home & Kitchen Appliances"],
        "demand_multiplier": 2.7,
    },
    # 2025 Festivals (Islamic dates shifted ~11 days earlier!)
    {
        "festival_name": "Ramadan",
        "festival_type": "Islamic_Moving",
        "start_date": "2025-03-01",
        "end_date": "2025-03-29",
        "boost_categories": ["Women's Lawn & Unstitched", "Men's Kurta & Ethnic", "Groceries & Staples", "Beauty & Fragrances"],
        "demand_multiplier": 2.7,
    },
    {
        "festival_name": "Chaand Raat & Eid ul Fitr",
        "festival_type": "Islamic_Moving",
        "start_date": "2025-03-21",
        "end_date": "2025-04-03",
        "boost_categories": ["Women's Lawn & Unstitched", "Men's Kurta & Ethnic", "Footwear & Khussa", "Beauty & Fragrances", "Bridal & Formal Wear"],
        "demand_multiplier": 4.5,
    },
    {
        "festival_name": "Spring Back to School",
        "festival_type": "Seasonal_Fixed",
        "start_date": "2025-03-25",
        "end_date": "2025-04-10",
        "boost_categories": ["Kids & School Supplies", "Footwear & Khussa"],
        "demand_multiplier": 2.4,
    },
    {
        "festival_name": "Eid ul Adha",
        "festival_type": "Islamic_Moving",
        "start_date": "2025-05-28",
        "end_date": "2025-06-10",
        "boost_categories": ["Home & Kitchen Appliances", "Groceries & Staples", "Men's Kurta & Ethnic", "Women's Lawn & Unstitched"],
        "demand_multiplier": 3.2,
    },
    {
        "festival_name": "Azadi Sale (14 August)",
        "festival_type": "National_Fixed",
        "start_date": "2025-08-10",
        "end_date": "2025-08-16",
        "boost_categories": ["Women's Lawn & Unstitched", "Men's Kurta & Ethnic", "Smartphones & Accessories"],
        "demand_multiplier": 2.1,
    },
    {
        "festival_name": "Back to School Season",
        "festival_type": "Seasonal_Fixed",
        "start_date": "2025-08-15",
        "end_date": "2025-09-05",
        "boost_categories": ["Kids & School Supplies", "Footwear & Khussa", "Laptops & Computing"],
        "demand_multiplier": 2.9,
    },
    {
        "festival_name": "11.11 Mega Sale",
        "festival_type": "Commercial_Fixed",
        "start_date": "2025-11-08",
        "end_date": "2025-11-15",
        "boost_categories": ["Smartphones & Accessories", "Laptops & Computing", "Home & Kitchen Appliances", "Beauty & Fragrances"],
        "demand_multiplier": 3.7,
    },
    {
        "festival_name": "Blessed Friday (Black Friday)",
        "festival_type": "Commercial_Fixed",
        "start_date": "2025-11-24",
        "end_date": "2025-11-30",
        "boost_categories": ["Smartphones & Accessories", "Winter Wear & Jackets", "Footwear & Khussa", "Laptops & Computing"],
        "demand_multiplier": 3.0,
    },
    {
        "festival_name": "Wedding & Shaadi Season",
        "festival_type": "Seasonal_Fixed",
        "start_date": "2025-12-05",
        "end_date": "2025-12-28",
        "boost_categories": ["Bridal & Formal Wear", "Beauty & Fragrances", "Footwear & Khussa", "Home & Kitchen Appliances"],
        "demand_multiplier": 2.8,
    },
]


# ---------------------------------------------------------------------------
# 2. Pakistani Category Taxonomy & Catalogue Templates
# ---------------------------------------------------------------------------
CATEGORY_TEMPLATES: dict[str, dict[str, Any]] = {
    "Women's Lawn & Unstitched": {
        "brands": ["Khaadi", "Sapphire", "Gul Ahmed", "Alkaram Studio", "Nishat Linen", "Sana Safinaz", "Limelight", "Beechtree"],
        "sub_categories": ["3-Piece Lawn Suit", "2-Piece Printed Lawn", "Embroidered Eid Lawn", "Chiffon Dupatta Suit", "Embroidered Shawl"],
        "colors": ["Emerald Green", "Pastel Pink", "Mustard Yellow", "Sky Blue", "Maroon", "Ivory White", "Black", "Teal"],
        "occasions": ["Eid", "Summer", "Casual/Daily", "Semi-Formal"],
        "price_range": (1800, 9500),
        "margin_range": (0.28, 0.48),
        "urdu_keywords": "eid ke liye lawn suit kapra unstitched 3 piece suit ammi gift",
        "title_templates": [
            "{brand} {sub_cat} in {color} — Eid Festive Collection",
            "{brand} Luxury {sub_cat} ({color}) with Printed Dupatta",
            "{brand} Summer {sub_cat} {color} — Unstitched Lawn Kapra",
        ],
        "desc_templates": [
            "Premium breathable {sub_cat} by {brand} in {color}. Ideal for {occasion} wear and summer heat. Includes unstitched shirt fabric, dyed trouser, and dupatta. Keywords: {urdu_kw}.",
            "Authentic {brand} {sub_cat} crafted with fine Pakistani cotton lawn in {color}. Perfect for {occasion} gatherings and gifting. Keywords: {urdu_kw}.",
        ],
    },
    "Men's Kurta & Ethnic": {
        "brands": ["J. Junaid Jamshed", "Gul Ahmed Men", "Almirah", "MTJ", "Khaadi Man", "Bonanza Satrangi", "Edenrobe"],
        "sub_categories": ["Cotton Embroidered Kurta", "Wash & Wear Shalwar Kameez", "Festive Waistcoat", "Boski Silk Kurta"],
        "colors": ["Navy Blue", "Crisp White", "Charcoal Grey", "Olive Green", "Black", "Beige", "Maroon"],
        "occasions": ["Eid", "Jummah/Festive", "Shaadi/Wedding", "Casual/Daily"],
        "price_range": (2200, 12000),
        "margin_range": (0.30, 0.50),
        "urdu_keywords": "mardana kurta shalwar kameez eid ke liye kapre waistcoat",
        "title_templates": [
            "{brand} {color} {sub_cat} — Eid & Jummah Special",
            "{brand} Classic {sub_cat} in {color} (Stitched)",
        ],
        "desc_templates": [
            "Stitched {sub_cat} by {brand} in {color}. Tailored regular fit designed for {occasion} occasions across Pakistan. Keywords: {urdu_kw}.",
        ],
    },
    "Bridal & Formal Wear": {
        "brands": ["Maria B", "Asim Jofa", "Baroque", "Qalamkar", "Zaha", "Elan Studio", "Republic Womenswear"],
        "sub_categories": ["Bridal Embroidered Lehenga", "Shaadi Maxi Dress", "Zari Gharara Suit", "Velvet Formal Shawl"],
        "colors": ["Crimson Red", "Deep Maroon", "Royal Gold", "Emerald Green", "Dusty Rose", "Champagne"],
        "occasions": ["Shaadi/Wedding", "Bridal/Barat", "Walima", "Eid"],
        "price_range": (8500, 48000),
        "margin_range": (0.35, 0.55),
        "urdu_keywords": "shaadi ke liye red lehenga maxi dulhan dress barat walima",
        "title_templates": [
            "{brand} {color} {sub_cat} — Shaadi & Wedding Collection",
            "{brand} Hand-Embellished {sub_cat} ({color}) for Barat & Walima",
        ],
        "desc_templates": [
            "Exquisite {sub_cat} by {brand} in {color} featuring zari, tilla, and sequin work. Designed for {occasion} celebrations. Keywords: {urdu_kw}.",
        ],
    },
    "Footwear & Khussa": {
        "brands": ["Bata", "Servis", "Ndure", "Stylo", "Borjan", "ECS", "Chapter 13", "Insignia"],
        "sub_categories": ["Traditional Punjabi Khussa", "Running Sneakers", "School Uniform Shoes", "Festive Block Heels", "Peshawari Chappal"],
        "colors": ["Black", "Tan Brown", "Golden", "White", "Silver", "Burgundy"],
        "occasions": ["Casual/Daily", "Eid", "School/Office", "Shaadi/Wedding"],
        "price_range": (1200, 8500),
        "margin_range": (0.25, 0.45),
        "urdu_keywords": "joota juta shoes chappal khussa sandals bachon ke school shoes",
        "title_templates": [
            "{brand} {color} {sub_cat} — Comfortable Daily & {occasion} Joota",
            "{brand} Durable {sub_cat} in {color}",
        ],
        "desc_templates": [
            "High-comfort {sub_cat} from {brand} in {color}. Cushioned sole suitable for {occasion}. Roman Urdu search tags: {urdu_kw}.",
        ],
    },
    "Smartphones & Accessories": {
        "brands": ["Samsung", "Infinix", "Xiaomi Redmi", "Tecno", "Vivo", "Realme", "Anker", "Baseus", "Audionic"],
        "sub_categories": ["5G Smartphone", "Fast Charger 45W", "Silicone Back Cover", "Wireless Earbuds", "Power Bank 20000mAh"],
        "colors": ["Phantom Black", "Titanium Grey", "Ocean Blue", "Mint Green", "White"],
        "occasions": ["All-Season", "11.11 Sale", "Gift"],
        "price_range": (850, 145000),
        "margin_range": (0.12, 0.35),
        "urdu_keywords": "mobile phone samsung galaxy cover charger earbuds sasta phone PTA approved",
        "title_templates": [
            "{brand} {sub_cat} ({color}) — Official PTA Approved Warranty",
            "{brand} Original {sub_cat} in {color} with Fast Charging",
        ],
        "desc_templates": [
            "Genuine {brand} {sub_cat} in {color}. Official Pakistani warranty. Popular choice during {occasion}. Keywords: {urdu_kw}.",
        ],
    },
    "Laptops & Computing": {
        "brands": ["HP", "Lenovo", "Dell", "Asus", "Acer", "Apple", "Logitech"],
        "sub_categories": ["Core i5 Coding Laptop 16GB RAM", "Ryzen 7 Programming Laptop", "Student Notebook SSD", "Mechanical Gaming Keyboard", "Wireless Mouse"],
        "colors": ["Silver", "Matte Black", "Space Grey"],
        "occasions": ["School/Office", "11.11 Sale", "All-Season"],
        "price_range": (2500, 220000),
        "margin_range": (0.10, 0.25),
        "urdu_keywords": "laptop for coding programming university student computer under 1.5 lac",
        "title_templates": [
            "{brand} {sub_cat} ({color}) — Full HD Display for Coding & Study",
            "{brand} High-Performance {sub_cat} in {color}",
        ],
        "desc_templates": [
            "Reliable {brand} {sub_cat} in {color}. Equipped with fast NVMe SSD and multi-core processor ideal for software coding, university projects, and freelancing. Keywords: {urdu_kw}.",
        ],
    },
    "Kids & School Supplies": {
        "brands": ["Bata School", "Polo Kids", "Dollar", "Pelikan", "Minnie Kids", "Outfitter Junior", "Oxford"],
        "sub_categories": ["Waterproof Ergonomic School Bag", "Kids Cartoon Backpack", "Lunch Box & Water Bottle Set", "Complete Geometry & Stationery Kit"],
        "colors": ["Navy Blue", "Pink", "Red", "Royal Blue", "Black"],
        "occasions": ["School/Office", "Back to School", "All-Season"],
        "price_range": (650, 4800),
        "margin_range": (0.28, 0.46),
        "urdu_keywords": "bachon ke liye school bag basta bottle lunch box stationery",
        "title_templates": [
            "{brand} {sub_cat} in {color} — Bachon ke Liye Durable School Bag",
            "{brand} Kids {sub_cat} ({color}) — Back to School Special",
        ],
        "desc_templates": [
            "Heavy-duty padded {sub_cat} by {brand} in {color}. Designed for Pakistani school children with spacious compartments. Keywords: {urdu_kw}.",
        ],
    },
    "Beauty & Fragrances": {
        "brands": ["J. Fragrances", "Saeed Ghani", "Hemani", "WB by Hemani", "Bonanza Perfumes", "Conatural", "Maybelline", "Rivaj UK"],
        "sub_categories": ["Oud & Attar Perfume Gift Set", "Luxury Eau De Parfum", "Herbal Skincare Facial Kit", "Halal Matte Lipstick Set", "Rose Water Toner"],
        "colors": ["Gold", "Rose Pink", "Amber", "Clear"],
        "occasions": ["Eid", "Gift", "Shaadi/Wedding", "All-Season"],
        "price_range": (550, 6500),
        "margin_range": (0.35, 0.60),
        "urdu_keywords": "perfume attar khushboo makeup gift set ammi ke liye eid gift",
        "title_templates": [
            "{brand} {sub_cat} — Best for Eid Gift & Shaadi Season",
            "{brand} Signature {sub_cat} ({color} Edition)",
        ],
        "desc_templates": [
            "Long-lasting {sub_cat} from {brand}. A thoughtful gift for Ammi, family, and festive Eid occasions. Keywords: {urdu_kw}.",
        ],
    },
    "Home & Kitchen Appliances": {
        "brands": ["Dawlance", "Haier", "Pel", "Westpoint", "Anex", "Philips", "Kenwood", "Boss"],
        "sub_categories": ["Food Processor & Juicer Blender", "Air Fryer 5L", "Microwave Oven", "Electric Kettle", "Steam Iron"],
        "colors": ["Stainless Steel", "Black", "White", "Silver"],
        "occasions": ["Eid ul Adha", "11.11 Sale", "Shaadi/Wedding", "All-Season"],
        "price_range": (3200, 65000),
        "margin_range": (0.18, 0.34),
        "urdu_keywords": "kitchen blender juicer iron استری air fryer ghar ka saman",
        "title_templates": [
            "{brand} {sub_cat} ({color}) — Energy Saver Official Warranty",
            "{brand} Heavy-Duty {sub_cat} for Modern Pakistani Kitchens",
        ],
        "desc_templates": [
            "Official {brand} {sub_cat} in {color} with copper motor and 1-year warranty. Essential for Ramadan & Eid ul Adha preparation. Keywords: {urdu_kw}.",
        ],
    },
    "Groceries & Staples": {
        "brands": ["Shan Foods", "National Foods", "Tapal Danedar", "Dalda", "Sufi", "Guard Basmati", "Rooh Afza", "Mitchell's"],
        "sub_categories": ["Super Kernel Basmati Rice 5kg", "Biryani & Qorma Masala Value Pack", "Danedar Family Mixture Tea 900g", "Ramadan Iftar Rooh Afza & Dates Pack", "Pure Cooking Oil 5L"],
        "colors": ["Standard Pack", "Family Pack", "Jumbo Pack"],
        "occasions": ["Ramadan", "Eid ul Adha", "Casual/Daily"],
        "price_range": (350, 4200),
        "margin_range": (0.10, 0.22),
        "urdu_keywords": "rashan chawal patti masala oil rooh afza ramzan iftar",
        "title_templates": [
            "{brand} {sub_cat} ({color}) — Fresh Monthly Rashan Saver",
            "{brand} {sub_cat} — Ramadan & Daily Kitchen Essential",
        ],
        "desc_templates": [
            "100% pure and fresh {sub_cat} by {brand}. Ideal for daily household cooking, Ramadan Iftar, and Eid dawat. Keywords: {urdu_kw}.",
        ],
    },
    "Winter Wear & Jackets": {
        "brands": ["Outfitters", "Breakout", "Charcoal", "Cougar", "Engine", "Diners", "Lama"],
        "sub_categories": ["Puffer Winter Jacket", "Woolen Kashmiri Shawl", "Fleece Hoodie", "Men's Leather Jacket"],
        "colors": ["Black", "Olive Green", "Navy Blue", "Camel Brown", "Grey"],
        "occasions": ["Winter", "Blessed Friday"],
        "price_range": (2800, 14500),
        "margin_range": (0.32, 0.52),
        "urdu_keywords": "sardi ke kapre winter jacket sweater hoodie گرم شال",
        "title_templates": [
            "{brand} {color} {sub_cat} — Warm Winter Collection",
            "{brand} Premium {sub_cat} in {color}",
        ],
        "desc_templates": [
            "Warm thermal-insulated {sub_cat} by {brand} in {color}. Built for northern trips and chilly winter evenings. Keywords: {urdu_kw}.",
        ],
    },
}


# Curated Hero Products to guarantee exact matches for all Capstone Demo Scenarios
CURATED_HERO_PRODUCTS: list[dict[str, Any]] = [
    # Scenario 1: "eid ke liye lawn suit under 5000"
    {
        "title": "Sapphire 3-Piece Unstitched Embroidered Lawn Suit in Emerald Green — Eid Collection",
        "category": "Women's Lawn & Unstitched",
        "sub_category": "3-Piece Lawn Suit",
        "brand": "Sapphire",
        "color": "Emerald Green",
        "occasion": "Eid",
        "price_pkr": 4450.0,
        "on_sale": True,
        "discount_pct": 15.0,
        "margin_pct": 0.42,
        "stock_qty": 140,
        "description": "Festive 3-piece unstitched Pakistani cotton lawn suit by Sapphire in Emerald Green with chiffon dupatta. Ideal for Eid ul Fitr under 5000 PKR. Tags: eid ke liye lawn suit under 5000 kapra.",
    },
    {
        "title": "Khaadi Festive 3-Piece Printed Lawn Suit in Pastel Pink — Eid Special",
        "category": "Women's Lawn & Unstitched",
        "sub_category": "3-Piece Lawn Suit",
        "brand": "Khaadi",
        "color": "Pastel Pink",
        "occasion": "Eid",
        "price_pkr": 3890.0,
        "on_sale": True,
        "discount_pct": 10.0,
        "margin_pct": 0.40,
        "stock_qty": 95,
        "description": "Breathable summer 3-piece lawn suit by Khaadi in Pastel Pink. Designed for Eid celebrations at an affordable budget under 5000 PKR. Tags: eid ke liye lawn suit under 5000.",
    },
    {
        "title": "Gul Ahmed Tribute Embroidered Lawn Suit in Mustard Yellow — Eid Edition",
        "category": "Women's Lawn & Unstitched",
        "sub_category": "Embroidered Eid Lawn",
        "brand": "Gul Ahmed",
        "color": "Mustard Yellow",
        "occasion": "Eid",
        "price_pkr": 4750.0,
        "on_sale": False,
        "discount_pct": 0.0,
        "margin_pct": 0.45,
        "stock_qty": 110,
        "description": "Original Gul Ahmed unstitched embroidered lawn suit with lawn dupatta in Mustard Yellow. Best seller for Ramadan and Eid under 5000. Tags: eid ke liye lawn suit under 5000.",
    },
    # Scenario 2: "bachon ke liye school bag"
    {
        "title": "Polo Kids Waterproof Ergonomic School Bag in Navy Blue — Bachon ke Liye",
        "category": "Kids & School Supplies",
        "sub_category": "Waterproof Ergonomic School Bag",
        "brand": "Polo Kids",
        "color": "Navy Blue",
        "occasion": "School/Office",
        "price_pkr": 2150.0,
        "on_sale": True,
        "discount_pct": 12.0,
        "margin_pct": 0.38,
        "stock_qty": 180,
        "description": "Durable waterproof backpack with padded shoulder straps for primary and high school students. Tags: bachon ke liye school bag basta kids backpack.",
    },
    {
        "title": "Bata School Heavy-Duty Kids Backpack with Lunch Box Compartment (Red)",
        "category": "Kids & School Supplies",
        "sub_category": "Waterproof Ergonomic School Bag",
        "brand": "Bata School",
        "color": "Red",
        "occasion": "School/Office",
        "price_pkr": 1850.0,
        "on_sale": False,
        "discount_pct": 0.0,
        "margin_pct": 0.35,
        "stock_qty": 130,
        "description": "Lightweight ergonomic kids school bag with bottle holder and multiple compartments. Tags: bachon ke liye school bag basta.",
    },
    # Scenario 3: "shaadi ke liye red lehenga 20 hazaar tak"
    {
        "title": "Maria B Crimson Red Bridal Embroidered Lehenga Choli — Shaadi Collection",
        "category": "Bridal & Formal Wear",
        "sub_category": "Bridal Embroidered Lehenga",
        "brand": "Maria B",
        "color": "Crimson Red",
        "occasion": "Shaadi/Wedding",
        "price_pkr": 18500.0,
        "on_sale": True,
        "discount_pct": 10.0,
        "margin_pct": 0.48,
        "stock_qty": 25,
        "description": "Luxury Crimson Red wedding lehenga with zari and tilla embroidery under 20,000 PKR. Ideal for Shaadi, Barat, and Mehndi events. Tags: shaadi ke liye red lehenga 20 hazaar tak.",
    },
    {
        "title": "Asim Jofa Festive Deep Red Zari Lehenga & Organza Dupatta",
        "category": "Bridal & Formal Wear",
        "sub_category": "Bridal Embroidered Lehenga",
        "brand": "Asim Jofa",
        "color": "Crimson Red",
        "occasion": "Shaadi/Wedding",
        "price_pkr": 19200.0,
        "on_sale": False,
        "discount_pct": 0.0,
        "margin_pct": 0.50,
        "stock_qty": 18,
        "description": "Hand-embellished red party and wedding lehenga suit priced under 20 hazaar PKR. Tags: shaadi ke liye red lehenga 20 hazaar tak.",
    },
    # Scenario 4: "laptop for coding under 1.5 lac"
    {
        "title": "Lenovo ThinkBook 15 Core i5 12th Gen Coding Laptop (16GB RAM, 512GB SSD)",
        "category": "Laptops & Computing",
        "sub_category": "Core i5 Coding Laptop 16GB RAM",
        "brand": "Lenovo",
        "color": "Space Grey",
        "occasion": "School/Office",
        "price_pkr": 138000.0,
        "on_sale": True,
        "discount_pct": 8.0,
        "margin_pct": 0.16,
        "stock_qty": 32,
        "description": "High-speed programming and software engineering laptop with 16GB DDR4 RAM, 512GB NVMe SSD, and backlit keyboard under 1.5 lac (150,000 PKR). Tags: laptop for coding under 1.5 lac programming.",
    },
    {
        "title": "HP ProBook 450 G9 Core i5 Coding & University Laptop (16GB RAM, 512GB SSD)",
        "category": "Laptops & Computing",
        "sub_category": "Core i5 Coding Laptop 16GB RAM",
        "brand": "HP",
        "color": "Silver",
        "occasion": "School/Office",
        "price_pkr": 144500.0,
        "on_sale": False,
        "discount_pct": 0.0,
        "margin_pct": 0.15,
        "stock_qty": 24,
        "description": "Reliable HP ProBook for CS students, web developers, and data science coding workflows under 1.5 lac PKR. Tags: laptop for coding under 1.5 lac.",
    },
    # Scenario 5: "Ammi ke liye Eid gift chahiye, 3000 tak"
    {
        "title": "Khaadi Luxury Embroidered Shawl in Ivory White — Ammi Eid Gift Edition",
        "category": "Women's Lawn & Unstitched",
        "sub_category": "Embroidered Shawl",
        "brand": "Khaadi",
        "color": "Ivory White",
        "occasion": "Eid",
        "price_pkr": 2450.0,
        "on_sale": True,
        "discount_pct": 15.0,
        "margin_pct": 0.44,
        "stock_qty": 75,
        "description": "Khoobsurat soft embroidered shawl in Ivory White. Best Eid gift for Ammi and mothers under 3000 PKR. Tags: ammi ke liye eid gift chahiye 3000 tak shawl.",
    },
    {
        "title": "J. Junaid Jamshed Oud & Rose Perfume Gift Set — Festive Edition",
        "category": "Beauty & Fragrances",
        "sub_category": "Oud & Attar Perfume Gift Set",
        "brand": "J. Fragrances",
        "color": "Gold",
        "occasion": "Eid",
        "price_pkr": 2800.0,
        "on_sale": False,
        "discount_pct": 0.0,
        "margin_pct": 0.52,
        "stock_qty": 90,
        "description": "Elegant non-alcoholic attar and perfume gift box by J. Ideal Eid present for Ammi under 3000 PKR. Tags: ammi ke liye eid gift chahiye 3000 tak perfume gift set.",
    },
    {
        "title": "Saeed Ghani Herbal Skincare & Rose Water Luxury Gift Basket",
        "category": "Beauty & Fragrances",
        "sub_category": "Herbal Skincare Facial Kit",
        "brand": "Saeed Ghani",
        "color": "Rose Pink",
        "occasion": "Eid",
        "price_pkr": 2250.0,
        "on_sale": True,
        "discount_pct": 10.0,
        "margin_pct": 0.48,
        "stock_qty": 110,
        "description": "Natural organic skincare gift set perfect for Ammi on Eid under 3000 PKR. Tags: ammi ke liye eid gift chahiye 3000 tak.",
    },
    # Scenario 6: Samsung Galaxy + Covers + Chargers (Frequently Bought Together)
    {
        "title": "Samsung Galaxy A55 5G (8GB/256GB) Awesome Navy — Official PTA Approved",
        "category": "Smartphones & Accessories",
        "sub_category": "5G Smartphone",
        "brand": "Samsung",
        "color": "Phantom Black",
        "occasion": "11.11 Sale",
        "price_pkr": 119999.0,
        "on_sale": True,
        "discount_pct": 5.0,
        "margin_pct": 0.14,
        "stock_qty": 45,
        "description": "Official PTA approved Samsung Galaxy A55 5G smartphone with Super AMOLED display. Frequently bought with Samsung 45W Fast Charger and Silicone Back Cover.",
    },
    {
        "title": "Samsung Original 45W Super Fast USB-C Wall Charger Adapter",
        "category": "Smartphones & Accessories",
        "sub_category": "Fast Charger 45W",
        "brand": "Samsung",
        "color": "Phantom Black",
        "occasion": "All-Season",
        "price_pkr": 4200.0,
        "on_sale": False,
        "discount_pct": 0.0,
        "margin_pct": 0.35,
        "stock_qty": 200,
        "description": "Original 45W PD fast charger compatible with Samsung Galaxy smartphones.",
    },
    {
        "title": "Baseus Shockproof MagSafe Silicone Back Cover for Samsung Galaxy",
        "category": "Smartphones & Accessories",
        "sub_category": "Silicone Back Cover",
        "brand": "Baseus",
        "color": "Phantom Black",
        "occasion": "All-Season",
        "price_pkr": 1450.0,
        "on_sale": True,
        "discount_pct": 10.0,
        "margin_pct": 0.48,
        "stock_qty": 260,
        "description": "Premium shockproof protective phone case cover for Samsung Galaxy series.",
    },
]


_REPEATED_WORD = re.compile(r"\b(\w+)(?:\s+\1\b)+", re.IGNORECASE)


def collapse_repeated_words(text: str) -> str:
    """'Polo Kids Kids Cartoon Backpack' -> 'Polo Kids Cartoon Backpack' (brand + template + sub-category overlap)."""
    return _REPEATED_WORD.sub(r"\1", text)


def _classify_price_band(price_pkr: float) -> str:
    if price_pkr < 2000:
        return "Budget (<2k PKR)"
    if price_pkr <= 5000:
        return "Mid-Range (2k-5k PKR)"
    if price_pkr <= 25000:
        return "Premium (5k-25k PKR)"
    return "Luxury (>25k PKR)"


def generate_festival_calendar(output_dir: Path | None = None) -> pd.DataFrame:
    """Build both event-level and daily expanded festival calendar tables."""
    out = output_dir or settings.synthetic_dir
    out.mkdir(parents=True, exist_ok=True)

    records = []
    for idx, fest in enumerate(PAKISTANI_FESTIVALS, start=1):
        records.append(
            {
                "festival_id": idx,
                "festival_name": fest["festival_name"],
                "festival_type": fest["festival_type"],
                "start_date": pd.to_datetime(fest["start_date"]).date(),
                "end_date": pd.to_datetime(fest["end_date"]).date(),
                "boost_categories": ", ".join(fest["boost_categories"]),
                "demand_multiplier": float(fest["demand_multiplier"]),
                "is_synthetic": True,
                "data_source": "ShopKaro_Pakistani_Calendar",
            }
        )

    df = pd.DataFrame(records)
    df.to_parquet(out / "festival_calendar.parquet", index=False)
    return df


CATEGORY_WEIGHTS = np.array([0.22, 0.12, 0.06, 0.11, 0.14, 0.05, 0.07, 0.09, 0.06, 0.05, 0.03])


def generate_product_catalogue(
    active_item_ids: list[int],
    olist_product_ids: list[str] | None = None,
    output_dir: Path | None = None,
    seed: int = 42,
    item_categories: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Generate a rich Pakistani Product Catalogue mapped deterministically to
    active RetailRocket `itemid`s and Olist `product_id`s.

    `item_categories` (from `shopkaro.data.category_mapping.map_items_to_categories`) gives each
    item a Pakistani category derived from its real RetailRocket category, so items shoppers browse
    together share sensible categories. Without it, categories are drawn at random (legacy behaviour,
    which makes co-occurrence patterns meaningless to a human).
    """
    out = output_dir or settings.synthetic_dir
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)

    categories = list(CATEGORY_TEMPLATES.keys())
    # Weight categories realistically for a Pakistani marketplace (Fashion & Mobile heavy)
    cat_weights = CATEGORY_WEIGHTS / CATEGORY_WEIGHTS.sum()

    mapped: dict[int, dict[str, Any]] = {}
    if item_categories is not None:
        mapped = item_categories.set_index("raw_itemid").to_dict("index")
        # Each hero product takes the most active item already mapped to the hero's category, and
        # heroes keep codes SK-00001..SK-000NN. Remaining items keep their activity order.
        used: set[int] = set()
        hero_items: list[int] = []
        for hero in CURATED_HERO_PRODUCTS:
            pick = next(
                (i for i in active_item_ids if i not in used and mapped.get(int(i), {}).get("category") == hero["category"]),
                None,
            )
            if pick is None:
                raise ValueError(f"No item mapped to hero category {hero['category']!r}")
            used.add(pick)
            hero_items.append(pick)
        active_item_ids = hero_items + [i for i in active_item_ids if i not in used]

    n_items = len(active_item_ids)
    olist_ids = olist_product_ids or []
    n_olist = len(olist_ids)

    rows: list[dict[str, Any]] = []

    # 1. Assign curated hero products to the top most-interacted item IDs
    for idx, item_id in enumerate(active_item_ids):
        product_code = f"SK-{idx + 1:05d}"
        olist_pid = olist_ids[idx % n_olist] if n_olist > 0 else f"olist_{idx:05d}"

        if idx < len(CURATED_HERO_PRODUCTS):
            hero = CURATED_HERO_PRODUCTS[idx]
            price_pkr = float(hero["price_pkr"])
            stock_qty = int(hero["stock_qty"])
            rows.append(
                {
                    "product_id": product_code,
                    "raw_itemid": int(item_id),
                    "olist_product_id": olist_pid,
                    "title": hero["title"],
                    "description": hero["description"],
                    "category": hero["category"],
                    "sub_category": hero["sub_category"],
                    "brand": hero["brand"],
                    "color": hero["color"],
                    "occasion": hero["occasion"],
                    "price_pkr": price_pkr,
                    "price_band": _classify_price_band(price_pkr),
                    "on_sale": bool(hero["on_sale"]),
                    "discount_pct": float(hero["discount_pct"]),
                    "margin_pct": float(hero["margin_pct"]),
                    "stock_qty": stock_qty,
                    "in_stock": stock_qty > 0,
                    "lead_time_days": int(rng.integers(3, 10)),
                    "rr_categoryid": mapped.get(int(item_id), {}).get("rr_categoryid"),
                    "category_source": "curated_hero",
                    "is_curated_hero": True,
                    "is_synthetic": True,
                    "data_source": "RetailRocket+Olist_Pakistani_Adapted",
                }
            )
            continue

        # 2. Generate structured Pakistani catalogue records for remaining active items
        if mapped:
            cat = str(mapped[int(item_id)]["category"])
            cat_source = str(mapped[int(item_id)]["category_source"])
        else:
            cat = str(rng.choice(categories, p=cat_weights))
            cat_source = "random_legacy"
        tmpl = CATEGORY_TEMPLATES[cat]
        brand = str(rng.choice(tmpl["brands"]))
        sub_cat = str(rng.choice(tmpl["sub_categories"]))
        color = str(rng.choice(tmpl["colors"]))
        occasion = str(rng.choice(tmpl["occasions"]))

        low_p, high_p = tmpl["price_range"]
        # Round price to realistic Pakistani retail endings (e.g., 50 or 99)
        raw_price = float(rng.uniform(low_p, high_p))
        price_pkr = round(raw_price / 50.0) * 50.0

        low_m, high_m = tmpl["margin_range"]
        margin_pct = round(float(rng.uniform(low_m, high_m)), 3)

        on_sale = bool(rng.random() < 0.25)
        discount_pct = float(rng.choice([5.0, 10.0, 15.0, 20.0, 25.0])) if on_sale else 0.0

        # 6% of products are out-of-stock to test Day 2 & Day 3 out-of-stock handling
        if rng.random() < 0.06:
            stock_qty = 0
        else:
            stock_qty = int(rng.integers(5, 250))

        title_fmt = str(rng.choice(tmpl["title_templates"]))
        desc_fmt = str(rng.choice(tmpl["desc_templates"]))

        title = collapse_repeated_words(
            title_fmt.format(brand=brand, sub_cat=sub_cat, color=color, occasion=occasion)
        )
        description = desc_fmt.format(
            brand=brand,
            sub_cat=sub_cat,
            color=color,
            occasion=occasion,
            urdu_kw=tmpl["urdu_keywords"],
        )

        rows.append(
            {
                "product_id": product_code,
                "raw_itemid": int(item_id),
                "olist_product_id": olist_pid,
                "title": title,
                "description": description,
                "category": cat,
                "sub_category": sub_cat,
                "brand": brand,
                "color": color,
                "occasion": occasion,
                "price_pkr": price_pkr,
                "price_band": _classify_price_band(price_pkr),
                "on_sale": on_sale,
                "discount_pct": discount_pct,
                "margin_pct": margin_pct,
                "stock_qty": stock_qty,
                "in_stock": stock_qty > 0,
                "lead_time_days": int(rng.integers(3, 12)),
                "rr_categoryid": mapped.get(int(item_id), {}).get("rr_categoryid"),
                "category_source": cat_source,
                "is_curated_hero": False,
                "is_synthetic": True,
                "data_source": "RetailRocket+Olist_Pakistani_Adapted",
            }
        )

    catalogue_df = pd.DataFrame(rows)
    catalogue_df["rr_categoryid"] = pd.array(
        [None if pd.isna(v) else int(v) for v in catalogue_df["rr_categoryid"]], dtype="Int64"
    )
    catalogue_df.to_parquet(out / "product_catalogue.parquet", index=False)
    return catalogue_df


def generate_daily_sales_history(
    catalogue_df: pd.DataFrame,
    festival_df: pd.DataFrame,
    top_n_products: int = 300,
    start_date: str = "2024-01-01",
    end_date: str = "2025-12-31",
    output_dir: Path | None = None,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate 2 full years (731 days) of daily product sales incorporating:
    - Product velocity tiers (Fast movers, Steady movers, Slow/Intermittent movers)
    - Weekly seasonality (Friday/Weekend surges)
    - Yearly climate seasonality (Summer lawn peak vs Winter jacket peak)
    - Moving Islamic festival surges (Ramadan, Eid ul Fitr, Eid ul Adha) + 11.11 & Back-to-School
    """
    out = output_dir or settings.synthetic_dir
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)

    selected = catalogue_df.head(min(top_n_products, len(catalogue_df))).copy()
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    n_days = len(dates)

    # Precompute date-level calendar features & active festivals per date
    day_of_week = dates.day_of_week.to_numpy()  # 0=Mon .. 6=Sun
    day_of_year = dates.day_of_year.to_numpy()
    month = dates.month.to_numpy()

    # Weekly multiplier: Fri (4), Sat (5), Sun (6) have higher online shopping traffic
    weekly_mult = np.where(day_of_week == 4, 1.25, np.where(day_of_week >= 5, 1.35, 0.92))

    # Build a lookup of (date, category) -> festival multiplier and festival name
    fest_records = festival_df.to_dict("records")

    all_frames: list[pd.DataFrame] = []

    for idx, prod in selected.iterrows():
        pid = prod["product_id"]
        cat = prod["category"]
        price = float(prod["price_pkr"])

        # Assign velocity tier:
        # Top 25% fast movers, middle 50% steady movers, bottom 25% intermittent/slow movers
        rank_ratio = idx / max(len(selected), 1)
        if rank_ratio < 0.25:
            velocity_tier = "Fast_Mover"
            base_rate = float(rng.uniform(14.0, 35.0))
        elif rank_ratio < 0.75:
            velocity_tier = "Steady_Mover"
            base_rate = float(rng.uniform(4.0, 13.0))
        else:
            velocity_tier = "Slow_Intermittent"
            base_rate = float(rng.uniform(0.3, 2.2))

        # Slight upward secular growth trend over 2 years (+15%)
        trend = np.linspace(1.0, 1.18, n_days)

        # Yearly seasonal wave based on category
        if cat == "Women's Lawn & Unstitched":
            # Peaks in Spring/Summer (Mar-Jul), low in Dec-Jan
            seasonal = 1.0 + 0.55 * np.sin(2 * np.pi * (day_of_year - 60) / 365.25)
        elif cat == "Winter Wear & Jackets":
            # Peaks in Nov-Jan, near-zero in May-Aug (matches the Capstone scenario!)
            seasonal = np.where(
                np.isin(month, [11, 12, 1, 2]),
                2.4,
                0.08,
            )
        else:
            seasonal = 1.0 + 0.18 * np.sin(2 * np.pi * (day_of_year - 90) / 365.25)

        # Festival multiplier array
        fest_mult = np.ones(n_days, dtype=float)
        fest_names = np.full(n_days, "Regular_Day", dtype=object)

        for fest in fest_records:
            f_start = pd.Timestamp(fest["start_date"])
            f_end = pd.Timestamp(fest["end_date"])
            boost_cats = [c.strip() for c in fest["boost_categories"].split(",")]
            mask = (dates >= f_start) & (dates <= f_end)
            if mask.any():
                fest_names[mask] = fest["festival_name"]
                if cat in boost_cats:
                    fest_mult[mask] = np.maximum(fest_mult[mask], float(fest["demand_multiplier"]))
                else:
                    fest_mult[mask] = np.maximum(fest_mult[mask], 1.15)

        expected_lambda = np.maximum(0.05, base_rate * trend * weekly_mult * seasonal * fest_mult)

        if velocity_tier == "Slow_Intermittent":
            # Zero-inflated Poisson for intermittent demand
            active_day = rng.random(n_days) < 0.35
            units_sold = rng.poisson(expected_lambda) * active_day
        else:
            # Overdispersed Poisson / Negative Binomial approximation
            noise = rng.gamma(shape=10.0, scale=0.1, size=n_days)
            units_sold = rng.poisson(expected_lambda * noise)

        revenue_pkr = units_sold.astype(float) * price

        prod_df = pd.DataFrame(
            {
                "sale_date": dates,
                "product_id": pid,
                "category": cat,
                "brand": prod["brand"],
                "velocity_tier": velocity_tier,
                "units_sold": units_sold.astype(int),
                "unit_price_pkr": price,
                "revenue_pkr": revenue_pkr,
                "festival_name": fest_names,
                "is_festival_day": fest_names != "Regular_Day",
                "is_synthetic": True,
                "data_source": "Olist_Seasonality_Pakistani_Adapted",
            }
        )
        all_frames.append(prod_df)

    sales_df = pd.concat(all_frames, ignore_index=True)
    sales_df.to_parquet(out / "daily_sales.parquet", index=False)
    return sales_df


INVENTORY_SNAPSHOT_DATE = "2025-03-15"  # the date the Day 3 inventory plan is made from


def calibrate_stock_to_demand(
    catalogue_df: pd.DataFrame,
    sales_df: pd.DataFrame,
    snapshot_date: str = INVENTORY_SNAPSHOT_DATE,
    median_cover_days: float = 30.0,
    cover_spread: float = 0.7,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Set `stock_qty` of every product with sales history to a plausible warehouse level for its own demand.

    The catalogue generator draws stock uniformly from 5..250 units regardless of how fast a product sells, so a
    product selling 50 units/day had 3 days of stock and the inventory plan flagged ~75% of SKUs as critical.
    Here stock = (mean daily sales over the 28 days up to `snapshot_date`) x (days of cover), with days of cover
    drawn from a log-normal distribution (median `median_cover_days`). With the defaults about 1 in 7 products
    has under 2 weeks of cover and about 1 in 16 has over 90 days. Out-of-stock products (stock 0) stay at 0,
    and products without sales history are untouched. A separate random generator is used, so no other
    generated data changes.
    """
    rng = np.random.default_rng(seed + 7919)
    snap = pd.Timestamp(snapshot_date)
    dates = pd.to_datetime(sales_df["sale_date"])
    window = sales_df[(dates > snap - pd.Timedelta(days=28)) & (dates <= snap)]
    trailing = window.groupby("product_id")["units_sold"].mean()

    out = catalogue_df.copy()
    for idx in out.index[out["product_id"].isin(trailing.index)]:
        if int(out.at[idx, "stock_qty"]) == 0:
            continue
        cover = float(np.clip(rng.lognormal(np.log(median_cover_days), cover_spread), 2.0, 400.0))
        out.at[idx, "stock_qty"] = max(1, int(round(float(trailing[out.at[idx, "product_id"]]) * cover)))
    out["in_stock"] = out["stock_qty"] > 0
    return out


# ---------------------------------------------------------------------------
# 3. Multilingual Review Templates (English, Roman Urdu / UrduLish, Urdu)
# ---------------------------------------------------------------------------
REVIEW_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "positive": [
        {
            "lang": "Roman_Urdu",
            "title": "Bohot zabardast quality!",
            "text": "MashAllah {brand} ka {sub_cat} bilkul tasveer jaisa hai. Kapra aur finishing bohot achi hai aur delivery bhi time par mili.",
            "aspects": {"quality": 1, "price": 1, "delivery": 1, "size_fit": 1, "packaging": 1, "seller_behaviour": 1},
        },
        {
            "lang": "Roman_Urdu",
            "title": "Paisa wasool product",
            "text": "Price ke hisaab se {sub_cat} ki quality kamaal hai. Packing bhi mehfooz thi aur seller ne bohot acha taawun kiya.",
            "aspects": {"quality": 1, "price": 1, "delivery": 1, "size_fit": 0, "packaging": 1, "seller_behaviour": 1},
        },
        {
            "lang": "English",
            "title": "Excellent quality and fast delivery",
            "text": "Ordered this {sub_cat} from {brand} for Eid. The material quality exceeded expectations, fits perfectly, and arrived in 2 days.",
            "aspects": {"quality": 1, "price": 1, "delivery": 1, "size_fit": 1, "packaging": 1, "seller_behaviour": 1},
        },
        {
            "lang": "Urdu",
            "title": "بہترین معیار اور تیز ڈلیوری",
            "text": "{brand} کی یہ پراڈکٹ بہت شاندار ہے۔ کوالٹی اور پیکنگ دونوں لاجواب ہیں، قیمت بھی مناسب ہے۔",
            "aspects": {"quality": 1, "price": 1, "delivery": 1, "size_fit": 0, "packaging": 1, "seller_behaviour": 1},
        },
    ],
    "mixed_late_delivery": [
        {
            "lang": "Roman_Urdu",
            "title": "Quality achi hai lekin delivery late",
            "text": "Kapra aur {sub_cat} ki quality bohot achi hai lekin delivery bohot late thi, Eid se ek din pehle mushkil se mila.",
            "aspects": {"quality": 1, "price": 1, "delivery": -1, "size_fit": 1, "packaging": 0, "seller_behaviour": -1},
        },
        {
            "lang": "Roman_Urdu",
            "title": "Size thora chhota hai",
            "text": "{brand} ki quality to pasand aayi magar size thora chhota hai aur courier walon ne 5 din laga diye.",
            "aspects": {"quality": 1, "price": 0, "delivery": -1, "size_fit": -1, "packaging": 1, "seller_behaviour": 0},
        },
        {
            "lang": "English",
            "title": "Good product but size runs small and slow shipping",
            "text": "The {sub_cat} quality is genuinely nice for the price, however the size is smaller than standard and delivery took over a week.",
            "aspects": {"quality": 1, "price": 1, "delivery": -1, "size_fit": -1, "packaging": 0, "seller_behaviour": 0},
        },
    ],
    "negative": [
        {
            "lang": "Roman_Urdu",
            "title": "Bilkul bekaar aur kharab packing",
            "text": "Bohot ghatiya quality ka {sub_cat} bheja hai. Dabba phata hua tha, size bhi galat hai aur seller reply nahi karta.",
            "aspects": {"quality": -1, "price": -1, "delivery": -1, "size_fit": -1, "packaging": -1, "seller_behaviour": -1},
        },
        {
            "lang": "Roman_Urdu",
            "title": "Paise zaya ho gaye",
            "text": "Tasveer mein kuch aur tha aur asliyat mein halka kapra nikla. Qeemat bohot zyada hai is meyaar ke hisaab se.",
            "aspects": {"quality": -1, "price": -1, "delivery": 0, "size_fit": -1, "packaging": -1, "seller_behaviour": -1},
        },
        {
            "lang": "English",
            "title": "Damaged packaging and poor seller response",
            "text": "Received a defective item with torn packaging. Extremely overpriced and the seller ignored my replacement request.",
            "aspects": {"quality": -1, "price": -1, "delivery": -1, "size_fit": -1, "packaging": -1, "seller_behaviour": -1},
        },
        {
            "lang": "Urdu",
            "title": "ناقص معیار اور خراب پیکنگ",
            "text": "تصویر سے بالکل مختلف چیز بھیجی گئی ہے۔ ڈلیوری بھی تاخیر سے ہوئی اور پیکنگ ٹوٹی ہوئی تھی۔",
            "aspects": {"quality": -1, "price": -1, "delivery": -1, "size_fit": -1, "packaging": -1, "seller_behaviour": -1},
        },
    ],
}


def generate_pakistani_reviews(
    catalogue_df: pd.DataFrame,
    raw_olist_dir: Path | None = None,
    max_reviews: int = 8000,
    output_dir: Path | None = None,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Pair real Olist order/review metadata (scores, timestamps, seller IDs, delivery delays)
    with English, Urdu, and Roman Urdu (UrduLish) review texts and aspect annotations.
    Includes 5% realistic spam/fake review patterns for Day 4 spam detection.
    """
    out = output_dir or settings.synthetic_dir
    out.mkdir(parents=True, exist_ok=True)
    olist_dir = raw_olist_dir or settings.raw_olist_dir
    rng = np.random.default_rng(seed)

    # Load real Olist reviews + orders + order_items via DuckDB for speed
    con = duckdb.connect(":memory:")
    rev_path = str(olist_dir / "olist_order_reviews_dataset.csv").replace("\\", "/")
    ord_path = str(olist_dir / "olist_orders_dataset.csv").replace("\\", "/")
    itm_path = str(olist_dir / "olist_order_items_dataset.csv").replace("\\", "/")

    base_df = con.execute(
        f"""
        SELECT
            r.review_id,
            r.order_id,
            CAST(r.review_score AS INTEGER) AS rating,
            CAST(r.review_creation_date AS TIMESTAMP) AS review_date,
            i.seller_id,
            DATE_DIFF(
                'day',
                CAST(o.order_estimated_delivery_date AS TIMESTAMP),
                CAST(o.order_delivered_customer_date AS TIMESTAMP)
            ) AS delivery_delay_days
        FROM read_csv_auto('{rev_path}', ignore_errors=true) r
        JOIN read_csv_auto('{ord_path}', ignore_errors=true) o
          ON r.order_id = o.order_id
        JOIN read_csv_auto('{itm_path}', ignore_errors=true) i
          ON r.order_id = i.order_id
        WHERE r.review_score IS NOT NULL
        LIMIT {int(max_reviews)}
        """
    ).df()
    con.close()

    # Map products from our top 500 catalogue items so each product has dense reviews
    top_prods = catalogue_df.head(min(500, len(catalogue_df))).to_dict("records")
    n_prods = len(top_prods)

    rows: list[dict[str, Any]] = []
    for idx, rec in base_df.iterrows():
        prod = top_prods[idx % n_prods]
        rating = int(rec["rating"])
        delay = float(rec["delivery_delay_days"]) if pd.notna(rec["delivery_delay_days"]) else 0.0

        # Inject 5% fake / spam reviews (duplicates, promotional URLs, burst timestamps)
        is_spam = bool(rng.random() < 0.05)
        if is_spam:
            spam_type = str(rng.choice(["duplicate_bot", "promo_link", "extreme_burst"]))
            if spam_type == "duplicate_bot":
                title = "BEST PRODUCT 100% A+++ MUST BUY"
                text = "BEST PRODUCT 100% A+++ MUST BUY BEST SELLER FAST SHIPPING 5 STARS!!!"
                rating = 5
            elif spam_type == "promo_link":
                title = "Cheap discount offer WhatsApp now"
                text = "Visit www.cheap-deals-pk.biz or WhatsApp 0300-0000000 for 90% off replicas!!"
                rating = 5
            else:
                title = "Worst fake fraud seller"
                text = "FAKE FAKE FAKE DO NOT BUY COMPETITOR STORE IS BETTER!!!"
                rating = 1

            sentiment_label = "Positive" if rating >= 4 else "Negative"
            lang = "English"
            aspects = {
                "quality": 0,
                "price": 0,
                "delivery": 0,
                "size_fit": 0,
                "packaging": 0,
                "seller_behaviour": 0,
            }
        else:
            spam_type = "none"
            if rating >= 4 and delay <= 0:
                bucket = "positive"
                sentiment_label = "Positive"
            elif rating == 3 or (rating >= 4 and delay > 0):
                bucket = "mixed_late_delivery"
                sentiment_label = "Neutral" if rating == 3 else "Positive"
            else:
                bucket = "negative"
                sentiment_label = "Negative"

            tmpl = rng.choice(REVIEW_TEMPLATES[bucket])
            lang = tmpl["lang"]
            title = tmpl["title"]
            text = tmpl["text"].format(
                brand=prod["brand"],
                sub_cat=prod["sub_category"],
            )
            aspects = tmpl["aspects"]

        rows.append(
            {
                "review_id": f"REV-{idx + 1:05d}",
                "olist_review_id": str(rec["review_id"]),
                "order_id": str(rec["order_id"]),
                "product_id": prod["product_id"],
                "category": prod["category"],
                "brand": prod["brand"],
                "seller_id": str(rec["seller_id"])[:12],
                "rating": rating,
                "sentiment_label": sentiment_label,
                "language": lang,
                "review_title": title,
                "review_text": text,
                "delivery_delay_days": int(delay),
                "aspect_quality": int(aspects["quality"]),
                "aspect_price": int(aspects["price"]),
                "aspect_delivery": int(aspects["delivery"]),
                "aspect_size_fit": int(aspects["size_fit"]),
                "aspect_packaging": int(aspects["packaging"]),
                "aspect_seller": int(aspects["seller_behaviour"]),
                "is_fake_spam": is_spam,
                "spam_reason": spam_type,
                "review_date": rec["review_date"],
                "is_synthetic": True,
                "data_source": "Olist_Metadata_Pakistani_UrduLish_Enriched",
            }
        )

    reviews_df = pd.DataFrame(rows)
    reviews_df.to_parquet(out / "reviews.parquet", index=False)
    return reviews_df

