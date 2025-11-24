-- Seed data for Northwind Analytics
-- Synthetic but realistic SaaS metrics data

-- Insert regions
INSERT INTO regions (region_id, region_name, region_code, quota_mrr) VALUES
(1, 'North America', 'NA', 300000),
(2, 'EMEA', 'EMEA', 250000),
(3, 'APAC', 'APAC', 150000),
(4, 'LATAM', 'LATAM', 80000);

-- Insert customers (100 customers across regions and segments)
INSERT INTO customers (customer_id, company_name, industry, segment, region_id, signup_date, status) VALUES
-- North America - Enterprise
(1, 'TechCorp Global', 'Technology', 'Enterprise', 1, '2022-03-15', 'active'),
(2, 'FinanceHub Inc', 'Financial Services', 'Enterprise', 1, '2022-06-20', 'active'),
(3, 'HealthCare Systems', 'Healthcare', 'Enterprise', 1, '2022-09-10', 'active'),
(4, 'RetailMax Corp', 'Retail', 'Enterprise', 1, '2023-01-05', 'active'),
(5, 'ManufacturingPro', 'Manufacturing', 'Enterprise', 1, '2023-04-12', 'active'),
(6, 'MediaCo Entertainment', 'Media', 'Enterprise', 1, '2023-07-18', 'churned'),
(7, 'EduTech Solutions', 'Education', 'Enterprise', 1, '2023-10-22', 'active'),
(8, 'LogisticsXpress', 'Logistics', 'Enterprise', 1, '2024-01-15', 'active'),

-- North America - Professional
(9, 'StartupNow LLC', 'Technology', 'Professional', 1, '2023-02-10', 'active'),
(10, 'ConsultPro Partners', 'Consulting', 'Professional', 1, '2023-03-22', 'active'),
(11, 'DesignStudio Plus', 'Creative', 'Professional', 1, '2023-05-14', 'active'),
(12, 'LegalEagle Associates', 'Legal', 'Professional', 1, '2023-06-30', 'active'),
(13, 'RealEstate Pro', 'Real Estate', 'Professional', 1, '2023-08-05', 'active'),
(14, 'Marketing Masters', 'Marketing', 'Professional', 1, '2023-09-18', 'churned'),
(15, 'CloudOps Services', 'Technology', 'Professional', 1, '2023-11-01', 'active'),
(16, 'DataLabs Analytics', 'Technology', 'Professional', 1, '2024-01-08', 'active'),
(17, 'InsureTech Group', 'Insurance', 'Professional', 1, '2024-02-14', 'active'),
(18, 'AgriTech Innovations', 'Agriculture', 'Professional', 1, '2024-03-20', 'active'),
(19, 'ConstructBuild Co', 'Construction', 'Professional', 1, '2024-04-25', 'active'),
(20, 'HospitalityHub', 'Hospitality', 'Professional', 1, '2024-05-30', 'active'),

-- North America - Starter
(21, 'Local Coffee Shop', 'Food & Beverage', 'Starter', 1, '2023-06-15', 'active'),
(22, 'Boutique Fashion', 'Retail', 'Starter', 1, '2023-07-20', 'active'),
(23, 'Home Services Pro', 'Services', 'Starter', 1, '2023-08-25', 'active'),
(24, 'Fitness Studio Elite', 'Health & Fitness', 'Starter', 1, '2023-09-30', 'churned'),
(25, 'Pet Care Plus', 'Services', 'Starter', 1, '2023-11-05', 'active'),
(26, 'Auto Repair Shop', 'Automotive', 'Starter', 1, '2023-12-10', 'active'),
(27, 'Cleaning Services Co', 'Services', 'Starter', 1, '2024-01-15', 'active'),
(28, 'Photography Studio', 'Creative', 'Starter', 1, '2024-02-20', 'active'),
(29, 'Landscaping Pros', 'Services', 'Starter', 1, '2024-03-25', 'active'),
(30, 'Bakery Delights', 'Food & Beverage', 'Starter', 1, '2024-04-30', 'active'),

