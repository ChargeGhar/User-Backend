

# Business Rules

Note: This Design Assume that User already is inside the system and existing user can be respective VENDOR/FRANCHAISE as respective Hirarcy Under Chargeghar or Franchasie.

## BR1 - Entity Creation & Ownership Rules

1. ChargeGhar is the root entity and owns the entire system
2. ChargeGhar can create Franchises
3. ChargeGhar can create their own Vendors (Revenue/Non-Revenue)
4. ChargeGhar is responsible for creating all Stations and assign to franchir or vendor and franchise can to therir own vendor
5. Franchise can create their own Vendors (Revenue/Non-Revenue)
7. Vendors cannot create any entities
8. Non-Revenue Vendors do not have dashboard access and Revenue model

## BR2 - Station Assignment Rules

1. ChargeGhar assigns stations to ChargeGhar-level Vendors while creating them
2. Franchise assigns stations to Franchise-level Vendors while creating them
3. Each Vendor can be assigned ONLY ONE station
5. A station can only be assigned to one Vendor at a time

## BR3 - Revenue Model Assignment Rules

1. ChargeGhar apply revenue model to ChargeGhar-level Revenue Vendors while creating them
2. Franchise apply revenue model to Franchise-level Revenue Vendors while creating them
3. Revenue model options: Fixed monthly amount OR Percentage (x%) of station transactions
4. Non-Revenue Vendors have NO revenue model (they earn nothing)
5. Franchise revenue model is defined at Franchise creation (upfront payment + y% share)
6. Revenue models can be use by the respective owner (ChargeGhar or Franchise) while applying t\when they are creating their entries.

## BR4 - Transaction Collection Rules

1. ALL transactions from ALL stations go to ChargeGhar's account
2. User rents powerbank and payment is collected by ChargeGhar
3. Transaction amount is the gross revenue
4. ChargeGhar collects 100% of all transactions regardless of station ownership

## BR5 - VAT & Service Charge Rules

1. VAT is deducted ONLY at ChargeGhar level
2. Service charges are deducted ONLY at ChargeGhar level
3. Franchise does NOT deduct VAT or service charges
4. Net Revenue = Gross Revenue - VAT - Service Charge
5. All revenue sharing calculations use Net Revenue (after VAT/service charge deduction)

## BR6 - Revenue Distribution Rules - ChargeGhar Owned Stations

1. ChargeGhar-owned stations operated by ChargeGhar: 100% net revenue to ChargeGhar
2. ChargeGhar-owned stations operated by Revenue Vendor: Vendor gets (Fixed OR x%), ChargeGhar gets remainder
3. ChargeGhar-owned stations operated by Non-Revenue Vendor: 100% net revenue to ChargeGhar, Vendor gets 0%

## BR7 - Revenue Distribution Rules - Franchise Owned Stations

1. Franchise receives y% of their stations' net revenue from ChargeGhar
2. ChargeGhar receives (100-y)% of franchise stations' net revenue
3. Franchise-owned stations operated by Franchise: Franchise keeps 100% of their y% share
4. Franchise-owned stations operated by Revenue Vendor: Vendor gets (Fixed OR x%) from Franchise's y% share, Franchise keeps remainder
5. Franchise-owned stations operated by Non-Revenue Vendor: Franchise keeps 100% of their y% share, Vendor gets 0%

## BR8 - Payout Responsibility Rules

1. ChargeGhar manages payouts to all Franchises
2. ChargeGhar manages payouts to all ChargeGhar-level Revenue Vendors
3. Franchise manages payouts to all Franchise-level Revenue Vendors
4. Non-Revenue Vendors receive NO payouts from anyone
5. Franchise receives their payout from ChargeGhar BEFORE paying their own vendors
6. All payouts are based on net revenue (after VAT/service charge deduction)

## BR9 - Vendor Type Rules

1. Revenue Vendors have a payment model and receive earnings
2. Revenue Vendors have dashboard access
3. Non-Revenue Vendors have NO payment model and receive NO earnings
4. Non-Revenue Vendors have NO dashboard access
5. Vendor type (Revenue/Non-Revenue) is set at vendor creation
6. Vendor type can be changed by their owner (ChargeGhar or Franchise)

