import React, { useState } from "react";
import { Eye, EyeOff, Loader2, XCircle } from "lucide-react";

import { COLORS } from "../styles/tokens.js";
import { Card } from "../components/shared/Card.jsx";
import { Logo, Vitals } from "../components/shared/Brand.jsx";

import { loginUser, loginAdmin } from "../services/authService.js";

export function Login({ onLogin, onRegister }) {
    // "admin" or "user"
const [role, setRole] = useState("admin");

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");

    const [remember, setRemember] = useState(true);
    const [showPw, setShowPw] = useState(false);

    const [errors, setErrors] = useState({});
    const [loading, setLoading] = useState(false);
    const [authError, setAuthError] = useState("");

    const validate = () => {
        const errs = {};

if (!email.trim()) {
    errs.email = "Email is required.";
} else if (!/^\S+@\S+\.\S+$/.test(email)) {
    errs.email = "Enter a valid email address.";
}

        if (!password) {
            errs.password = "Password is required.";
        } else if (password.length < 6) {
            errs.password = "Password must be at least 6 characters.";
        }

        setErrors(errs);

        return Object.keys(errs).length === 0;
    };

const handleSubmit = async (e) => {
    e.preventDefault();

    setAuthError("");

    if (!validate()) {
        return;
    }

    setLoading(true);

    try {
        let data;

        if (role === "admin") {
            // Staff/Admin login
            data = await loginAdmin(email, password);

            console.log("Admin login successful:", data);

            onLogin({
                ...data.admin,
                role: "admin",
            });
        } else {
            // Patient login
            data = await loginUser(email, password);

            console.log("Patient login successful:", data);

            onLogin({
                ...data.user,
                role: "user",
            });
        }
    } catch (error) {
        console.error("Login error:", error);

        setAuthError(
            error.message ||
            "Incorrect email or password. Please try again."
        );
    } finally {
        setLoading(false);
    }
};

    const handleRoleChange = (newRole) => {
        setRole(newRole);
        setAuthError("");
        setErrors({});
    };

    return (
        <div
            className="min-h-screen w-full flex items-center justify-center px-4"
            style={{ backgroundColor: COLORS.bg }}
        >
            <div className="w-full max-w-md">

                {/* Logo */}
                <div className="flex flex-col items-center mb-8">
                    <Logo size="lg" />

                    <div className="mt-4">
                        <Vitals w={140} h={24} />
                    </div>
                </div>

                <Card className="p-7 sm:p-8">

                    {/* Role Selector */}
                    <div
                        className="flex mb-6 rounded-xl p-1"
                        style={{ backgroundColor: COLORS.bg }}
                    >
                        <button
                            type="button"
                            onClick={() => handleRoleChange("admin")}
                            className="flex-1 rounded-lg py-2 text-sm font-medium transition"
                            style={{
                                backgroundColor:
                                    role === "admin"
                                        ? COLORS.teal
                                        : "transparent",

                                color:
                                    role === "admin"
                                        ? "white"
                                        : COLORS.slate,
                            }}
                        >
                            Staff / Admin
                        </button>

                        <button
                            type="button"
                            onClick={() => handleRoleChange("user")}
                            className="flex-1 rounded-lg py-2 text-sm font-medium transition"
                            style={{
                                backgroundColor:
                                    role === "user"
                                        ? COLORS.teal
                                        : "transparent",

                                color:
                                    role === "user"
                                        ? "white"
                                        : COLORS.slate,
                            }}
                        >
                            Patient
                        </button>
                    </div>

                    {/* Heading */}
                    <h1
                        className="text-xl font-semibold mb-1"
                        style={{ color: COLORS.ink }}
                    >
                        {role === "admin"
                            ? "Staff / Admin sign in"
                            : "Patient sign in"}
                    </h1>

                    <p
                        className="text-sm mb-6"
                        style={{ color: COLORS.slate }}
                    >
                        {role === "admin"
                            ? "Sign in to manage today's queue and hospital resources."
                            : "Sign in to access your CareFlow patient account."}
                    </p>

                    {/* Authentication Error */}
                    {authError && (
                        <div
                            role="alert"
                            className="mb-5 flex items-start gap-2 rounded-xl px-3.5 py-3 text-sm"
                            style={{
                                backgroundColor: COLORS.criticalSoft,
                                color: COLORS.critical,
                            }}
                        >
                            <XCircle className="w-4 h-4 mt-0.5 shrink-0" />

                            <span>{authError}</span>
                        </div>
                    )}

                    {/* Login Form */}
                    <form onSubmit={handleSubmit} noValidate>

                        {/* Email */}
                        <div className="mb-4">
                            <label
                                htmlFor="email"
                                className="block text-sm font-medium mb-1.5"
                                style={{ color: COLORS.ink }}
                            >
                                Email
                            </label>

                            <input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                aria-invalid={!!errors.email}
                                aria-describedby={
                                    errors.email
                                        ? "email-error"
                                        : undefined
                                }
                                placeholder={
                                    role === "admin"
                                        ? "staff@hospital.org"
                                        : "patient@email.com"
                                }
                                className="w-full rounded-xl border px-3.5 py-2.5 text-sm outline-none focus:ring-2 transition"
                                style={{
                                    borderColor: errors.email
                                        ? COLORS.critical
                                        : COLORS.line,

                                    "--tw-ring-color": COLORS.teal,
                                }}
                            />

                            {errors.email && (
                                <p
                                    id="email-error"
                                    className="mt-1.5 text-xs"
                                    style={{
                                        color: COLORS.critical,
                                    }}
                                >
                                    {errors.email}
                                </p>
                            )}
                        </div>

                        {/* Password */}
                        <div className="mb-4">
                            <label
                                htmlFor="password"
                                className="block text-sm font-medium mb-1.5"
                                style={{ color: COLORS.ink }}
                            >
                                Password
                            </label>

                            <div className="relative">

                                <input
                                    id="password"
                                    type={showPw ? "text" : "password"}
                                    value={password}
                                    onChange={(e) =>
                                        setPassword(e.target.value)
                                    }
                                    aria-invalid={!!errors.password}
                                    aria-describedby={
                                        errors.password
                                            ? "password-error"
                                            : undefined
                                    }
                                    placeholder="••••••••"
                                    className="w-full rounded-xl border px-3.5 py-2.5 pr-10 text-sm outline-none focus:ring-2 transition"
                                    style={{
                                        borderColor: errors.password
                                            ? COLORS.critical
                                            : COLORS.line,

                                        "--tw-ring-color": COLORS.teal,
                                    }}
                                />

                                <button
                                    type="button"
                                    onClick={() =>
                                        setShowPw((v) => !v)
                                    }
                                    aria-label={
                                        showPw
                                            ? "Hide password"
                                            : "Show password"
                                    }
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                                >
                                    {showPw ? (
                                        <EyeOff className="w-4 h-4" />
                                    ) : (
                                        <Eye className="w-4 h-4" />
                                    )}
                                </button>

                            </div>

                            {errors.password && (
                                <p
                                    id="password-error"
                                    className="mt-1.5 text-xs"
                                    style={{
                                        color: COLORS.critical,
                                    }}
                                >
                                    {errors.password}
                                </p>
                            )}
                        </div>

                        {/* Remember / Forgot Password */}
                        <div className="flex items-center justify-between mb-6">

                            <label
                                className="flex items-center gap-2 text-sm select-none"
                                style={{ color: COLORS.slate }}
                            >
                                <input
                                    type="checkbox"
                                    checked={remember}
                                    onChange={(e) =>
                                        setRemember(e.target.checked)
                                    }
                                    className="rounded"
                                    style={{
                                        accentColor: COLORS.teal,
                                    }}
                                />

                                Remember me
                            </label>

                            <button
                                type="button"
                                className="text-sm font-medium hover:underline"
                                style={{ color: COLORS.teal }}
                            >
                                Forgot password?
                            </button>

                        </div>

                        {/* Submit */}
                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full flex items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-semibold text-white transition disabled:opacity-70"
                            style={{
                                backgroundColor: COLORS.teal,
                            }}
                        >
                            {loading ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Signing in…
                                </>
                            ) : (
                                "Sign in"
                            )}
                        </button>

                    </form>

                    {/* Account Information */}
<div className="mt-5 text-center">
    <p
        className="text-xs"
        style={{ color: COLORS.slate }}
    >
        Don't have a CareFlow account?
    </p>

    <button
        type="button"
        onClick={() => onRegister(role)}
        className="mt-1 text-sm font-semibold hover:underline"
        style={{ color: COLORS.teal }}
    >
        Register now
    </button>
</div>

                </Card>

                {/* Disclaimer */}
                <p
                    className="text-xs text-center mt-6"
                    style={{ color: COLORS.slate }}
                >
                    CareFlow provides operational estimates and queue-management
                    recommendations. It does not diagnose patients or replace
                    clinical judgment.
                </p>

            </div>
        </div>
    );
}

export default Login;
