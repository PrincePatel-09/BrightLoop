import { useEffect, useState, type FormEvent } from "react";
import { Building2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";

type Company = { id: number; name: string; slug: string; legal_name: string | null; email: string | null; phone: string | null; tax_id: string | null; is_active: boolean; user_count: number };
type CompanyAdmin = { id: number; name: string; email: string; is_active: boolean };

export function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [companyAdmins, setCompanyAdmins] = useState<Record<number, CompanyAdmin[]>>({});
  const [form, setForm] = useState({ name: "", slug: "", email: "", tax_id: "" });
  const [adminForm, setAdminForm] = useState({ company_id: "", name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);

  async function load() {
    const rows = await api<Company[]>("/companies");
    setCompanies(rows);
    const adminRows = await Promise.all(rows.map(async company => [company.id, await api<CompanyAdmin[]>(`/companies/${company.id}/admins`)] as const));
    setCompanyAdmins(Object.fromEntries(adminRows));
  }

  useEffect(() => { void load().catch(err => setError(err instanceof ApiError ? err.message : "Unable to load companies")); }, []);

  async function createCompany(event: FormEvent) {
    event.preventDefault();
    setPending(true); setError(""); setMessage("");
    try {
      await api("/companies", { method: "POST", body: JSON.stringify({ ...form, email: form.email || null, tax_id: form.tax_id || null }) });
      setForm({ name: "", slug: "", email: "", tax_id: "" });
      setMessage("Company created.");
      await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to create company"); }
    finally { setPending(false); }
  }

  async function toggleActive(company: Company) {
    setError("");
    try {
      await api(`/companies/${company.id}`, { method: "PATCH", body: JSON.stringify({ is_active: !company.is_active }) });
      await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to update company"); }
  }

  async function createCompanyAdmin(event: FormEvent) {
    event.preventDefault(); setPending(true); setError(""); setMessage("");
    try {
      await api(`/companies/${adminForm.company_id}/admins`, { method: "POST", body: JSON.stringify({ name: adminForm.name, email: adminForm.email, password: adminForm.password }) });
      setAdminForm({ ...adminForm, name: "", email: "", password: "" });
      setMessage("Company administrator account created."); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to create company administrator"); }
    finally { setPending(false); }
  }

  async function toggleCompanyAdmin(companyId: number, member: CompanyAdmin) {
    setError("");
    try {
      await api(`/companies/${companyId}/admins/${member.id}`, { method: "PATCH", body: JSON.stringify({ is_active: !member.is_active }) });
      setMessage(`Company administrator ${member.is_active ? "deactivated" : "activated"}.`); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to update company administrator"); }
  }

  return <div className="space-y-6">
    <div><h1 className="page-title">Companies</h1><p className="mt-1 text-sm text-muted">Manage tenant workspaces and their platform access.</p></div>
    {error && <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-danger">{error}</p>}
    {message && <p role="status" className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-success">{message}</p>}
    <Card>
      <div className="flex items-center gap-3"><div className="rounded-xl bg-sky p-2 text-primary"><Building2 className="h-4 w-4" /></div><div><h2 className="font-semibold">Add company workspace</h2><p className="mt-1 text-xs text-muted">Company records are the boundary for future products, staff, customers, and billing data.</p></div></div>
      <form className="mt-5 grid gap-4 md:grid-cols-4" onSubmit={createCompany}>
        <div className="space-y-1.5"><Label htmlFor="company-name">Name</Label><Input id="company-name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required /></div>
        <div className="space-y-1.5"><Label htmlFor="company-slug">Slug</Label><Input id="company-slug" pattern="[a-z0-9-]+" value={form.slug} onChange={e => setForm({ ...form, slug: e.target.value.toLowerCase() })} required /></div>
        <div className="space-y-1.5"><Label htmlFor="company-email">Email</Label><Input id="company-email" type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></div>
        <div className="flex items-end"><Button className="w-full" disabled={pending}>{pending ? "Saving..." : "Create company"}</Button></div>
      </form>
    </Card>
    <Card>
      <div className="flex items-center gap-3"><div className="rounded-xl bg-mint p-2 text-success"><Building2 className="h-4 w-4" /></div><div><h2 className="font-semibold">Assign company administrator</h2><p className="mt-1 text-xs text-muted">The administrator can manage staff and records inside this company only.</p></div></div>
      <form className="mt-5 grid gap-4 md:grid-cols-5" onSubmit={createCompanyAdmin}>
        <div className="space-y-1.5"><Label htmlFor="admin-company">Company</Label><select id="admin-company" className="h-10 w-full rounded-xl border border-line bg-white px-3 text-sm" value={adminForm.company_id} onChange={event => setAdminForm({ ...adminForm, company_id: event.target.value })} required><option value="">Select company</option>{companies.filter(item => item.is_active).map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div>
        <div className="space-y-1.5"><Label htmlFor="admin-name">Name</Label><Input id="admin-name" minLength={2} value={adminForm.name} onChange={event => setAdminForm({ ...adminForm, name: event.target.value })} required /></div>
        <div className="space-y-1.5"><Label htmlFor="admin-email">Email</Label><Input id="admin-email" type="email" value={adminForm.email} onChange={event => setAdminForm({ ...adminForm, email: event.target.value })} required /></div>
        <div className="space-y-1.5"><Label htmlFor="admin-password">Temporary password</Label><Input id="admin-password" type="password" minLength={8} value={adminForm.password} onChange={event => setAdminForm({ ...adminForm, password: event.target.value })} required /></div>
        <div className="flex items-end"><Button className="w-full" disabled={pending}>{pending ? "Saving..." : "Create admin"}</Button></div>
      </form>
      <p className="helper mt-3">Use at least 8 characters with a letter and a number.</p>
    </Card>
    <Card className="overflow-hidden p-0">
      <table className="w-full text-left text-sm"><thead className="bg-canvas text-[13px] font-semibold text-muted"><tr><th className="px-6 py-3">Company</th><th className="px-6 py-3">Slug</th><th className="px-6 py-3">Users</th><th className="px-6 py-3">Status</th><th className="px-6 py-3">Action</th></tr></thead><tbody>{companies.length === 0 ? <tr><td className="px-6 py-8 text-muted" colSpan={5}>No companies yet.</td></tr> : companies.map(company => <tr key={company.id} className="border-t border-line"><td className="px-6 py-3 font-medium">{company.name}<span className="mt-1 block text-xs text-muted">{company.email || "No email configured"}</span></td><td className="px-6 py-3 text-muted">{company.slug}</td><td className="px-6 py-3">{company.user_count}</td><td className="px-6 py-3">{company.is_active ? "Active" : "Suspended"}</td><td className="px-6 py-3"><Button variant="secondary" size="sm" onClick={() => void toggleActive(company)}>{company.is_active ? "Suspend" : "Activate"}</Button></td></tr>)}</tbody></table>
    </Card>
    <div className="space-y-3"><div><h2 className="text-lg font-semibold">Company administrators</h2><p className="mt-1 text-sm text-muted">Manage administrator access for each workspace.</p></div>{companies.map(company => <Card key={`admins-${company.id}`}><div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-semibold">{company.name}</h3><p className="mt-1 text-xs text-muted">{company.slug}</p></div>{!(companyAdmins[company.id] || []).length && <span className="text-sm text-muted">No administrators assigned.</span>}</div>{(companyAdmins[company.id] || []).map(member => <div key={member.id} className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-3"><div><p className="text-sm font-medium">{member.name}</p><p className="text-xs text-muted">{member.email} · {member.is_active ? "Active" : "Inactive"}</p></div><Button size="sm" variant="secondary" onClick={() => void toggleCompanyAdmin(company.id, member)}>{member.is_active ? "Deactivate" : "Activate"}</Button></div>)}</Card>)}</div>
  </div>;
}
