import { isId, newId, query } from "../config/db.js";

const COLUMNS = "id, name, email, password, created_at, updated_at";

const toAdmin = (r) =>
    r && { id: r.id, name: r.name, email: r.email, password: r.password, createdAt: r.created_at, updatedAt: r.updated_at };

const one = async (sql, params) => toAdmin((await query(sql, params)).rows[0]) || null;

const Admin = {
    findById: (id) => (isId(id) ? one(`SELECT ${COLUMNS} FROM admins WHERE id = $1`, [id]) : null),

    findByEmail: (email) => one(`SELECT ${COLUMNS} FROM admins WHERE email = $1`, [String(email).trim().toLowerCase()]),

    create: ({ name, email, password }) =>
        one(
            `INSERT INTO admins (id, name, email, password) VALUES ($1, $2, $3, $4) RETURNING ${COLUMNS}`,
            [newId(), String(name).trim(), String(email).trim().toLowerCase(), password]
        ),
};

export default Admin;
