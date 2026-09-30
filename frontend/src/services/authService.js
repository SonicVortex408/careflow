import { api, tokenStore } from "./apiClient.js";

function persist(token, account) {
    tokenStore.set(token);
    localStorage.setItem("user", JSON.stringify(account));
    localStorage.setItem("role", account.role);
    return account;
}

// Patients and clinicians share one sign-in; the server decides the role.
export async function loginUser(email, password) {
    const data = await api("/auth/login", { method: "POST", body: { email, password }, auth: false });
    return persist(data.token, data.user);
}

export async function loginAdmin(email, password) {
    const data = await api("/auth/admin/login", { method: "POST", body: { email, password }, auth: false });
    return persist(data.token, { ...data.admin, role: "admin" });
}

// Public registration creates patient accounts only.
export async function registerUser({ name, email, password, sex, birthYear }) {
    const data = await api("/auth/register", {
        method: "POST",
        body: { name, email, password, sex: sex || null, birthYear: birthYear ? Number(birthYear) : null },
        auth: false,
    });
    return persist(data.token, data.user);
}

export function logout() {
    tokenStore.clear();
    localStorage.removeItem("user");
    localStorage.removeItem("role");
}

export const getToken = () => tokenStore.get();

export function getStoredUser() {
    try {
        return JSON.parse(localStorage.getItem("user") || "null");
    } catch {
        return null;
    }
}

export async function getCurrentUser() {
    if (!getToken()) return null;
    const data = await api("/users/profile");
    const user = data.user;
    localStorage.setItem("user", JSON.stringify(user));
    localStorage.setItem("role", user.role);
    return user;
}

export async function updateProfile(fields) {
    const data = await api("/users/profile", { method: "PATCH", body: fields });
    localStorage.setItem("user", JSON.stringify(data.user));
    return data.user;
}