-- EMEA - Enterprise
(31, 'EuroTech Solutions', 'Technology', 'Enterprise', 2, '2022-04-10', 'active'),
(32, 'BankingFirst AG', 'Financial Services', 'Enterprise', 2, '2022-07-15', 'active'),
(33, 'PharmaCo International', 'Healthcare', 'Enterprise', 2, '2022-10-20', 'active'),
(34, 'AutoManufacture GmbH', 'Manufacturing', 'Enterprise', 2, '2023-02-25', 'active'),
(35, 'Energy Systems Ltd', 'Energy', 'Enterprise', 2, '2023-05-30', 'active'),
(36, 'Telecom Global SA', 'Telecommunications', 'Enterprise', 2, '2023-08-15', 'active'),

-- EMEA - Professional
(37, 'DesignHub Berlin', 'Creative', 'Professional', 2, '2023-03-10', 'active'),
(38, 'Consulting Partners UK', 'Consulting', 'Professional', 2, '2023-04-15', 'active'),
(39, 'E-Commerce Pro FR', 'Retail', 'Professional', 2, '2023-05-20', 'active'),
(40, 'SaaS Startup Dublin', 'Technology', 'Professional', 2, '2023-06-25', 'active'),
(41, 'Marketing Agency ES', 'Marketing', 'Professional', 2, '2023-07-30', 'active'),
(42, 'Legal Advisors IT', 'Legal', 'Professional', 2, '2023-09-05', 'churned'),
(43, 'Logistics Hub NL', 'Logistics', 'Professional', 2, '2023-10-10', 'active'),
(44, 'PropTech Solutions', 'Real Estate', 'Professional', 2, '2023-11-15', 'active'),
(45, 'FoodTech Innovators', 'Food & Beverage', 'Professional', 2, '2023-12-20', 'active'),
(46, 'CleanEnergy Group', 'Energy', 'Professional', 2, '2024-01-25', 'active'),
(47, 'HealthTech Nordic', 'Healthcare', 'Professional', 2, '2024-02-28', 'active'),
(48, 'FinTech Startup CH', 'Financial Services', 'Professional', 2, '2024-03-30', 'active'),

-- EMEA - Starter
(49, 'Cafe Central', 'Food & Beverage', 'Starter', 2, '2023-08-10', 'active'),
(50, 'Yoga Studio', 'Health & Fitness', 'Starter', 2, '2023-09-15', 'active'),
(51, 'Bookshop Local', 'Retail', 'Starter', 2, '2023-10-20', 'active'),
(52, 'Salon Beauty', 'Services', 'Starter', 2, '2023-11-25', 'active'),
(53, 'Bike Repair Shop', 'Services', 'Starter', 2, '2023-12-30', 'active'),
(54, 'Art Gallery', 'Arts', 'Starter', 2, '2024-02-05', 'active'),
(55, 'Wine Bar', 'Food & Beverage', 'Starter', 2, '2024-03-10', 'active'),

-- APAC - Enterprise
(56, 'AsiaTech Corp', 'Technology', 'Enterprise', 3, '2022-05-15', 'active'),
(57, 'Manufacturing Asia Ltd', 'Manufacturing', 'Enterprise', 3, '2022-08-20', 'active'),
(58, 'Financial Services KK', 'Financial Services', 'Enterprise', 3, '2022-11-25', 'active'),
(59, 'E-Commerce Giant', 'Retail', 'Enterprise', 3, '2023-03-01', 'active'),
(60, 'Gaming Studios', 'Entertainment', 'Enterprise', 3, '2023-06-05', 'active'),
(61, 'Telecom Pacific', 'Telecommunications', 'Enterprise', 3, '2024-07-01', 'active'),  -- Note: This is TechCorp that downgraded in Q3

-- APAC - Professional
(62, 'SaaS Startup SG', 'Technology', 'Professional', 3, '2023-04-10', 'active'),
(63, 'Marketing Agency HK', 'Marketing', 'Professional', 3, '2023-05-15', 'active'),
(64, 'Consulting Partners AU', 'Consulting', 'Professional', 3, '2023-06-20', 'active'),
(65, 'PropTech Solutions IN', 'Real Estate', 'Professional', 3, '2023-07-25', 'active'),
(66, 'HealthTech Innovators', 'Healthcare', 'Professional', 3, '2023-08-30', 'active'),
(67, 'EdTech Platform', 'Education', 'Professional', 3, '2023-10-05', 'active'),
(68, 'FinTech Startup JP', 'Financial Services', 'Professional', 3, '2023-11-10', 'active'),
(69, 'AgriTech Solutions', 'Agriculture', 'Professional', 3, '2023-12-15', 'active'),
(70, 'Logistics Tech', 'Logistics', 'Professional', 3, '2024-01-20', 'active'),
(71, 'CleanTech Group', 'Energy', 'Professional', 3, '2024-02-25', 'active'),

