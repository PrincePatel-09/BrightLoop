export type Role = "admin" | "staff" | "customer" | "company_admin" | "company_staff";

export type User = {
  id: number;
  name: string;
  email: string;
  role: Role;
  is_active: boolean;
  customer_id: number | null;
  company_id?: number | null;
  created_at: string;
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type StaffMember = User;
