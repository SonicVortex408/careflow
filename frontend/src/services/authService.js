const API_BASE_URL = "https://careflow-gwxc.onrender.com/api";
/* =========================
   USER AUTHENTICATION
========================= */

export const loginUser = async (email, password) => {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            email,
            password,
        }),
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || "Login failed");
    }

    localStorage.setItem("token", data.token);
    localStorage.setItem("user", JSON.stringify(data.user));
    localStorage.setItem("role", "user");

    return data;
};


/* =========================
   ADMIN AUTHENTICATION
========================= */

export const loginAdmin = async (email, password) => {
    const response = await fetch(`${API_BASE_URL}/auth/admin/login`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            email,
            password,
        }),
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || "Admin login failed");
    }

    localStorage.setItem("token", data.token);
    localStorage.setItem("user", JSON.stringify(data.admin));
    localStorage.setItem("role", "admin");

    return data;
};


/* =========================
   LOGOUT
========================= */

export const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    localStorage.removeItem("role");
};


/* =========================
   LOCAL STORAGE HELPERS
========================= */

export const getToken = () => {
    return localStorage.getItem("token");
};

export const getStoredUser = () => {
    const user = localStorage.getItem("user");

    return user ? JSON.parse(user) : null;
};

export const getRole = () => {
    return localStorage.getItem("role");
};


/* =========================
   CURRENT USER
========================= */

export const getCurrentUser = async () => {
    const token = getToken();
    const role = getRole();

    if (!token || !role) {
        return null;
    }

    const endpoint =
        role === "admin"
            ? `${API_BASE_URL}/admin/profile`
            : `${API_BASE_URL}/users/profile`;

    const response = await fetch(endpoint, {
        method: "GET",
        headers: {
            Authorization: `Bearer ${token}`,
        },
    });

    if (!response.ok) {
        logout();
        return null;
    }

    const data = await response.json();

    return data;
};


/* =========================
   REGISTER USER
========================= */

export const registerUser = async (name, email, password) => {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            name,
            email,
            password,
        }),
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || "Registration failed");
    }

    localStorage.setItem("token", data.token);
    localStorage.setItem("user", JSON.stringify(data.user));
    localStorage.setItem("role", "user");

    return data;
};


/* =========================
   REGISTER ADMIN
========================= */

export const registerAdmin = async (name, email, password) => {
    const response = await fetch(`${API_BASE_URL}/auth/admin/register`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            name,
            email,
            password,
        }),
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || "Admin registration failed");
    }

    localStorage.setItem("token", data.token);
    localStorage.setItem("user", JSON.stringify(data.admin));
    localStorage.setItem("role", "admin");

    return data;
};

