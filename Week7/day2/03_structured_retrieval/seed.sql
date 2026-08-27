-- Demo seed data is provided in 01_knowledge_base/properties.csv.
-- Load it into PostgreSQL using your preferred CSV import method.

-- Example:
-- \copy properties(property_id,name,area,city,property_type,bedrooms,bathrooms,price,currency,available,status,developer,purpose)
-- FROM '01_knowledge_base/properties.csv'
-- WITH (FORMAT csv, HEADER true, NULL '-');
