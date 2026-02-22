-- ============================================================================
-- DATABASE VERIFICATION QUERIES FOR RENTAL TESTING
-- ============================================================================
-- Date: 2026-02-22
-- Purpose: Comprehensive queries to verify rental flow data integrity
-- ============================================================================

-- ============================================================================
-- SECTION 1: USER BALANCE QUERIES
-- ============================================================================

-- Get current user balances
-- Replace 'USER_EMAIL' with actual email
SELECT
    u.id as user_id,
    u.email,
    u.username,
    w.balance as wallet_balance,
    p.current_points,
    p.lifetime_earned as total_points_earned,
    p.lifetime_spent as total_points_spent
FROM users u
LEFT JOIN wallets w ON w.user_id = u.id
LEFT JOIN points p ON p.user_id = u.id
WHERE u.email = 'janak@powerbank.com';

-- Get wallet transaction history
SELECT
    wt.id,
    wt.transaction_type,
    wt.amount,
    wt.balance_after,
    wt.description,
    wt.created_at,
    t.transaction_id as related_transaction
FROM wallet_transactions wt
LEFT JOIN transactions t ON wt.transaction_id = t.id
WHERE wt.user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
ORDER BY wt.created_at DESC
LIMIT 20;

-- Get points transaction history
SELECT
    pt.id,
    pt.transaction_type,
    pt.points,
    pt.balance_after,
    pt.description,
    pt.created_at
FROM point_transactions pt
WHERE pt.user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
ORDER BY pt.created_at DESC
LIMIT 20;

-- ============================================================================
-- SECTION 2: RENTAL QUERIES
-- ============================================================================

-- Get all rentals for a user
SELECT
    r.id,
    r.rental_code,
    r.status,
    r.payment_status,
    r.amount_paid,
    r.overdue_amount,
    r.is_returned_on_time,
    r.timely_return_bonus_awarded,
    rp.name as package_name,
    rp.payment_model,
    rp.price as package_price,
    rp.duration_minutes,
    r.started_at,
    r.ended_at,
    r.due_at,
    CASE
        WHEN r.ended_at IS NOT NULL THEN
            EXTRACT(EPOCH FROM (r.ended_at - r.started_at))/60
        ELSE
            EXTRACT(EPOCH FROM (NOW() - r.started_at))/60
    END as usage_minutes,
    CASE
        WHEN r.ended_at IS NOT NULL AND r.ended_at > r.due_at THEN
            EXTRACT(EPOCH FROM (r.ended_at - r.due_at))/60
        WHEN r.ended_at IS NULL AND NOW() > r.due_at THEN
            EXTRACT(EPOCH FROM (NOW() - r.due_at))/60
        ELSE 0
    END as overdue_minutes,
    s.station_name as start_station,
    rs.station_name as return_station,
    pb.serial_number as powerbank_serial
FROM rentals r
JOIN rental_packages rp ON r.package_id = rp.id
JOIN stations s ON r.station_id = s.id
LEFT JOIN stations rs ON r.return_station_id = rs.id
LEFT JOIN power_banks pb ON r.power_bank_id = pb.id
WHERE r.user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
ORDER BY r.created_at DESC
LIMIT 20;

-- Get specific rental by code
SELECT
    r.id,
    r.rental_code,
    r.status,
    r.payment_status,
    r.amount_paid,
    r.overdue_amount,
    r.is_returned_on_time,
    rp.name as package_name,
    rp.payment_model,
    rp.price as package_price,
    rp.duration_minutes,
    r.started_at,
    r.ended_at,
    r.due_at,
    r.start_battery_level,
    r.return_battery_level,
    r.is_under_5_min,
    r.hardware_issue_reported,
    r.rental_metadata,
    pb.serial_number as powerbank_serial,
    s.station_name as start_station,
    rs.station_name as return_station
FROM rentals r
JOIN rental_packages rp ON r.package_id = rp.id
JOIN stations s ON r.station_id = s.id
LEFT JOIN stations rs ON r.return_station_id = rs.id
LEFT JOIN power_banks pb ON r.power_bank_id = pb.id
WHERE r.rental_code = 'RENTAL_CODE_HERE';

