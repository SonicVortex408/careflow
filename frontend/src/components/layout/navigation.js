import {
  Activity,
  BarChart3,
  Bot,
  ClipboardCheck,
  FileText,
  FileUp,
  HeartPulse,
  ShieldAlert,
  User,
  Users,
} from "lucide-react";

/* Role-driven navigation (patient / clinician / admin). */
export const NAV_BY_ROLE = {
  patient: [
    { key: "dashboard", label: "My results", icon: Activity },
    { key: "upload", label: "Upload lab report", icon: FileUp },
    { key: "symptoms", label: "Symptom check-in", icon: HeartPulse },
    { key: "reports", label: "My reports", icon: FileText },
    { key: "assistant", label: "AI assistant", icon: Bot },
    { key: "profile", label: "My profile", icon: User },
  ],
  clinician: [
    { key: "reviews", label: "Review queue", icon: ClipboardCheck },
    { key: "escalations", label: "Escalations", icon: ShieldAlert },
    { key: "analytics", label: "Cohort analytics", icon: BarChart3 },
    { key: "assistant", label: "AI assistant", icon: Bot },
  ],
  admin: [
    { key: "clinicians", label: "Clinicians", icon: Users },
    { key: "reviews", label: "Review queue", icon: ClipboardCheck },
    { key: "analytics", label: "Cohort analytics", icon: BarChart3 },
  ],
};

export const DEFAULT_PAGE = { patient: "dashboard", clinician: "reviews", admin: "clinicians" };
