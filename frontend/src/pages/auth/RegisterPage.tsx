import { useEffect, useState, type ChangeEvent, type FormEvent, type InputHTMLAttributes } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { api, ApiError } from "@/lib/api";
import { AuthFrame } from "@/pages/auth/LoginPage";

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: "",
    email: "",
    company_name: "",
    company_slug: "",
    password: "",
    confirm_password: "",
  });
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [companies, setCompanies] = useState<{ id: number; name: string; slug: string }[]>([]);
  useEffect(() => {
    void api<{ id: number; name: string; slug: string }[]>("/companies/directory", { skipAuth: true })
      .then(items => { setCompanies(items); setForm(current => ({ ...current, company_slug: current.company_slug || items[0]?.slug || "" })); })
      .catch((err) => setError(err instanceof ApiError
        ? `Unable to load available company workspaces: ${err.message}`
        : "Unable to load available company workspaces. Please refresh and try again."));
  }, []);

  function update(key: keyof typeof form) {
    return (event: ChangeEvent<HTMLInputElement>) => setForm((current) => ({ ...current, [key]: event.target.value }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (form.password !== form.confirm_password) {
      setError("Passwords do not match");
      return;
    }
    setPending(true);
    try {
      await register(form);
      navigate("/my/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to create account");
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthFrame title="Create a customer account" subtitle="Registration always creates a customer portal account. Staff accounts are created by an admin.">
      <form className="space-y-4" onSubmit={onSubmit}>
        {error ? <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger">{error}</p> : null}
        <Field label="Full name" id="name" value={form.name} onChange={update("name")} required />
        <Field label="Email" id="email" type="email" value={form.email} onChange={update("email")} required />
        <div className="space-y-1.5"><Label htmlFor="workspace">Company workspace</Label><select id="workspace" required value={form.company_slug} onChange={event => setForm(current => ({ ...current, company_slug: event.target.value }))} className="h-10 w-full rounded-xl border border-line bg-white px-3 text-sm text-ink"><option value="" disabled>Select a company</option>{companies.map(company => <option key={company.id} value={company.slug}>{company.name}</option>)}</select></div>
        <Field label="Company (optional)" id="company" value={form.company_name} onChange={update("company_name")} />
        <Field label="Password" id="password" type="password" value={form.password} onChange={update("password")} required />
        <Field
          label="Confirm password"
          id="confirm"
          type="password"
          value={form.confirm_password}
          onChange={update("confirm_password")}
          required
        />
        <p className="helper">At least 8 characters, including a letter and a number.</p>
        <Button type="submit" className="w-full" disabled={pending}>
          {pending ? "Creating account…" : "Create account"}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-muted">
        Already have an account?{" "}
        <Link to="/login" className="font-medium text-primary hover:underline">
          Sign in
        </Link>
      </p>
    </AuthFrame>
  );
}

function Field({
  label,
  id,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string; id: string }) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} {...props} />
    </div>
  );
}
