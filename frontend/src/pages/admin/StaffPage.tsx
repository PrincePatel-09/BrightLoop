import { useEffect, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";
import type { StaffMember } from "@/types";

export function StaffPage() {
  const [staff, setStaff] = useState<StaffMember[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "" });

  async function load() {
    const rows = await api<StaffMember[]>("/staff");
    setStaff(rows);
  }

  useEffect(() => {
    void load().catch((err) => setError(err instanceof ApiError ? err.message : "Unable to load staff"));
  }, []);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    setPending(true);
    try {
      await api("/staff", { method: "POST", body: JSON.stringify(form) });
      setForm({ name: "", email: "", password: "" });
      setMessage("Staff account created.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to create staff");
    } finally {
      setPending(false);
    }
  }

  async function toggleActive(member: StaffMember) {
    setError("");
    try {
      await api(`/staff/${member.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !member.is_active }),
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to update staff");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Staff accounts</h1>
        <p className="mt-1 text-sm text-muted">Only admins can create or deactivate staff. Staff cannot create other staff accounts.</p>
      </div>
      {error ? <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger">{error}</p> : null}
      {message ? <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-success">{message}</p> : null}
      <Card>
        <h2 className="text-base font-semibold">Create staff</h2>
        <form className="mt-4 grid gap-4 md:grid-cols-4" onSubmit={onCreate}>
          <div className="space-y-1.5">
            <Label htmlFor="name">Name</Label>
            <Input id="name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password">Temporary password</Label>
            <Input
              id="password"
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
            />
          </div>
          <div className="flex items-end">
            <Button type="submit" disabled={pending} className="w-full">
              {pending ? "Saving…" : "Create staff"}
            </Button>
          </div>
        </form>
      </Card>
      <Card className="p-0 overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-canvas text-[13px] font-semibold text-muted">
            <tr>
              <th className="px-6 py-3">Name</th>
              <th className="px-6 py-3">Email</th>
              <th className="px-6 py-3">Status</th>
              <th className="px-6 py-3">Action</th>
            </tr>
          </thead>
          <tbody>
            {staff.length === 0 ? (
              <tr>
                <td className="px-6 py-8 text-muted" colSpan={4}>
                  No staff accounts yet. Create the first one above.
                </td>
              </tr>
            ) : (
              staff.map((member) => (
                <tr key={member.id} className="border-t border-line">
                  <td className="px-6 py-3 font-medium">{member.name}</td>
                  <td className="px-6 py-3">{member.email}</td>
                  <td className="px-6 py-3">{member.is_active ? "Active" : "Inactive"}</td>
                  <td className="px-6 py-3">
                    <Button variant="secondary" size="sm" onClick={() => void toggleActive(member)}>
                      {member.is_active ? "Deactivate" : "Reactivate"}
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