## BR10 - Control & Permission Rules

1. ChargeGhar has full control over: all Franchises, all ChargeGhar Vendors, all ChargeGhar Stations
2. Franchise has control over ONLY: their own Vendors, their own Stations
3. Franchise has NO control over: other Franchises, ChargeGhar's Vendors, ChargeGhar's Stations
4. Revenue Vendors can ONLY view their own station and earnings
5. Revenue Vendors have NO control over station settings or configuration
6. ChargeGhar controls VAT and service charge rates globally
7. Franchise cannot modify VAT or service charge rates

## BR11 - Financial Calculation Rules

1. All revenue calculations are based on Net Revenue (Gross - VAT - Service Charge)
2. Franchise share (y%) is calculated on net revenue of their stations
3. Revenue Vendor percentage (x%) is calculated on net revenue of their station
4. Fixed payment vendors receive the same amount regardless of transactions
5. Percentage payment vendors' earnings vary based on station performance

## BR12 - Reporting & Visibility Rules

1. ChargeGhar can view ALL transactions across the entire system
2. Franchise can view ONLY transactions from their own stations
3. Revenue Vendor can view ONLY transactions from their assigned station
4. Non-Revenue Vendors have NO access to any transaction data
5. ChargeGhar can view all Franchise earnings and payouts
6. Franchise can view all their Vendor earnings and payouts
7. Revenue Vendors can view only their own earnings and payout history

### BR13 - IOT HISTORY

1. **Powerbank Ejection (Perks & Limits):** Need to Make PartnerIotActions table for tracking both partner types in where we can log type [ eject/Reboot/Check/ WiFi Settings ]

2. **Vendor Perk:** Every vendor (Revenue or Non-Revenue) can eject **one powerbank for free, one at a time, per day** via the mobile app with this endpoint `POST /api/rentals/start`.

3. **Franchise Prek**: Franchise have all the control and unlimited ejection from his Dashboard only

4. **Control Rights:** Chargeghar and Franchises have full system control (remote eject/Reboot/Check/ WiFi Settings) and Vendors have only **(remote Reboot/Check/ WiFi Settings)** and for manual ejections must manually contact their Franchise or Chargeghar for operational needs.

- Franchise has unlimited ejections from Dashboard
- Every Vendor (Revenue or Non-Revenue) gets 1 free ejection per day
- FRANCHASIE and Chargeghar have full access 'EJECT', 'REBOOT', 'CHECK', 'WIFI_SETTINGS', 'VOLUME', 'MODE'
- Vendor Can perform: REBOOT, CHECK, WIFI_SETTINGS, VOLUME, MODE
- Both Vendor type Cannot perform: EJECT (except 1 free per day via rental flow) In POST `/api/rentals/start`

------

## Entity Relationship & Flow Table

| Entity                                    | Created By  | Owns Stations            | Assigns Stations To            | Assigns Revenue Model To   | Receives Revenue From                                        | Pays Out To                                  | Has Dashboard         |
| ----------------------------------------- | ----------- | ------------------------ | ------------------------------ | -------------------------- | ------------------------------------------------------------ | -------------------------------------------- | --------------------- |
| **ChargeGhar**                            | System Root | Yes (Multiple)           | ChargeGhar Vendors             | ChargeGhar Revenue Vendors | - All ChargeGhar stations (100%)<br>- Franchise stations ((100-y)%) | - Franchises<br>- ChargeGhar Revenue Vendors | ✅ Admin Dashboard     |
| **Franchise**                             | ChargeGhar  | Yes (Multiple, per deal) | Franchise Vendors              | Franchise Revenue Vendors  | ChargeGhar (y% of franchise stations)                        | Franchise Revenue Vendors                    | ✅ Franchise Dashboard |
| **Revenue Vendor (ChargeGhar-level)**     | ChargeGhar  | No                       | N/A                            | N/A                        | ChargeGhar (Fixed OR x% of station)                          | N/A                                          | ✅ Vendor Dashboard    |
| **Revenue Vendor (Franchise-level)**      | Franchise   | No                       | N/A                            | N/A                        | Franchise (Fixed OR x% of station)                           | N/A                                          | ✅ Vendor Dashboard    |
| **Non-Revenue Vendor (ChargeGhar-level)** | ChargeGhar  | No                       | N/A                            | N/A                        | None (0%)                                                    | N/A                                          | ❌ No Dashboard        |
| **Non-Revenue Vendor (Franchise-level)**  | Franchise   | No                       | N/A                            | N/A                        | None (0%)                                                    | N/A                                          | ❌ No Dashboard        |
| **Station (ChargeGhar-owned)**            | ChargeGhar  | N/A                      | Assigned to ChargeGhar Vendors | N/A                        | Generates revenue for ChargeGhar/Vendor                      | N/A                                          | N/A                   |
| **Station (Franchise-owned)**             | Franchise   | N/A                      | Assigned to Franchise Vendors  | N/A                        | Generates revenue for Franchise/Vendor                       | N/A                                          | N/A                   |

