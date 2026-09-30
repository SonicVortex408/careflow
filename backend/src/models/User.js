import { isId, newId, query } from "../config/db.js";

// Patients and clinicians share one table (architecture decision 2);
// platform administrators stay in the separate admins table.
export const USER_ROLES = ["patient", "clinician"];

const COLUMNS = "id, name, email, password, role, sex, birth_year, created_at, updated_at";

export const toUser = (r) =>
    r && {
        id: r.id,
        name: r.name,
        email: r.email,
        password: r.password,
        role: r.role,
        // Optional demographics used for sex-specific reference ranges and cohort inference.
        sex: r.sex,
        birthYear: r.birth_year,
        createdAt: r.created_at,
        updatedAt: r.updated_at,
    };

const one = async (sql, params) => toUser((await query(sql, params)).rows[0]) || null;

const User = {
    findById: (id) => (isId(id) ? one(`SELECT ${COLUMNS} FROM users WHERE id = $1`, [id]) : null),

    findByEmail: (email) => one(`SELECT ${COLUMNS} FROM users WHERE email = $1`, [String(email).trim().toLowerCase()]),

    create: ({ name, email, password, role = "patient", sex = null, birthYear = null }) =>
        one(
            `INSERT INTO users (id, name, email, password, role, sex, birth_year)
             VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING ${COLUMNS}`,
            [newId(), String(name).trim(), String(email).trim().toLowerCase(), password, role, sex, birthYear]
        ),

    /** Update name / sex / birthYear (only the keys present in `fields`). */
    async update(id, fields) {
        const columns = { name: "name", sex: "sex", birthYear: "birth_year" };
        const sets = [];
        const params = [id];
        for (const [key, column] of Object.entries(columns)) {
            if (fields[key] !== undefined) {
                params.push(fields[key]);
                sets.push(`${column} = $${params.length}`);
            }
        }
        if (!sets.length) return User.findById(id);
        return one(`UPDATE users SET ${sets.join(", ")}, updated_at = now() WHERE id = $1 RETURNING ${COLUMNS}`, params);
    },

    listByRole: async (role) =>
        (await query(`SELECT ${COLUMNS} FROM users WHERE role = $1 ORDER BY created_at DESC`, [role])).rows.map(toUser),
};

export default User;