-- Get active rentals
SELECT
    r.rental_code,
    r.status,
    r.payment_status,
    r.amount_paid,
    r.overdue_amount,
    rp.payment_model,
    r.started_at,
    r.due_at,
    EXTRACT(EPOCH FROM (NOW() - r.due_at))/60 as minutes_overdue,
    u.email as user_email
FROM rentals r
JOIN rental_packages rp ON r.package_id = rp.id
JOIN users u ON r.user_id = u.id
WHERE r.status IN ('ACTIVE', 'OVERDUE')
ORDER BY r.started_at DESC;

-- Get rentals by payment model
SELECT
    rp.payment_model,
    r.status,
    r.payment_status,
    COUNT(*) as count,
    SUM(r.amount_paid) as total_amount_paid,
    SUM(r.overdue_amount) as total_overdue
FROM rentals r
JOIN rental_packages rp ON r.package_id = rp.id
WHERE r.user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
GROUP BY rp.payment_model, r.status, r.payment_status
ORDER BY rp.payment_model, r.status;

-- ============================================================================
-- SECTION 3: TRANSACTION QUERIES
-- ============================================================================

-- Get all transactions for a user
SELECT
    t.id,
    t.transaction_id,
    t.transaction_type,
    t.amount,
    t.status,
    t.payment_method_type,
    t.created_at,
    r.rental_code,
    t.gateway_response
FROM transactions t
LEFT JOIN rentals r ON t.related_rental_id = r.id
WHERE t.user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
ORDER BY t.created_at DESC
LIMIT 20;

-- Get transactions for specific rental
SELECT
    t.transaction_id,
    t.transaction_type,
    t.amount,
    t.status,
    t.payment_method_type,
    t.gateway_response,
    t.created_at
FROM transactions t
WHERE t.related_rental_id = (SELECT id FROM rentals WHERE rental_code = 'RENTAL_CODE_HERE')
ORDER BY t.created_at;

-- Get transaction summary by type
SELECT
    t.transaction_type,
    t.status,
    COUNT(*) as count,
    SUM(t.amount) as total_amount,
    MIN(t.created_at) as first_transaction,
    MAX(t.created_at) as last_transaction
FROM transactions t
WHERE t.user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
GROUP BY t.transaction_type, t.status
ORDER BY t.transaction_type, t.status;

-- ============================================================================
-- SECTION 4: RENTAL EXTENSIONS
-- ============================================================================

-- Get rental extensions
SELECT
    re.id,
    r.rental_code,
    re.extended_minutes,
    re.extension_cost,
    re.extended_at,
    rp.name as extension_package
FROM rental_extensions re
JOIN rentals r ON re.rental_id = r.id
JOIN rental_packages rp ON re.package_id = rp.id
WHERE r.user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
ORDER BY re.extended_at DESC;

-- ============================================================================
-- SECTION 5: RENTAL ISSUES
-- ============================================================================

-- Get rental issues
SELECT
    ri.id,
    r.rental_code,
    ri.issue_type,
    ri.description,
    ri.status,
    ri.reported_at,
    ri.resolved_at
FROM rental_issues ri
JOIN rentals r ON ri.rental_id = r.id
WHERE r.user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
ORDER BY ri.reported_at DESC;

-- ============================================================================
-- SECTION 6: RENTAL SWAPS
-- ============================================================================

-- Get rental swaps
SELECT
    rs.id,
    r.rental_code,
    rs.swap_reason,
    rs.description,
    opb.serial_number as old_powerbank,
    rs.old_battery_level,
    npb.serial_number as new_powerbank,
    rs.new_battery_level,
    rs.swapped_at
FROM rental_swaps rs
JOIN rentals r ON rs.rental_id = r.id
LEFT JOIN power_banks opb ON rs.old_powerbank_id = opb.id
LEFT JOIN power_banks npb ON rs.new_powerbank_id = npb.id
WHERE r.user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
ORDER BY rs.swapped_at DESC;

-- ============================================================================
-- SECTION 7: REVENUE DISTRIBUTION
-- ============================================================================