**Table Notes:**

- **Created By**: Who has permission to create this entity
- **Owns Stations**: Can this entity own multiple stations
- **Assigns Stations To**: After creating vendors, who assigns the station
- **Assigns Revenue Model To**: After station assignment, who sets the payment terms
- **Receives Revenue From**: Source and percentage of revenue
- **Pays Out To**: Which entities this entity is responsible for paying
- **Has Dashboard**: Whether this entity has system access

## Critical questions Need to address on Database Schema

- How system get identify **Belongs to** of Entity Under Whome ?
- How system get identify **Belongs to** of payouts and transaction Under Whome ?
- How System get identify **Belongs to** of station under Whome ?

---

# Database Schema

## Core Tables

### 1. Partner

```sql
CREATE TABLE Partner (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type ENUM('chargeghar', 'franchise') NOT NULL,
    user oeToOneField(User)Linked user accountNOT NULL, UNIQUE, on_delete=PROTECT
    parent_id UUID NULL REFERENCES Partner(id) ON DELETE RESTRICT,
    status ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_organization_hierarchy CHECK (
        (type = 'chargeghar' AND parent_id IS NULL) OR
        (type = 'franchise' AND parent_id IS NOT NULL)
    )
);

CREATE INDEX idx_Partner_parent ON Partner(parent_id);
CREATE INDEX idx_Partner_type ON Partner(type);
```

**Business Rules:**

- ChargeGhar: `type = 'chargeghar'` AND `parent_id IS NULL`
- Franchise: `type = 'franchise'` AND `parent_id = ChargeGhar Partner id`

------

### 2. franchise_deals

```sql
CREATE TABLE franchise_deals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    franchise_id UUID NOT NULL UNIQUE REFERENCES Partner(id) ON DELETE RESTRICT,
    upfront_payment DECIMAL(15, 2) NOT NULL,
    franchise_revenue_percentage DECIMAL(5, 2) NOT NULL, -- y%
    chargeghar_revenue_percentage DECIMAL(5, 2) NOT NULL, -- (100-y)%
    max_stations_allowed INT NULL, -- NULL means unlimited
    deal_start_date DATE NOT NULL,
    deal_end_date DATE NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_revenue_percentage_sum CHECK (
        franchise_revenue_percentage + chargeghar_revenue_percentage = 100
    ),
    CONSTRAINT chk_revenue_percentage_range CHECK (
        franchise_revenue_percentage >= 0 AND franchise_revenue_percentage <= 100
    )
);

CREATE INDEX idx_franchise_deals_franchise ON franchise_deals(franchise_id);
```

**Business Rules:**

- One deal per franchise
- `franchise_revenue_percentage` + `chargeghar_revenue_percentage` must equal 100
- Defines the y% share franchise receives

------

### 3. Partner stations

```sql
CREATE TABLE partner_stations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    station ForeignKey(Station)Station being distributedNOT NULL, on_delete=CASCADE
    owner_id UUID NOT NULL REFERENCES Partner(id) ON DELETE RESTRICT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_stations_owner ON stations(owner_id);
```