-- APAC - Starter
(72, 'Coffee House', 'Food & Beverage', 'Starter', 3, '2023-09-10', 'active'),
(73, 'Fitness Center', 'Health & Fitness', 'Starter', 3, '2023-10-15', 'active'),
(74, 'Retail Boutique', 'Retail', 'Starter', 3, '2023-11-20', 'active'),
(75, 'Beauty Salon', 'Services', 'Starter', 3, '2023-12-25', 'active'),
(76, 'Restaurant Local', 'Food & Beverage', 'Starter', 3, '2024-01-30', 'active'),
(77, 'Design Studio', 'Creative', 'Starter', 3, '2024-03-05', 'active'),

-- LATAM - Enterprise
(78, 'TechBrasil SA', 'Technology', 'Enterprise', 4, '2022-06-10', 'active'),
(79, 'Banking LATAM', 'Financial Services', 'Enterprise', 4, '2022-09-15', 'active'),
(80, 'Manufacturing MX', 'Manufacturing', 'Enterprise', 4, '2023-01-20', 'active'),
(81, 'Retail Group AR', 'Retail', 'Enterprise', 4, '2023-04-25', 'active'),

-- LATAM - Professional
(82, 'SaaS Startup BR', 'Technology', 'Professional', 4, '2023-05-10', 'active'),
(83, 'Marketing Agency CO', 'Marketing', 'Professional', 4, '2023-06-15', 'active'),
(84, 'Consulting CL', 'Consulting', 'Professional', 4, '2023-07-20', 'active'),
(85, 'E-Commerce PE', 'Retail', 'Professional', 4, '2023-08-25', 'active'),
(86, 'FinTech MX', 'Financial Services', 'Professional', 4, '2023-09-30', 'active'),
(87, 'PropTech BR', 'Real Estate', 'Professional', 4, '2023-11-05', 'active'),
(88, 'HealthTech CO', 'Healthcare', 'Professional', 4, '2023-12-10', 'active'),
(89, 'EdTech Platform', 'Education', 'Professional', 4, '2024-01-15', 'active'),
(90, 'AgriTech Solutions', 'Agriculture', 'Professional', 4, '2024-02-20', 'active'),

-- LATAM - Starter
(91, 'Cafe Local', 'Food & Beverage', 'Starter', 4, '2023-10-10', 'active'),
(92, 'Gym Fitness', 'Health & Fitness', 'Starter', 4, '2023-11-15', 'active'),
(93, 'Shop Boutique', 'Retail', 'Starter', 4, '2023-12-20', 'active'),
(94, 'Salon Beauty', 'Services', 'Starter', 4, '2024-01-25', 'active'),
(95, 'Restaurant', 'Food & Beverage', 'Starter', 4, '2024-02-28', 'active'),
(96, 'Auto Service', 'Automotive', 'Starter', 4, '2024-03-30', 'active'),
(97, 'Photography', 'Creative', 'Starter', 4, '2024-04-30', 'active'),
(98, 'Pet Services', 'Services', 'Starter', 4, '2024-05-30', 'active'),
(99, 'Cleaning Co', 'Services', 'Starter', 4, '2024-06-15', 'active'),
(100, 'Landscaping', 'Services', 'Starter', 4, '2024-07-01', 'active');

-- Insert subscriptions (active subscriptions for active customers)
-- Pricing: Enterprise ~$15K/mo, Professional ~$3K/mo, Starter ~$500/mo
INSERT INTO subscriptions (subscription_id, customer_id, plan_name, monthly_value, start_date, end_date, status) VALUES
-- North America Enterprise (active)
(1, 1, 'Enterprise Plus', 18000, '2022-03-15', NULL, 'active'),
(2, 2, 'Enterprise', 15000, '2022-06-20', NULL, 'active'),
(3, 3, 'Enterprise', 16500, '2022-09-10', NULL, 'active'),
(4, 4, 'Enterprise Plus', 19000, '2023-01-05', NULL, 'active'),
(5, 5, 'Enterprise', 14000, '2023-04-12', NULL, 'active'),
(7, 7, 'Enterprise', 17000, '2023-10-22', NULL, 'active'),
(8, 8, 'Enterprise Plus', 20000, '2024-01-15', NULL, 'active'),

