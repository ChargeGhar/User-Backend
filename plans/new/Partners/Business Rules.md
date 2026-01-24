# Business Rules

Note: This Design Assume that User already is inside the system and existing user can be respective VENDOR/FRANCHAISE as respective Hirarcy Under Chargeghar or Franchasie.

## BR1 - Entity Creation & Ownership Rules

1. ChargeGhar is the root entity and owns the entire system
2. ChargeGhar can create Franchises
3. ChargeGhar can create their own Vendors (Revenue/Non-Revenue)
4. ChargeGhar is responsible for creating all Stations and assign to franchir or vendor and franchise can to therir own vendor
5. Franchise can create their own Vendors (Revenue/Non-Revenue)
6. Vendors cannot create any entities
7. Non-Revenue Vendors do not have dashboard access and Revenue model

## BR2 - Station Assignment Rules

1. ChargeGhar assigns stations to ChargeGhar-level Vendors while creating them
2. Franchise assigns stations to Franchise-level Vendors while creating them
3. Each Vendor can be assigned ONLY ONE station
4. A station can only be assigned to one Vendor at a time

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