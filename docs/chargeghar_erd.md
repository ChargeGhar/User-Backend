## ChargeGhar ER Diagram

```mermaid
erDiagram
    Country {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField name
        CharField code
        CharField dial_code
        CharField flag_url
        BooleanField is_active
    }
    AppConfig {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField key
        TextField value
        CharField description
        BooleanField is_active
    }
    AppVersion {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField version
        CharField platform
        BooleanField is_mandatory
        CharField download_url
        TextField release_notes
        DateTimeField released_at
    }
    AppUpdate {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField version
        CharField title
        TextField description
        JSONField features
        BooleanField is_major
        DateTimeField released_at
    }
    AuditLog {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField action
        CharField entity_type
        CharField entity_id
        JSONField old_values
        JSONField new_values
        GenericIPAddressField ip_address
        TextField user_agent
        CharField session_id
    }
    MediaUpload {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField file_url
        CharField file_type
        CharField original_name
        IntegerField file_size
        CharField cloud_provider
        CharField public_id
        JSONField metadata
    }
    User {
        BigAutoField id
        CharField password
        BooleanField is_superuser
        CharField email
        CharField phone_number
        CharField username
        CharField profile_picture
        CharField referral_code
        CharField status
        BooleanField email_verified
        BooleanField phone_verified
        BooleanField is_active
        BooleanField is_staff
        DateTimeField date_joined
        DateTimeField last_login
        CharField google_id
        CharField apple_id
        CharField social_provider
        JSONField social_profile_data
    }
    UserProfile {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField full_name
        DateField date_of_birth
        CharField address
        CharField avatar_url
        BooleanField is_profile_complete
    }
    UserKYC {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField document_type
        CharField document_number
        CharField document_front_url
        CharField document_back_url
        CharField status
        DateTimeField verified_at
        CharField rejection_reason
    }
    UserDevice {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField device_id
        TextField fcm_token
        CharField device_type
        CharField device_name
        CharField app_version
        CharField os_version
        BooleanField is_active
        DateTimeField last_used
    }
    Station {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField station_name
        CharField serial_number
        CharField imei
        DecimalField latitude
        DecimalField longitude
        CharField address
        CharField landmark
        TextField description
        IntegerField total_slots
        CharField status
        BooleanField is_maintenance
        BooleanField is_deleted
        JSONField hardware_info
        DateTimeField last_heartbeat
        TimeField opening_time
        TimeField closing_time
    }
    StationSlot {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        IntegerField slot_number
        CharField status
        IntegerField battery_level
        JSONField slot_metadata
        DateTimeField last_updated
    }
    StationAmenity {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField name
        CharField icon
        CharField description
        BooleanField is_active
    }
    StationAmenityMapping {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        BooleanField is_available
        CharField notes
    }
    StationIssue {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField issue_type
        CharField description
        JSONField images
        CharField priority
        CharField status
        DateTimeField reported_at
        DateTimeField resolved_at
    }
    StationMedia {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField media_type
        CharField title
        CharField description
        BooleanField is_primary
    }
    UserStationFavorite {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
    }
    PowerBank {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField serial_number
        CharField model
        IntegerField capacity_mah
        CharField status
        IntegerField battery_level
        JSONField hardware_info
        DateTimeField last_updated
    }
    Rental {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField rental_code
        CharField status
        CharField payment_status
        DateTimeField started_at
        DateTimeField ended_at
        DateTimeField due_at
        DecimalField amount_paid
        DecimalField overdue_amount
        BooleanField is_returned_on_time
        BooleanField timely_return_bonus_awarded
        JSONField rental_metadata
    }
    RentalExtension {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        IntegerField extended_minutes
        DecimalField extension_cost
        DateTimeField extended_at
    }
    RentalIssue {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField issue_type
        CharField description
        JSONField images
        CharField status
        DateTimeField reported_at
        DateTimeField resolved_at
    }
    RentalLocation {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        DecimalField latitude
        DecimalField longitude
        DecimalField accuracy
        DateTimeField recorded_at
    }
    RentalPackage {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField name
        CharField description
        IntegerField duration_minutes
        DecimalField price
        CharField package_type
        CharField payment_model
        BooleanField is_active
        JSONField package_metadata
    }
    LateFeeConfiguration {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField name
        CharField fee_type
        DecimalField multiplier
        DecimalField flat_rate_per_hour
        IntegerField grace_period_minutes
        DecimalField max_daily_rate
        BooleanField is_active
        JSONField applicable_package_types
        JSONField metadata
    }
    Transaction {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField transaction_id
        CharField transaction_type
        DecimalField amount
        CharField currency
        CharField status
        CharField payment_method_type
        CharField gateway_reference
        JSONField gateway_response
    }
    Wallet {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        DecimalField balance
        CharField currency
        BooleanField is_active
    }
    WalletTransaction {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField transaction_type
        DecimalField amount
        DecimalField balance_before
        DecimalField balance_after
        CharField description
        JSONField metadata
    }
    PaymentIntent {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField intent_id
        CharField intent_type
        DecimalField amount
        CharField currency
        CharField status
        CharField gateway_url
        JSONField intent_metadata
        DateTimeField expires_at
        DateTimeField completed_at
    }
    Refund {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField refund_id
        DecimalField amount
        CharField reason
        CharField status
        TextField admin_notes
        CharField gateway_reference
        DateTimeField requested_at
        DateTimeField processed_at
    }
    PaymentMethod {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField name
        CharField gateway
        BooleanField is_active
        JSONField configuration
        DecimalField min_amount
        DecimalField max_amount
        JSONField supported_currencies
    }
    WithdrawalRequest {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        DecimalField amount
        CharField bank_name
        CharField account_number
        CharField account_holder_name
        DecimalField processing_fee
        DecimalField net_amount
        JSONField account_details
        CharField status
        TextField admin_notes
        DateTimeField requested_at
        DateTimeField processed_at
        CharField gateway_reference
        CharField internal_reference
    }
    WithdrawalLimit {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        DecimalField daily_withdrawn
        DecimalField monthly_withdrawn
        DateField last_daily_reset
        DateField last_monthly_reset
    }
    PointsTransaction {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField transaction_type
        CharField source
        IntegerField points
        IntegerField balance_before
        IntegerField balance_after
        CharField description
        JSONField metadata
    }
    Referral {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField referral_code
        CharField status
        IntegerField inviter_points_awarded
        IntegerField invitee_points_awarded
        BooleanField first_rental_completed
        DateTimeField completed_at
        DateTimeField expires_at
    }
    UserPoints {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        IntegerField current_points
        IntegerField total_points
        DateTimeField last_updated
    }
    NotificationTemplate {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField name
        SlugField slug
        CharField title_template
        TextField message_template
        CharField notification_type
        CharField description
        BooleanField is_active
    }
    NotificationRule {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField notification_type
        BooleanField send_in_app
        BooleanField send_push
        BooleanField send_sms
        BooleanField send_email
        BooleanField is_critical
    }
    Notification {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField title
        TextField message
        CharField notification_type
        JSONField data
        CharField channel
        BooleanField is_read
        DateTimeField read_at
    }
    SMS_FCMLog {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField title
        TextField message
        CharField notification_type
        CharField recipient
        CharField status
        TextField response
        DateTimeField sent_at
    }
    Achievement {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField name
        TextField description
        CharField criteria_type
        IntegerField criteria_value
        CharField reward_type
        IntegerField reward_value
        BooleanField is_active
    }
    UserAchievement {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        IntegerField current_progress
        BooleanField is_unlocked
        DateTimeField unlocked_at
        BooleanField is_claimed
        DateTimeField claimed_at
        IntegerField points_awarded
    }
    UserLeaderboard {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        IntegerField rank
        IntegerField total_rentals
        IntegerField total_points_earned
        IntegerField referrals_count
        IntegerField timely_returns
        DateTimeField last_updated
    }
    Coupon {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField code
        CharField name
        IntegerField points_value
        IntegerField max_uses_per_user
        DateTimeField valid_from
        DateTimeField valid_until
        CharField status
    }
    CouponUsage {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        IntegerField points_awarded
        DateTimeField used_at
    }
    ContentPage {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField page_type
        CharField title
        TextField content
        BooleanField is_active
    }
    FAQ {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField question
        TextField answer
        CharField category
        IntegerField sort_order
        BooleanField is_active
    }
    ContactInfo {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField info_type
        CharField label
        CharField value
        CharField description
        BooleanField is_active
    }
    Banner {
        UUIDField id
        DateTimeField created_at
        DateTimeField updated_at
        CharField title
        CharField description
        CharField image_url
        CharField redirect_url
        IntegerField display_order
        BooleanField is_active
        DateTimeField valid_from
        DateTimeField valid_until
    }
    AdminProfile {
        UUIDField id
        CharField role
        BooleanField is_active
        DateTimeField created_at
        DateTimeField updated_at
    }
    AdminActionLog {
        UUIDField id
        DateTimeField updated_at
        CharField action_type
        CharField target_model
        CharField target_id
        JSONField changes
        TextField description
        CharField ip_address
        CharField user_agent
        DateTimeField created_at
    }
    SystemLog {
        UUIDField id
        DateTimeField updated_at
        CharField level
        CharField module
        TextField message
        JSONField context
        CharField trace_id
        DateTimeField created_at
    }

    AuditLog ||--|{ User : user
    AuditLog ||--|{ User : admin
    MediaUpload ||--|{ StationMedia : stationmedia
    MediaUpload ||--|{ User : uploaded_by
    User ||--|{ AuditLog : audit_logs
    User ||--|{ AuditLog : admin_audit_logs
    User ||--|{ MediaUpload : mediaupload
    User ||--|{ User : user
    User ||--|| UserProfile : profile
    User ||--|| UserKYC : kyc
    User ||--|{ UserKYC : verified_kycs
    User ||--|{ UserDevice : devices
    User ||--|{ StationIssue : stationissue
    User ||--|{ StationIssue : assigned_station_issues
    User ||--|{ UserStationFavorite : favorite_stations
    User ||--|{ Rental : rentals
    User ||--|{ RentalExtension : rentalextension
    User ||--|{ Transaction : transactions
    User ||--|| Wallet : wallet
    User ||--|{ PaymentIntent : payment_intents
    User ||--|{ Refund : requested_refunds
    User ||--|{ Refund : approved_refunds
    User ||--|{ WithdrawalRequest : withdrawal_requests
    User ||--|{ WithdrawalRequest : processed_withdrawals
    User ||--|| WithdrawalLimit : withdrawal_limit
    User ||--|{ PointsTransaction : points_transactions
    User ||--|{ Referral : sent_referrals
    User ||--|{ Referral : received_referrals
    User ||--|| UserPoints : points
    User ||--|{ Notification : notifications
    User ||--|{ SMS_FCMLog : sms_fcm_logs
    User ||--|{ UserAchievement : achievements
    User ||--|| UserLeaderboard : leaderboard
    User ||--|{ CouponUsage : coupon_usages
    User ||--|{ FAQ : created_faqs
    User ||--|{ FAQ : updated_faqs
    User ||--|{ ContactInfo : updated_contact_info
    User ||--|| AdminProfile : admin_profile
    User ||--|{ AdminProfile : created_admin_profiles
    User ||--|{ AdminActionLog : admin_actions
    User ||--|{ User : referred_by
    UserProfile ||--|| User : user
    UserKYC ||--|| User : user
    UserKYC ||--|{ User : verified_by
    UserDevice ||--|{ User : user
    Station ||--|{ StationSlot : slots
    Station ||--|{ StationAmenityMapping : amenity_mappings
    Station ||--|{ StationIssue : issues
    Station ||--|{ StationMedia : media
    Station ||--|{ UserStationFavorite : favorited_by
    Station ||--|{ PowerBank : powerbank
    Station ||--|{ Rental : rentals
    Station ||--|{ Rental : returned_rentals
    StationSlot ||--|{ PowerBank : powerbank
    StationSlot ||--|{ Rental : rental
    StationSlot ||--|{ Station : station
    StationSlot ||--|{ Rental : current_rental
    StationAmenity ||--|{ StationAmenityMapping : stationamenitymapping
    StationAmenityMapping ||--|{ Station : station
    StationAmenityMapping ||--|{ StationAmenity : amenity
    StationIssue ||--|{ Station : station
    StationIssue ||--|{ User : reported_by
    StationIssue ||--|{ User : assigned_to
    StationMedia ||--|{ Station : station
    StationMedia ||--|{ MediaUpload : media_upload
    UserStationFavorite ||--|{ User : user
    UserStationFavorite ||--|{ Station : station
    PowerBank ||--|{ Rental : rental
    PowerBank ||--|{ Station : current_station
    PowerBank ||--|{ StationSlot : current_slot
    Rental ||--|{ StationSlot : stationslot
    Rental ||--|{ RentalExtension : extensions
    Rental ||--|{ RentalIssue : issues
    Rental ||--|{ RentalLocation : locations
    Rental ||--|{ Transaction : transaction
    Rental ||--|{ PaymentIntent : paymentintent
    Rental ||--|{ PointsTransaction : pointstransaction
    Rental ||--|{ User : user
    Rental ||--|{ Station : station
    Rental ||--|{ Station : return_station
    Rental ||--|{ StationSlot : slot
    Rental ||--|{ RentalPackage : package
    Rental ||--|{ PowerBank : power_bank
    RentalExtension ||--|{ Rental : rental
    RentalExtension ||--|{ RentalPackage : package
    RentalExtension ||--|{ User : created_by
    RentalIssue ||--|{ Rental : rental
    RentalLocation ||--|{ Rental : rental
    RentalPackage ||--|{ Rental : rental
    RentalPackage ||--|{ RentalExtension : rentalextension
    Transaction ||--|{ WalletTransaction : wallettransaction
    Transaction ||--|{ Refund : refunds
    Transaction ||--|{ User : user
    Transaction ||--|{ Rental : related_rental
    Wallet ||--|{ WalletTransaction : transactions
    Wallet ||--|| User : user
    WalletTransaction ||--|{ Wallet : wallet
    WalletTransaction ||--|{ Transaction : transaction
    PaymentIntent ||--|{ User : user
    PaymentIntent ||--|{ Rental : related_rental
    Refund ||--|{ Transaction : transaction
    Refund ||--|{ User : requested_by
    Refund ||--|{ User : approved_by
    PaymentMethod ||--|{ WithdrawalRequest : withdrawalrequest
    WithdrawalRequest ||--|{ User : user
    WithdrawalRequest ||--|{ PaymentMethod : payment_method
    WithdrawalRequest ||--|{ User : processed_by
    WithdrawalLimit ||--|| User : user
    PointsTransaction ||--|{ User : user
    PointsTransaction ||--|{ Rental : related_rental
    PointsTransaction ||--|{ Referral : related_referral
    Referral ||--|{ PointsTransaction : pointstransaction
    Referral ||--|{ User : inviter
    Referral ||--|{ User : invitee
    UserPoints ||--|| User : user
    NotificationTemplate ||--|{ Notification : notification
    Notification ||--|{ User : user
    Notification ||--|{ NotificationTemplate : template
    SMS_FCMLog ||--|{ User : user
    Achievement ||--|{ UserAchievement : userachievement
    UserAchievement ||--|{ User : user
    UserAchievement ||--|{ Achievement : achievement
    UserLeaderboard ||--|| User : user
    Coupon ||--|{ CouponUsage : usages
    CouponUsage ||--|{ Coupon : coupon
    CouponUsage ||--|{ User : user
    FAQ ||--|{ User : created_by
    FAQ ||--|{ User : updated_by
    ContactInfo ||--|{ User : updated_by
    AdminProfile ||--|| User : user
    AdminProfile ||--|{ User : created_by
    AdminActionLog ||--|{ User : admin_user
```