**Business Rules:**

- `owner_id` references Partner (ChargeGhar or Franchise)
- Station can only have one owner
- Owner controls the station
- One station can be assigned to ONLY ONE vendor
- One vendor can be assigned to ONLY ONE station
- `assigned_by` must be the owner of the station
- Vendor's `parent_org_id` must match `assigned_by`
- Application level validation required for ownership matching

------

### 4. vendors

```sql
CREATE TABLE vendors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_org_id UUID NOT NULL REFERENCES Partner(id) ON DELETE RESTRICT,
    vendor_type ENUM('revenue', 'non_revenue') NOT NULL,
    status ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_vendors_parent_org ON vendors(parent_org_id);
CREATE INDEX idx_vendors_type ON vendors(vendor_type);
CREATE INDEX idx_vendors_status ON vendors(status);
```

**Business Rules:**

- `parent_org_id` is the Partner that created this vendor (ChargeGhar or Franchise)
- `vendor_type = 'revenue'`: Vendor has revenue model and dashboard
- `vendor_type = 'non_revenue'`: Vendor has NO revenue model, NO dashboard, earns 0%

------

### 6. vendor_revenue_models

```sql
CREATE TABLE vendor_revenue_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id UUID NOT NULL UNIQUE REFERENCES vendors(id) ON DELETE RESTRICT,
    payment_type ENUM('fixed', 'percentage') NOT NULL,
    fixed_amount DECIMAL(15, 2) NULL,
    percentage_rate DECIMAL(5, 2) NULL,
    deal_start_date DATE NOT NULL,
    deal_end_date DATE NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_payment_type_fixed CHECK (
        (payment_type = 'fixed' AND fixed_amount IS NOT NULL AND fixed_amount > 0 AND percentage_rate IS NULL) OR
        (payment_type = 'percentage' AND percentage_rate IS NOT NULL AND percentage_rate > 0 AND percentage_rate <= 100 AND fixed_amount IS NULL)
    )
);

CREATE INDEX idx_vendor_revenue_models_vendor ON vendor_revenue_models(vendor_id);
```

**Business Rules:**

- Only for vendors with `vendor_type = 'revenue'`
- If `payment_type = 'fixed'`: `fixed_amount` is required, `percentage_rate` must be NULL
- If `payment_type = 'percentage'`: `percentage_rate` is required, `fixed_amount` must be NULL
- One active revenue model per vendor
- Non-revenue vendors have NO entry in this table

------

### 7. AppConfig (Already Exist)

```sql
-- Pre-populated data
INSERT INTO AppConfig (setting_key, setting_value, description) VALUES
('vat_rate', '13.00', 'VAT percentage rate'),
('service_charge_rate', '5.00', 'Service charge percentage rate');
```

**Business Rules:**

- VAT and service charge rates stored here
- Only ChargeGhar admin can modify
- Global settings applied to all transactions

------

### 8. revenue_transactions

```sql
CREATE TABLE revenue_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    station_id UUID NOT NULL REFERENCES stations(id) ON DELETE RESTRICT,
    transaction_code VARCHAR(100) NOT NULL UNIQUE,
    gross_amount DECIMAL(15, 2) NOT NULL,
    vat_rate DECIMAL(5, 2) NOT NULL,
    vat_amount DECIMAL(15, 2) NOT NULL,
    service_charge_rate DECIMAL(5, 2) NOT NULL,
    service_charge_amount DECIMAL(15, 2) NOT NULL,
    net_amount DECIMAL(15, 2) NOT NULL,
    transaction_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status ENUM('completed', 'pending', 'failed', 'refunded') NOT NULL DEFAULT 'completed',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_transaction_amounts CHECK (
        gross_amount > 0 AND
        vat_amount >= 0 AND
        service_charge_amount >= 0 AND
        net_amount = gross_amount - vat_amount - service_charge_amount
    )
);

CREATE INDEX idx_transactions_station ON transactions(station_id);
CREATE INDEX idx_transactions_date ON transactions(transaction_date);
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_code ON transactions(transaction_code);
```

