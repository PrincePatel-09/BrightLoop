import { BarChart3, Building2, CreditCard, FileText, LayoutDashboard, Package, Percent, Receipt, RefreshCw, ScrollText, Settings, ShoppingBag, UserRound, Users } from "lucide-react";

import { AppShell } from "@/layouts/AppShell";
import { useAuth } from "@/context/AuthContext";

export function AdminLayout() {
  return (
    <AppShell
      title="Admin"
      items={[
        { to: "/admin/dashboard", label: "Dashboard", icon: LayoutDashboard },
        { to: "/admin/companies", label: "Companies", icon: Building2 },
        { to: "/admin/staff", label: "Staff", icon: Users },
        { to: "/admin/products", label: "Products", icon: Package },
        { to: "/admin/customers", label: "Customers", icon: UserRound },
        { to: "/admin/reports", label: "Reports", icon: BarChart3 },
        { to: "/admin/quotations", label: "Quotations", icon: FileText },
        { to: "/admin/subscriptions", label: "Subscriptions", icon: RefreshCw },
        { to: "/admin/invoices", label: "Invoices", icon: Receipt },
        { to: "/admin/payments", label: "Payments", icon: CreditCard },
        { to: "/admin/pricing", label: "Discounts and tax info", icon: Percent },
        { to: "/admin/settings", label: "Settings", icon: Settings },
        { to: "/admin/audit", label: "Audit history", icon: ScrollText },
      ]}
    />
  );
}

export function StaffLayout() {
  return (
    <AppShell
      title="Staff"
      items={[
        { to: "/staff/dashboard", label: "Dashboard", icon: LayoutDashboard },
        { to: "/staff/customers", label: "Customers", icon: UserRound },
        { to: "/staff/quotations", label: "Quotations", icon: FileText },
        { to: "/staff/subscriptions", label: "Subscriptions", icon: RefreshCw },
        { to: "/staff/invoices", label: "Invoices", icon: Receipt },
        { to: "/staff/payments", label: "Payments", icon: CreditCard },
      ]}
    />
  );
}

export function CustomerLayout() {
  return (
    <AppShell
      variant="portal"
      title="My account"
      items={[
        { to: "/my/dashboard", label: "Home", icon: LayoutDashboard },
        { to: "/my/catalog", label: "Browse plans", icon: ShoppingBag },
        { to: "/my/subscriptions", label: "Subscriptions", icon: RefreshCw },
        { to: "/my/invoices", label: "Invoices", icon: Receipt },
        { to: "/my/payments", label: "Payments", icon: CreditCard },
      ]}
    />
  );
}

export function CompanyLayout() {
  const { user } = useAuth();
  const items = [
    { to: "/company/dashboard", label: "Overview", icon: LayoutDashboard },
    { to: "/company/products", label: "Products", icon: Package },
    { to: "/company/customers", label: "Customers", icon: UserRound },
    { to: "/company/quotations", label: "Quotations", icon: FileText },
    ...(user?.role === "company_admin" ? [{ to: "/company/discounts", label: "Discounts", icon: Percent }] : []),
    { to: "/company/subscriptions", label: "Subscriptions", icon: RefreshCw },
    { to: "/company/requests", label: "Customer requests", icon: ScrollText },
    { to: "/company/invoices", label: "Invoices", icon: Receipt },
    { to: "/company/payments", label: "Payments", icon: CreditCard },
    { to: "/company/credits", label: "Credits and refunds", icon: Receipt },
    ...(user?.role === "company_admin" ? [{ to: "/company/settings", label: "Settings", icon: Settings }] : []),
    ...(user?.role === "company_admin" ? [{ to: "/company/staff", label: "Staff", icon: Users }] : []),
  ];
  return <AppShell title="Company workspace" items={items} />;
}