-- Get revenue distributions
SELECT
    rd.id,
    r.rental_code,
    t.transaction_id,
    rd.total_amount,
    rd.platform_amount,
    rd.vendor_amount,
    rd.status,
    rd.created_at,
    rd.distributed_at
FROM revenue_distributions rd
JOIN rentals r ON rd.rental_id = r.id
JOIN transactions t ON rd.transaction_id = t.id
WHERE r.user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
ORDER BY rd.created_at DESC;

-- ============================================================================
-- SECTION 8: PACKAGE INFORMATION
-- ============================================================================

-- Get all rental packages
SELECT
    rp.id,
    rp.name,
    rp.description,
    rp.payment_model,
    rp.package_type,
    rp.duration_minutes,
    rp.price,
    rp.is_active,
    COUNT(r.id) as times_used
FROM rental_packages rp
LEFT JOIN rentals r ON r.package_id = rp.id
GROUP BY rp.id
ORDER BY rp.payment_model, rp.duration_minutes;

-- ============================================================================
-- SECTION 9: STATION & POWERBANK STATUS
-- ============================================================================

-- Get station status
SELECT
    s.id,
    s.serial_number,
    s.station_name,
    s.status,
    s.is_maintenance,
    COUNT(CASE WHEN pb.status = 'AVAILABLE' THEN 1 END) as available_powerbanks,
    COUNT(CASE WHEN pb.status = 'RENTED' THEN 1 END) as rented_powerbanks,
    COUNT(CASE WHEN pb.status = 'CHARGING' THEN 1 END) as charging_powerbanks,
    COUNT(pb.id) as total_powerbanks
FROM stations s
LEFT JOIN power_banks pb ON pb.current_station_id = s.id
GROUP BY s.id
ORDER BY s.station_name;

-- Get powerbank details
SELECT
    pb.id,
    pb.serial_number,
    pb.status,
    pb.battery_level,
    pb.total_cycles,
    pb.total_charge_consumed,
    s.station_name as current_station,
    r.rental_code as current_rental
FROM power_banks pb
LEFT JOIN stations s ON pb.current_station_id = s.id
LEFT JOIN rentals r ON pb.current_rental_id = r.id
ORDER BY pb.serial_number;

-- ============================================================================
-- SECTION 10: LATE FEE CONFIGURATION
-- ============================================================================

-- Get late fee configuration
SELECT
    lfc.id,
    lfc.name,
    lfc.grace_period_minutes,
    lfc.initial_rate_multiplier,
    lfc.escalation_rate_multiplier,
    lfc.escalation_threshold_minutes,
    lfc.max_late_fee_cap,
    lfc.is_active,
    lfc.effective_from
FROM late_fee_configurations lfc
ORDER BY lfc.effective_from DESC;

-- ============================================================================
-- SECTION 11: COMPREHENSIVE RENTAL ANALYSIS
-- ============================================================================

-- Complete rental flow analysis for a specific rental
WITH rental_data AS (
    SELECT
        r.id,
        r.rental_code,
        r.status,
        r.payment_status,
        r.amount_paid,
        r.overdue_amount,
        r.is_returned_on_time,
        rp.payment_model,
        rp.price as package_price,
        rp.duration_minutes as package_duration,
        r.started_at,
        r.ended_at,
        r.due_at,
        u.email as user_email
    FROM rentals r
    JOIN rental_packages rp ON r.package_id = rp.id
    JOIN users u ON r.user_id = u.id
    WHERE r.rental_code = 'RENTAL_CODE_HERE'
)
SELECT
    rd.*,
    EXTRACT(EPOCH FROM (rd.ended_at - rd.started_at))/60 as actual_usage_minutes,
    EXTRACT(EPOCH FROM (rd.ended_at - rd.due_at))/60 as overdue_minutes,
    (SELECT COUNT(*) FROM transactions WHERE related_rental_id = rd.id) as transaction_count,
    (SELECT SUM(amount) FROM transactions WHERE related_rental_id = rd.id AND status = 'SUCCESS') as total_paid,
    (SELECT COUNT(*) FROM rental_extensions WHERE rental_id = rd.id) as extension_count,
    (SELECT SUM(extended_minutes) FROM rental_extensions WHERE rental_id = rd.id) as total_extended_minutes
