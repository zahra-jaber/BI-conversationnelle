-- ══════════════════════════════════════════════════════════════
-- Initialisation de la base bi_chat
-- Schémas : ecommerce (Olist) + rh (IBM HR)
-- ══════════════════════════════════════════════════════════════

-- ─── Schéma ecommerce ────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS ecommerce;

CREATE TABLE IF NOT EXISTS ecommerce.olist_customers_dataset (
    customer_id VARCHAR(50) PRIMARY KEY,
    customer_unique_id VARCHAR(50),
    customer_zip_code_prefix INT,
    customer_city VARCHAR(100),
    customer_state VARCHAR(5)
);

CREATE TABLE IF NOT EXISTS ecommerce.olist_orders_dataset (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50),
    order_status VARCHAR(30),
    order_purchase_timestamp TIMESTAMP,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ecommerce.olist_order_items_dataset (
    order_id VARCHAR(50),
    order_item_id INT,
    product_id VARCHAR(50),
    seller_id VARCHAR(50),
    shipping_limit_date TIMESTAMP,
    price NUMERIC(10,2),
    freight_value NUMERIC(10,2)
);

CREATE TABLE IF NOT EXISTS ecommerce.olist_order_payments_dataset (
    order_id VARCHAR(50),
    payment_sequential INT,
    payment_type VARCHAR(30),
    payment_installments INT,
    payment_value NUMERIC(10,2)
);

CREATE TABLE IF NOT EXISTS ecommerce.olist_products_dataset (
    product_id VARCHAR(50) PRIMARY KEY,
    product_category_name VARCHAR(100),
    product_name_length INT,
    product_description_length INT,
    product_photos_qty INT,
    product_weight_g INT,
    product_length_cm INT,
    product_height_cm INT,
    product_width_cm INT
);

CREATE TABLE IF NOT EXISTS ecommerce.olist_sellers_dataset (
    seller_id VARCHAR(50) PRIMARY KEY,
    seller_zip_code_prefix INT,
    seller_city VARCHAR(100),
    seller_state VARCHAR(5)
);

CREATE TABLE IF NOT EXISTS ecommerce.olist_geolocation_dataset (
    geolocation_zip_code_prefix INT,
    geolocation_lat NUMERIC(10,6),
    geolocation_lng NUMERIC(10,6),
    geolocation_city VARCHAR(100),
    geolocation_state VARCHAR(5)
);

CREATE TABLE IF NOT EXISTS ecommerce.product_category_name_translation (
    product_category_name VARCHAR(100) PRIMARY KEY,
    product_category_name_english VARCHAR(100)
);

-- ─── Schéma rh (IBM HR Dataset) ──────────────────────────────
CREATE SCHEMA IF NOT EXISTS rh;

CREATE TABLE IF NOT EXISTS rh.employees (
    employee_id SERIAL PRIMARY KEY,
    age INT,
    attrition VARCHAR(5),
    business_travel VARCHAR(50),
    daily_rate INT,
    department VARCHAR(50),
    distance_from_home INT,
    education INT,
    education_field VARCHAR(50),
    environment_satisfaction INT,
    gender VARCHAR(10),
    hourly_rate INT,
    job_involvement INT,
    job_level INT,
    job_role VARCHAR(50),
    job_satisfaction INT,
    marital_status VARCHAR(20),
    monthly_income INT,
    monthly_rate INT,
    num_companies_worked INT,
    over18 VARCHAR(5),
    over_time VARCHAR(5),
    percent_salary_hike INT,
    performance_rating INT,
    relationship_satisfaction INT,
    standard_hours INT,
    stock_option_level INT,
    total_working_years INT,
    training_times_last_year INT,
    work_life_balance INT,
    years_at_company INT,
    years_in_current_role INT,
    years_since_last_promotion INT,
    years_with_curr_manager INT
);

CREATE TABLE IF NOT EXISTS rh.departments (
    department_id SERIAL PRIMARY KEY,
    department_name VARCHAR(50) UNIQUE,
    manager_name VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS rh.evaluations (
    evaluation_id SERIAL PRIMARY KEY,
    employee_id INT REFERENCES rh.employees(employee_id),
    evaluation_year INT,
    performance_score INT,
    comments TEXT
);

-- ─── Utilisateurs PostgreSQL par rôle (RLS) ──────────────────
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'role_finance') THEN
        CREATE ROLE role_finance;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'role_marketing') THEN
        CREATE ROLE role_marketing;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'role_rh') THEN
        CREATE ROLE role_rh;
    END IF;
END $$;

-- Finance : accès schéma ecommerce uniquement
GRANT USAGE ON SCHEMA ecommerce TO role_finance;
GRANT SELECT ON
    ecommerce.olist_orders_dataset,
    ecommerce.olist_order_items_dataset,
    ecommerce.olist_order_payments_dataset,
    ecommerce.olist_products_dataset,
    ecommerce.product_category_name_translation
TO role_finance;

-- Marketing : accès schéma ecommerce (tables clients/produits)
GRANT USAGE ON SCHEMA ecommerce TO role_marketing;
GRANT SELECT ON
    ecommerce.olist_customers_dataset,
    ecommerce.olist_products_dataset,
    ecommerce.olist_sellers_dataset,
    ecommerce.product_category_name_translation,
    ecommerce.olist_geolocation_dataset
TO role_marketing;

-- RH : accès schéma rh uniquement
GRANT USAGE ON SCHEMA rh TO role_rh;
GRANT SELECT ON ALL TABLES IN SCHEMA rh TO role_rh;

-- Admin : accès complet
GRANT USAGE ON SCHEMA ecommerce, rh TO bi_user;
GRANT SELECT ON ALL TABLES IN SCHEMA ecommerce TO bi_user;
GRANT SELECT ON ALL TABLES IN SCHEMA rh TO bi_user;
