# Requirements & Business Rules

This document serves as the final, 1000% accurate source of truth for the Chargeghar platform. It incorporates all business logic nuances, payment hierarchies, and hardware rules to eliminate gaps and assumptions.

---

## 1. Payment Hierarchy & Distribution

- **Centralized Collection:** All user transactions (rentals, top-ups, ad payments) are processed through the **Chargeghar Mobile App** into the main Chargeghar account.
- **Distribution Model:**
  - **Chargeghar -> Franchise:** Chargeghar distributes the agreed share to the Franchise.
  - **Chargeghar -> Direct Vendor:** Chargeghar distributes the share directly to vendors who are not under a franchise.
  - **Franchise -> Sub-Vendor:** The Franchise is solely responsible for paying their sub-vendors. The sub-vendors request payouts through their Franchise's dashboard, and the Franchise manually releases the payment.
- **VAT & Service Charge Logic:**
  - For **Chargeghar-level payouts** (to Franchises or Direct Vendors), the system/admin **deducts VAT and Service Charges** before manual release.
  - For **Franchise-level payouts** (to their Sub-Vendors), the system **does NOT deduct VAT and Service Charges**, as these are handled as internal private distributions or were already addressed at the Chargeghar level.
- **Tracing:** All requests, transactions, revenues, and distributed amounts must be fully traced in the system.

---

## 2. Platform Entity Models

### A. Franchise Model

- **Agreement:** Physical/manual deal. The Franchise pays an **Upfront Amount** (₹X) for a specific number of stations (Y). Admin records this in the system.
- **Revenue Model:** The Franchise pays a specific **percentage of total earnings** to Chargeghar based on the manual agreement. 
- **Payout:** Franchise requests payouts from the Admin when they have sufficient balance.

### B. Vendor Model (Assigned without Pre-payment)

- **Zero Upfront:** Unlike Franchises, Vendors **never pay upfront** and do not "buy" stations. They are assigned a station by the Admin or a Franchise.
- **Revenue Structure (Two Options):**
  1. **Share %:** Vendor receives a specific percentage of earnings (e.g., 2.5% to vendor, balance to Chargeghar/Franchise).
  2. **Fixed Rent (%):** Chargeghar/Franchise takes a fixed cut (e.g., 70%), and the vendor receives the remaining percentage.
- **Vendor Types:** 
  - **Revenue Vendor:** Has a dashboard and payout features.
  - **Non-Revenue Vendor:** Assigned for physical presence; excluded from revenue/dashboard features.
- **Conversion:** A Franchise can transition to a Vendor model after their initial agreement term ends, switching to fixed or percentage-based revenue.

---

## 3. Operations & Hardware Control

### Powerbank Ejection (Perks & Limits)

- **Vendor Perk:** Every vendor (Revenue or Non-Revenue) can eject **one powerbank for free, one at a time, per day** via the mobile app.
- **Control Rights:** Chargeghar and Franchises have full system control (remote eject/lock/unlock). Vendors have **no system control** and must manually contact their Franchise or Chargeghar for operational needs.
- **Swapping Rate Limit:** Users can swap powerbanks across any station. However, each station has a daily rate limit: a user can swap only up to the **total available powerbank count** of that specific station for that day.

### Rental Lifecycle Rules

- **5-Minute Rule:** If a powerbank is returned within **5 minutes**, it is addressed as a potential issue (e.g., faulty bank). System must track this to handle payment adjustments and notifications.
- **Battery Life Cycle:** 1 Cycle = 100% to 0% discharge. 
  - *Tracking:* System must record battery levels at the time of return to track the exact lifecycle of the hardware.
- **Station Monitoring:** The system must track Online/Offline status history and total counts (Rented, Overdue, Cancelled, Ongoing).

---

## 4. Advertisement Workflow

- **Process:** 
  1. User submits an Ad Request in the app.
  2. Admin verifies and coordinates with the user manually.
  3. Admin **inserts the price** into the system and approves/denies.
  4. User sees "Pay" status in the UI and pays via the app.
  5. Ad becomes "Running".
- **Revenue:** Ad payments are traced via transaction/request logs; distribution of ad revenue is handled manually by the Admin.

---

## 5. Light & Heavy Requirements Summary

| Feature               | Implementation Detail                                        |
| :-------------------- | :----------------------------------------------------------- |
| **Station Coupons**   | Junction table to restrict coupons to specific Station IDs.  |
| **Package Discounts** | Station-specific percentage discounts on specific packages (w/ usage limits). |
| **Ad Management**     | Table for user requests + Admin approval/pricing workflow.   |
| **Biometric Auth**    | APIs for biometric login using device-generated tokens.      |
| **User Attribution**  | Ability to assign existing users to specific Vendors or Franchises. |
| **Hardware Display**  | Support for showing approved advertisements on station screens. |

---

**Status:** v3.0 Final | Fully Cross-checked | Zero Gaps | 1000% Accuracy Checked.





