FROM rental_data rd;

-- ============================================================================
-- SECTION 12: DATA INTEGRITY CHECKS
-- ============================================================================

-- Check for rentals with mismatched payment status
SELECT
    r.rental_code,
    r.status,
    r.payment_status,
    r.amount_paid,
    r.overdue_amount,
    rp.payment_model,
    CASE
        WHEN r.payment_status = 'PAID' AND r.overdue_amount > 0 THEN 'ISSUE: Paid but has overdue'
        WHEN r.payment_status = 'PENDING' AND r.overdue_amount = 0 AND r.status = 'COMPLETED' THEN 'ISSUE: Pending but no overdue'
        WHEN rp.payment_model = 'POSTPAID' AND r.status = 'ACTIVE' AND r.amount_paid > 0 THEN 'ISSUE: Postpaid active with payment'
        ELSE 'OK'
    END as integrity_check
FROM rentals r
JOIN rental_packages rp ON r.package_id = rp.id
WHERE r.user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
ORDER BY r.created_at DESC;

-- Check for transactions without corresponding wallet/point deductions
SELECT
    t.transaction_id,
    t.transaction_type,
    t.amount,
    t.payment_method_type,
    r.rental_code,
    CASE
        WHEN t.payment_method_type IN ('WALLET', 'COMBINATION')
             AND NOT EXISTS (SELECT 1 FROM wallet_transactions wt WHERE wt.transaction_id = t.id)
        THEN 'MISSING: Wallet transaction'
        WHEN t.payment_method_type IN ('POINTS', 'COMBINATION')
             AND NOT EXISTS (SELECT 1 FROM point_transactions pt WHERE pt.description LIKE '%' || r.rental_code || '%')
        THEN 'MISSING: Point transaction'
        ELSE 'OK'
    END as integrity_check
FROM transactions t
LEFT JOIN rentals r ON t.related_rental_id = r.id
WHERE t.user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
  AND t.status = 'SUCCESS'
ORDER BY t.created_at DESC;

-- ============================================================================
-- SECTION 13: PERFORMANCE METRICS
-- ============================================================================

-- User rental statistics
SELECT
    COUNT(*) as total_rentals,
    COUNT(CASE WHEN r.status = 'COMPLETED' THEN 1 END) as completed_rentals,
    COUNT(CASE WHEN r.status = 'CANCELLED' THEN 1 END) as cancelled_rentals,
    COUNT(CASE WHEN r.is_returned_on_time THEN 1 END) as on_time_returns,
    COUNT(CASE WHEN NOT r.is_returned_on_time AND r.status = 'COMPLETED' THEN 1 END) as late_returns,
    ROUND(AVG(EXTRACT(EPOCH FROM (r.ended_at - r.started_at))/60), 2) as avg_usage_minutes,
    SUM(r.amount_paid) as total_spent,
    SUM(r.overdue_amount) as total_late_fees_paid
FROM rentals r
WHERE r.user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
  AND r.ended_at IS NOT NULL;

-- Payment method usage
SELECT
    t.payment_method_type,
    COUNT(*) as usage_count,
    SUM(t.amount) as total_amount
FROM transactions t
WHERE t.user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
  AND t.status = 'SUCCESS'
GROUP BY t.payment_method_type
ORDER BY usage_count DESC;

-- ============================================================================
-- SECTION 14: QUICK LOOKUP QUERIES
-- ============================================================================

-- Find rental by code (quick)
\set rental_code 'ABCD1234'
SELECT rental_code, status, payment_status, amount_paid, overdue_amount
FROM rentals
WHERE rental_code = :'rental_code';

-- Find user by email (quick)
\set user_email 'janak@powerbank.com'
SELECT id, email, username
FROM users
WHERE email = :'user_email';

-- Get user's current balance (quick)
SELECT
    w.balance as wallet,
    p.current_points as points
FROM users u
LEFT JOIN wallets w ON w.user_id = u.id
LEFT JOIN points p ON p.user_id = u.id
WHERE u.email = :'user_email';

-- ============================================================================
-- END OF QUERIES
-- ============================================================================