**Business Rules:**

- All transactions linked to a station
- VAT and service charge rates stored per transaction (historical accuracy)
- `net_amount = gross_amount - vat_amount - service_charge_amount`
- All amounts collected in ChargeGhar account
- Transaction are Based on the Rentals made from `/api/rentals/start` in where partner_stations determines from which Partner is also applying the rules BR6--> NO. 3 || BR7--> NO. 5 conditionally.

------

### 9. revenue_distributions

```sql
CREATE TABLE revenue_distributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE RESTRICT,
    recipient_type ENUM('chargeghar', 'franchise', 'vendor') NOT NULL,
    recipient_id UUID NOT NULL, -- references Partner(id) or vendors(id)
    amount DECIMAL(15, 2) NOT NULL,
    percentage_applied DECIMAL(5, 2) NULL,
    calculation_note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_distribution_amount CHECK (amount >= 0)
);

CREATE INDEX idx_revenue_distributions_transaction ON revenue_distributions(transaction_id);
CREATE INDEX idx_revenue_distributions_recipient ON revenue_distributions(recipient_id, recipient_type);
```

**Business Rules:**

- Records how each transaction's net revenue is distributed
- `recipient_type = 'chargeghar'`: `recipient_id` is ChargeGhar Partner id
- `recipient_type = 'franchise'`: `recipient_id` is Franchise Partner id
- `recipient_type = 'vendor'`: `recipient_id` `type == revenue` is Vendor id
- Multiple entries per transaction (ChargeGhar, Franchise, Vendor shares)
- Sum of all distribution amounts for a transaction should equal transaction net_amount

------

### 10. payouts

```sql
CREATE TABLE payouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payer_id UUID NOT NULL REFERENCES Partner(id) ON DELETE RESTRICT,
    payee_type ENUM('franchise', 'vendor') NOT NULL,
    payee_id UUID NOT NULL, -- references Partner(id) or vendors(id)
    payout_amount DECIMAL(15, 2) NOT NULL,
    payout_period_start DATE NOT NULL,
    payout_period_end DATE NOT NULL,
    payout_date DATE NOT NULL,
    status ENUM('pending', 'completed', 'failed') NOT NULL DEFAULT 'pending',
    payment_method VARCHAR(100),
    payment_reference VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_payout_amount CHECK (payout_amount > 0),
    CONSTRAINT chk_payout_period CHECK (payout_period_end >= payout_period_start)
);

CREATE INDEX idx_payouts_payer ON payouts(payer_id);
CREATE INDEX idx_payouts_payee ON payouts(payee_id, payee_type);
CREATE INDEX idx_payouts_date ON payouts(payout_date);
CREATE INDEX idx_payouts_status ON payouts(status);
```

**Business Rules:**

- ChargeGhar pays: Franchises and ChargeGhar-level Revenue Vendors
- Franchise pays: Franchise-level Revenue Vendors
- `payer_id` is always an Partner (ChargeGhar or Franchise)
- `payee_type = 'franchise'`: `payee_id` is Franchise Partner id
- `payee_type = 'vendor'`: `payee_id` is Vendor id
- Non-revenue vendors have NO entries in this table

---

### **11. Ejection Log**

```sql
CREATE TABLE PartnerIotHistory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    partner_id UUID NOT NULL,
    station_id UUID NOT NULL,
    action_type VARCHAR(20) NOT NULL,
    powerbank_sn VARCHAR(100),
    rental_id UUID,
    is_successful BOOLEAN NOT NULL,
    is_free_ejection BOOLEAN NOT NULL DEFAULT FALSE,
    error_message TEXT,
    request_payload JSON DEFAULT '{}'::json,
    response_data JSON DEFAULT '{}'::json,
    ip_address INET,
    user_agent TEXT,
    FOREIGN KEY (partner_id) REFERENCES Partner(id) ON DELETE CASCADE,
    FOREIGN KEY (station_id) REFERENCES Station(id) ON DELETE CASCADE,
    FOREIGN KEY (rental_id) REFERENCES Rental(id) ON DELETE SET NULL
);

-- Action Type Choices
-- Action type can be 'EJECT', 'REBOOT', 'CHECK', 'WIFI_SETTINGS', 'VOLUME', 'MODE'
```