-- MediaCo (churned in Q2 2024)
(6, 6, 'Enterprise', 15000, '2023-07-18', '2024-05-30', 'canceled'),

-- North America Professional
(9, 9, 'Professional Plus', 3500, '2023-02-10', NULL, 'active'),
(10, 10, 'Professional', 2800, '2023-03-22', NULL, 'active'),
(11, 11, 'Professional', 3200, '2023-05-14', NULL, 'active'),
(12, 12, 'Professional Plus', 3800, '2023-06-30', NULL, 'active'),
(13, 13, 'Professional', 2900, '2023-08-05', NULL, 'active'),
(14, 14, 'Professional', 3000, '2023-09-18', '2024-03-15', 'canceled'),
(15, 15, 'Professional Plus', 4200, '2023-11-01', NULL, 'active'),
(16, 16, 'Professional', 3100, '2024-01-08', NULL, 'active'),
(17, 17, 'Professional', 2700, '2024-02-14', NULL, 'active'),
(18, 18, 'Professional Plus', 3600, '2024-03-20', NULL, 'active'),
(19, 19, 'Professional', 2900, '2024-04-25', NULL, 'active'),
(20, 20, 'Professional', 3000, '2024-05-30', NULL, 'active'),

-- North America Starter
(21, 21, 'Starter', 450, '2023-06-15', NULL, 'active'),
(22, 22, 'Starter Plus', 650, '2023-07-20', NULL, 'active'),
(23, 23, 'Starter', 500, '2023-08-25', NULL, 'active'),
(24, 24, 'Starter', 450, '2023-09-30', '2024-06-15', 'canceled'),
(25, 25, 'Starter Plus', 600, '2023-11-05', NULL, 'active'),
(26, 26, 'Starter', 480, '2023-12-10', NULL, 'active'),
(27, 27, 'Starter', 520, '2024-01-15', NULL, 'active'),
(28, 28, 'Starter Plus', 630, '2024-02-20', NULL, 'active'),
(29, 29, 'Starter', 490, '2024-03-25', NULL, 'active'),
(30, 30, 'Starter', 510, '2024-04-30', NULL, 'active'),

-- EMEA Enterprise
(31, 31, 'Enterprise', 16000, '2022-04-10', NULL, 'active'),
(32, 32, 'Enterprise Plus', 21000, '2022-07-15', NULL, 'active'),
(33, 33, 'Enterprise', 18500, '2022-10-20', NULL, 'active'),
(34, 34, 'Enterprise Plus', 19500, '2023-02-25', NULL, 'active'),
(35, 35, 'Enterprise', 17000, '2023-05-30', NULL, 'active'),
(36, 36, 'Enterprise Plus', 22000, '2023-08-15', NULL, 'active'),

-- EMEA Professional
(37, 37, 'Professional', 3100, '2023-03-10', NULL, 'active'),
(38, 38, 'Professional Plus', 3900, '2023-04-15', NULL, 'active'),
(39, 39, 'Professional', 2950, '2023-05-20', NULL, 'active'),
(40, 40, 'Professional Plus', 4100, '2023-06-25', NULL, 'active'),
(41, 41, 'Professional', 3200, '2023-07-30', NULL, 'active'),
(42, 42, 'Professional', 2800, '2023-09-05', '2024-04-10', 'canceled'),
(43, 43, 'Professional', 3300, '2023-10-10', NULL, 'active'),
(44, 44, 'Professional Plus', 3700, '2023-11-15', NULL, 'active'),
(45, 45, 'Professional', 3000, '2023-12-20', NULL, 'active'),
(46, 46, 'Professional', 2900, '2024-01-25', NULL, 'active'),
(47, 47, 'Professional Plus', 3800, '2024-02-28', NULL, 'active'),
(48, 48, 'Professional', 3400, '2024-03-30', NULL, 'active'),

-- EMEA Starter
(49, 49, 'Starter', 480, '2023-08-10', NULL, 'active'),
(50, 50, 'Starter', 520, '2023-09-15', NULL, 'active'),
(51, 51, 'Starter Plus', 640, '2023-10-20', NULL, 'active'),
(52, 52, 'Starter', 490, '2023-11-25', NULL, 'active'),
(53, 53, 'Starter', 510, '2023-12-30', NULL, 'active'),
(54, 54, 'Starter Plus', 620, '2024-02-05', NULL, 'active'),
(55, 55, 'Starter', 530, '2024-03-10', NULL, 'active'),

