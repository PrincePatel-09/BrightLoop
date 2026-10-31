# Brightloop MVP implementation checklist

Source of truth: `Brightloop product specification`, expanded by the user's three-workspace feature request. This checklist distinguishes implemented code from items that still need product work or verification. The original hackathon spec deferred multi-company and payment gateways; multi-company isolation is now being implemented for the expanded target.

## MVP scope

### Foundation and access

- [x] React/Vite frontend, FastAPI backend, SQLAlchemy, Alembic and PostgreSQL configuration
- [x] Customer registration, login, JWT refresh/logout, role redirects and server-side role checks
- [x] Password reset with expiring single-use token and optional SMTP delivery
- [x] Admin staff create/list/deactivate workflows
- [x] Customer portal ownership checks for subscriptions, invoices, payments and PDF downloads
- [x] Platform Admin can create/suspend companies, provision company admins, and activate/deactivate company admin accounts
- [x] Company admins and staff have separate roles, route access, and server-side dependencies
- [x] Company ownership on customers, products, quotations, subscriptions, and invoices with a backfill migration
- [x] Company registration selection and inactive-company login blocking
- [x] Company workspace APIs scope customer, catalog, quotation, subscription, invoice, payment, staff, and settings queries by authenticated company

### Catalog and sales

- [x] Product create, edit, deactivate/reactivate and SKU uniqueness
- [x] Product variant create/list/deactivate/reactivate with attribute, name and additional price
- [x] Plan create/edit/deactivate/reactivate with daily, weekly, monthly and yearly periods
- [x] Apply selected product variants to quotations with product-match validation and per-unit surcharges snapshotted into subscriptions/invoices
- [x] Searchable, paginated customer directory and billing contact edits
- [x] Quotations with validity/status, discount code, accept/cancel and subscription conversion
- [x] Multiple same-cadence plan line items in quotations, snapshotted into subscriptions, recurring invoices, and invoice PDFs
- [x] Draft quotation editing for quantity, validity, notes and discount recalculation
- [x] Company-scoped reusable quotation templates with plan, quantity, validity, notes and discount defaults
- [x] Subscription pause/resume/cancel lifecycle, plan feature snapshot and next billing date
- [x] Company Admin product, plan, and variant create/update workflows
- [x] Customer plan catalog scoped to the customer's company and subscription request creation
- [x] Customer pause/resume/cancel/upgrade/downgrade requests with company approval and audit history
- [x] Customer-hosted invoice checkout via Razorpay test-mode order creation and captured-payment verification

### Billing and finance

- [x] Hourly scheduler and staff-triggered billing run
- [x] Unique subscription/period invoices and retry-safe duplicate prevention
- [x] Invoice company/currency, item, tax and discount snapshots
- [x] Invoice PDF generation and role/ownership-checked downloads
- [x] Manual partial/full payments and balance/status updates
- [x] Company-scoped credit notes that adjust invoice balances and can be voided with audit history
- [x] Manual payment refund records that preserve original payments, reduce net received amounts, and reopen invoice balances safely
- [x] Company-scoped fixed/percentage discount rules with minimums, active dates, usage limits, and quote/request application
- [x] Company-scoped currency, invoice prefix, payment terms, and business details used in generated invoices
- [x] Company-specific configurable GST rate and state jurisdiction; invoice snapshots seller/customer GST details and computes CGST/SGST or IGST by state match
- [x] Sequential invoice numbering per company and financial year, protected by a per-company sequence lock
- [ ] Billing run history, failed-job detail/retry UI and invoice send action
- [ ] Multiple payment allocations and automatic refund execution through external payment gateways
- [x] Razorpay test-mode order/signature/capture verification and invoice payment application (mocked integration test)
- [ ] Concurrent billing/discount race-condition coverage on PostgreSQL

### Dashboards, reporting and administration

- [x] Database-backed Admin/Staff KPI cards for customers, active subscriptions, received revenue, outstanding, overdue and upcoming renewals
- [x] Admin overview includes total companies, users, subscriptions, MRR and ARR
- [x] Company overview includes customer/product/subscription counts, revenue, MRR, ARR, and outstanding balance
- [ ] Company revenue charts, renewal/pending-payment queues, and richer operational analytics
- [x] Admin company settings for currency, invoice numbering and payment terms
- [x] Admin-only audit history for key configuration and financial actions
- [x] Admin company registry and staff/customer account administration
- [x] Six-month revenue chart and subscription status breakdown on Admin/Staff dashboards
- [x] Recent activity feed from quotations, invoices and payments
- [ ] Richer Staff action queues
- [x] Date-filtered operational report for revenue, payments, subscriptions and invoices
- [x] Customer detail history for subscriptions, invoices and payments
- [ ] Discount usage reporting
- [x] SMTP invoice notices and password reset email hooks (delivery requires SMTP configuration)
- [x] Company-scoped invoice email action with delivery failure reporting and audit entry
- [x] Company invoice print action opens the authenticated PDF in a print window

### Delivery and verification

- [x] Alembic migrations through `0021_recurring_line_items` (including credit-note/refund ledger, company-scoped templates, and recurring line snapshots)
- [x] Docker Compose configuration and environment example
- [x] README setup, demo accounts and end-to-end demo workflow
- [x] Frontend production build succeeds with Admin, Customer, and Company workspace routes
- [x] API/business workflow tests cover tenant isolation for discounts/templates/products/customers, company provisioning, quotation editing and multiple line items, recurring invoices, invoice sequencing, inter-state GST snapshots, partial/manual payments, credit issuance/voiding, refunds, customer change requests, and mocked Razorpay checkout verification
- [x] Local preview API and Vite preview are running; admin/customer login, variant quotation surcharge, catalogue, invoice list, customer ownership, PDF, report and customer-history endpoints manually exercised
- [ ] Full browser-driven role workflow and visual QA (computer-use browser runtime currently unavailable)
- [ ] Docker Compose startup verification
- [x] Run the project's automated API/business-rule/security tests against isolated SQLite (18 passed)
- [ ] Test the production PostgreSQL configuration (the local preview uses SQLite)

## Future scope from the specification

- Card collection beyond the current Razorpay test-mode flow, proration, usage billing and dunning
- Multi-currency beyond per-company currency configuration
- External accounting integrations, advanced revenue recognition and production email provider setup

## Next implementation order

1. Add billing-run history and failed-run detail/retry.
2. Add external gateway refund execution and multiple-payment allocation workflows.
3. Complete remaining ERP invoice item tax/HSN details, customer shipping addresses, and invoice status transitions.
4. Perform full role-based browser walkthrough and PostgreSQL/Docker verification.