**Business Rules:**

- Franchise has unlimited ejections from Dashboard
- Every Vendor (Revenue or Non-Revenue) gets 1 free ejection per day
- FRANCHASIE and Chargeghar have full access 'EJECT', 'REBOOT', 'CHECK', 'WIFI_SETTINGS', 'VOLUME', 'MODE'
- Vendor Can perform: REBOOT, CHECK, WIFI_SETTINGS, VOLUME, MODE
- Both Vendor type Cannot perform: EJECT (except 1 free per day via rental flow) In POST `/api/rentals/start`

---

### Core Endpoints

**Admin:**

- GET /api/admin/partners/payouts [In where query, search, filter, under_me and other Franchasie and franchsie based sub vendors] which helps admin to Look all the payouts requetes with clear hirarcy and can monitor overall payouts as well as from him and under him franchise and franchsie based vendor. (Note but admin will process payouts for its own vendors and franchaise only) (Respectively need other payouts endpoints)

- GET api/admin/partners/transaction (under_charghar=true, today, seven days, monthly, yearly and with best MVP search and filters)

- GET /api/admin/users && GET /api/admin/stations (This is already exist into admin api so we can reuse this from admin panel before we send create admin level vendor or franchaise)

- POST api/admin/chargeghar/partners {create partner with partner-type, revinue model, stations } (Need to ensure the no revinue model for `vendor_type != revenue`  and partner_type  == Vendor then no more then 1 ststion assignment) (Respectively need other endpoints)

- IOT endpoints; (This endponits and authiicatate like that so both vendor and franchise and charghar can and use)

  ```sql
  | GET  | `/api/partner/iot/history` | Get partner's IoT action history  |
  | ---- | -------------------------- | --------------------------------- |
  | POST | `/api/internal/iot/reboot`  | Reboot station (Vendor/Franchise) |
  | POST | `/api/internal/iot/check`   | Check station status (Vendor/Franchise)             | for cacjing specific satation current state
  | POST | `/api/internal/iot/wifi/scan`    | Update WiFi settings  (Vendor/Franchise)            | for wifi scan
  | POST | `/api/internal/iot/wifi/connect`    | Update WiFi settings  (Vendor/Franchise)            | for wifi connect
  | POST | `/api/internal/iot/wifi/volume`    | Update WiFi settings  (Vendor/Franchise)            | for wifi total scan volume
  | POST | `/api/internal/iot/eject`   | Eject powerbank (Franchise and Charghar)  | for eject powerbank
  | POST | `/api/internal/iot/wifi/mode`   | Eject powerbank (Franchise and Charghar)  | for sim/wifi mode
  ```

**Franchaise:**

- GET /api/chargeghar/users?search{by email, username, phone} this endpoint will help the Franchaise Dashboard to creating its own vendors from the system.
- GET /api/partner/franchise/stations [To get only my stations]
- GET /api/partner/franchise/payouts [To get the payouts request under me by my vendors]
- GET api/partner/franchise/transaction (today, seven days, monthly, yearly and with best MVP search and filters) [To get the all the transaction made under me by mine or my vendors ststions]
- GET api/partner/franchsine/agreements (Including owns and with its own vendors) can be quey filter
- POST /api/partner/franchise/request/payouts [To request the franchise for payouts with its total earnings (total earnings = own) where franchin can have or not venrods if vendor then also incuding his own vendor franchaise do payout requate so after received by admin it can transfer respectovely as per condition]

**Vendors:**

- GET /api/partner/vendir/stations [To get only my stations]

- GET api/partner/vendor/transaction (today, seven days, monthly, yearly and with best MVP search and filters) [To get the all the transaction made under me]
- GET api/partner/vendor/agreements (to get the own agreement for his respective owner/partner)
- POST /api/partner/franchise/request/payouts [To request the the payout of its own to it respectove owner/partner]