-- APAC Enterprise
(56, 56, 'Enterprise Plus', 20000, '2022-05-15', NULL, 'active'),
(57, 57, 'Enterprise', 17500, '2022-08-20', NULL, 'active'),
(58, 58, 'Enterprise', 16000, '2022-11-25', NULL, 'active'),
(59, 59, 'Enterprise Plus', 21500, '2023-03-01', NULL, 'active'),
(60, 60, 'Enterprise', 18000, '2023-06-05', NULL, 'active'),
-- TechCorp downgraded from Enterprise ($18K) to Professional ($4K) in July 2024
(61, 61, 'Enterprise', 18000, '2024-01-01', '2024-07-15', 'canceled'),
(101, 61, 'Professional Plus', 4000, '2024-07-15', NULL, 'active'),  -- Downgrade

-- APAC Professional
(62, 62, 'Professional', 3200, '2023-04-10', NULL, 'active'),
(63, 63, 'Professional Plus', 3900, '2023-05-15', NULL, 'active'),
(64, 64, 'Professional', 3100, '2023-06-20', NULL, 'active'),
(65, 65, 'Professional', 2850, '2023-07-25', NULL, 'active'),
(66, 66, 'Professional Plus', 4000, '2023-08-30', NULL, 'active'),
(67, 67, 'Professional', 3300, '2023-10-05', NULL, 'active'),
(68, 68, 'Professional Plus', 3700, '2023-11-10', NULL, 'active'),
(69, 69, 'Professional', 2950, '2023-12-15', NULL, 'active'),
(70, 70, 'Professional', 3150, '2024-01-20', NULL, 'active'),
(71, 71, 'Professional', 2900, '2024-02-25', NULL, 'active'),

-- APAC Starter
(72, 72, 'Starter', 470, '2023-09-10', NULL, 'active'),
(73, 73, 'Starter Plus', 610, '2023-10-15', NULL, 'active'),
(74, 74, 'Starter', 500, '2023-11-20', NULL, 'active'),
(75, 75, 'Starter', 485, '2023-12-25', NULL, 'active'),
(76, 76, 'Starter', 515, '2024-01-30', NULL, 'active'),
(77, 77, 'Starter Plus', 630, '2024-03-05', NULL, 'active'),

-- LATAM Enterprise
(78, 78, 'Enterprise', 15500, '2022-06-10', NULL, 'active'),
(79, 79, 'Enterprise Plus', 19000, '2022-09-15', NULL, 'active'),
(80, 80, 'Enterprise', 16500, '2023-01-20', NULL, 'active'),
(81, 81, 'Enterprise', 17500, '2023-04-25', NULL, 'active'),

-- LATAM Professional
(82, 82, 'Professional Plus', 3600, '2023-05-10', NULL, 'active'),
(83, 83, 'Professional', 2900, '2023-06-15', NULL, 'active'),
(84, 84, 'Professional', 3100, '2023-07-20', NULL, 'active'),
(85, 85, 'Professional Plus', 3800, '2023-08-25', NULL, 'active'),
(86, 86, 'Professional', 3200, '2023-09-30', NULL, 'active'),
(87, 87, 'Professional', 2950, '2023-11-05', NULL, 'active'),
(88, 88, 'Professional Plus', 3700, '2023-12-10', NULL, 'active'),
(89, 89, 'Professional', 3050, '2024-01-15', NULL, 'active'),
(90, 90, 'Professional', 2850, '2024-02-20', NULL, 'active'),

-- LATAM Starter
(91, 91, 'Starter', 460, '2023-10-10', NULL, 'active'),
(92, 92, 'Starter', 495, '2023-11-15', NULL, 'active'),
(93, 93, 'Starter Plus', 625, '2023-12-20', NULL, 'active'),
(94, 94, 'Starter', 505, '2024-01-25', NULL, 'active'),
(95, 95, 'Starter', 520, '2024-02-28', NULL, 'active'),
(96, 96, 'Starter', 480, '2024-03-30', NULL, 'active'),
(97, 97, 'Starter Plus', 615, '2024-04-30', NULL, 'active'),
(98, 98, 'Starter', 490, '2024-05-30', NULL, 'active'),
(99, 99, 'Starter', 475, '2024-06-15', NULL, 'active'),
(100, 100, 'Starter', 510, '2024-07-01', NULL, 'active');
