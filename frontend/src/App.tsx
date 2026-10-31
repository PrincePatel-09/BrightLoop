import { Navigate, Route, Routes } from "react-router-dom";

import { GuestRoute, ProtectedRoute } from "@/components/ProtectedRoute";
import { AdminLayout, CompanyLayout, CustomerLayout, StaffLayout } from "@/layouts/role-layouts";
import { StaffPage } from "@/pages/admin/StaffPage";
import { ProductsPage } from "@/pages/admin/ProductsPage";
import { CustomersPage } from "@/pages/customers/CustomersPage";
import { QuotationsPage } from "@/pages/sales/QuotationsPage";
import { SubscriptionsPage } from "@/pages/sales/SubscriptionsPage";
import { BillingPage } from "@/pages/billing/BillingPage";
import { CustomerPortalPage } from "@/pages/customer/CustomerPortalPage";
import { CustomerCatalogPage } from "@/pages/customer/CustomerCatalogPage";
import { PricingRulesPage } from "@/pages/admin/PricingRulesPage";
import { SettingsPage } from "@/pages/admin/SettingsPage";
import { AuditPage } from "@/pages/admin/AuditPage";
import { CompaniesPage } from "@/pages/admin/CompaniesPage";
import { ReportsPage } from "@/pages/admin/ReportsPage";
import { CompanyWorkspacePage } from "@/pages/company/CompanyWorkspacePage";
import { ForgotPasswordPage } from "@/pages/auth/ForgotPasswordPage";
import { LoginPage } from "@/pages/auth/LoginPage";
import { RegisterPage } from "@/pages/auth/RegisterPage";
import { ResetPasswordPage } from "@/pages/auth/ResetPasswordPage";
import { RoleDashboard } from "@/pages/dashboards/RoleDashboard";

export default function App() {
  return (
    <Routes>
      <Route element={<GuestRoute />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
      </Route>

      <Route element={<ProtectedRoute roles={["admin"]} />}>
        <Route element={<AdminLayout />}>
          <Route path="/admin/dashboard" element={<RoleDashboard role="admin" />} />
          <Route path="/admin/companies" element={<CompaniesPage />} />
          <Route path="/admin/reports" element={<ReportsPage />} />
          <Route path="/admin/staff" element={<StaffPage />} />
          <Route path="/admin/products" element={<ProductsPage />} />
          <Route path="/admin/customers" element={<CustomersPage />} />
          <Route path="/admin/quotations" element={<QuotationsPage />} />
          <Route path="/admin/subscriptions" element={<SubscriptionsPage />} />
          <Route path="/admin/invoices" element={<BillingPage />} />
          <Route path="/admin/payments" element={<BillingPage />} />
          <Route path="/admin/pricing" element={<PricingRulesPage />} />
          <Route path="/admin/settings" element={<SettingsPage />} />
          <Route path="/admin/audit" element={<AuditPage />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute roles={["staff"]} />}>
        <Route element={<StaffLayout />}>
          <Route path="/staff/dashboard" element={<RoleDashboard role="staff" />} />
          <Route path="/staff/customers" element={<CustomersPage />} />
          <Route path="/staff/quotations" element={<QuotationsPage />} />
          <Route path="/staff/subscriptions" element={<SubscriptionsPage />} />
          <Route path="/staff/invoices" element={<BillingPage />} />
          <Route path="/staff/payments" element={<BillingPage />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute roles={["customer"]} />}>
        <Route path="/my" element={<CustomerLayout />}>
          <Route index element={<Navigate to="/my/dashboard" replace />} />
          <Route path="dashboard" element={<CustomerPortalPage section="dashboard" />} />
          <Route path="catalog" element={<CustomerCatalogPage />} />
          <Route path="subscriptions" element={<CustomerPortalPage section="subscriptions" />} />
          <Route path="invoices" element={<CustomerPortalPage section="invoices" />} />
          <Route path="payments" element={<CustomerPortalPage section="payments" />} />
          <Route path="*" element={<Navigate to="/my/dashboard" replace />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute roles={["company_admin", "company_staff"]} />}>
        <Route element={<CompanyLayout />}>
          <Route path="/company/dashboard" element={<CompanyWorkspacePage section="overview" />} />
          <Route path="/company/products" element={<CompanyWorkspacePage section="products" />} />
          <Route path="/company/customers" element={<CompanyWorkspacePage section="customers" />} />
          <Route path="/company/quotations" element={<CompanyWorkspacePage section="quotations" />} />
          <Route path="/company/discounts" element={<CompanyWorkspacePage section="discounts" />} />
          <Route path="/company/subscriptions" element={<CompanyWorkspacePage section="subscriptions" />} />
          <Route path="/company/requests" element={<CompanyWorkspacePage section="requests" />} />
          <Route path="/company/invoices" element={<CompanyWorkspacePage section="invoices" />} />
          <Route path="/company/payments" element={<CompanyWorkspacePage section="payments" />} />
          <Route path="/company/credits" element={<CompanyWorkspacePage section="credits" />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute roles={["company_admin"]} />}>
        <Route element={<CompanyLayout />}>
          <Route path="/company/settings" element={<CompanyWorkspacePage section="settings" />} />
          <Route path="/company/staff" element={<CompanyWorkspacePage section="staff" />} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
