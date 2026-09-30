import { isId, newId, query } from "../config/db.js";

export const REPORT_STATUSES = [
    "processing",
    "pending_clinician_review",
    "approved",
    "rejected",
    "failed",
];

export const SYNTHETIC_DATA_LABEL =
    "Derived from synthetic data, for research/demo purposes, not clinical guidance.";

const COLUMNS = `r.id, r.patient_id, r.original_name, r.storage_path, r.mime_type, r.size, r.status, r.job_id,
    r.job_error, r.proms, r.interpretation, r.escalation_level, r.review, r.audit_trail, r.synthetic_data_label,
    r.created_at, r.updated_at`;

const PATIENT_COLUMNS = "u.name AS patient_name, u.email AS patient_email, u.sex AS patient_sex, u.birth_year AS patient_birth_year";

const toReport = (r) =>
    r && {
        id: r.id,
        // With a join, `patient` is the patient summary; otherwise just the id.
        patient:
            r.patient_name !== undefined
                ? { id: r.patient_id, name: r.patient_name, email: r.patient_email, sex: r.patient_sex, birthYear: r.patient_birth_year }
                : r.patient_id,
        patientId: r.patient_id,
        originalName: r.original_name,
        storagePath: r.storage_path,
        mimeType: r.mime_type,
        size: r.size,
        status: r.status,
        jobId: r.job_id,
        jobError: r.job_error,
        proms: r.proms,
        interpretation: r.interpretation,
        escalationLevel: r.escalation_level,
        review: r.review,
        auditTrail: r.audit_trail || [],
        syntheticDataLabel: r.synthetic_data_label,
        createdAt: r.created_at,
        updatedAt: r.updated_at,
    };

const json = (value) => (value === null || value === undefined ? null : JSON.stringify(value));

export const auditEntry = (action, { actor = null, actorRole = "system", detail = null } = {}) => ({
    at: new Date().toISOString(),
    actor,
    actorRole,
    action,
    detail,
});

/** Append an audit entry to an in-memory report (persisted by Report.save). */
export function audit(report, action, options) {
    report.auditTrail.push(auditEntry(action, options));
}

const Report = {
    async create({ patientId, originalName, storagePath, mimeType, size, proms = null, auditTrail = [] }) {
        const { rows } = await query(
            `INSERT INTO reports AS r (id, patient_id, original_name, storage_path, mime_type, size, proms, audit_trail, synthetic_data_label)
             VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) RETURNING ${COLUMNS}`,
            [newId(), patientId, originalName, storagePath, mimeType, size, json(proms), json(auditTrail), SYNTHETIC_DATA_LABEL]
        );
        return toReport(rows[0]);
    },

    async findById(id, { withPatient = false } = {}) {
        if (!isId(id)) return null;
        const sql = withPatient
            ? `SELECT ${COLUMNS}, ${PATIENT_COLUMNS} FROM reports r JOIN users u ON u.id = r.patient_id WHERE r.id = $1`
            : `SELECT ${COLUMNS} FROM reports r WHERE r.id = $1`;
        return toReport((await query(sql, [id])).rows[0]) || null;
    },

    /** The report, only if it belongs to patientId. */
    async findOwn(id, patientId) {
        if (!isId(id)) return null;
        return toReport((await query(`SELECT ${COLUMNS} FROM reports r WHERE r.id = $1 AND r.patient_id = $2`, [id, patientId])).rows[0]) || null;
    },

    listForPatient: async (patientId, limit = 100) =>
        (await query(`SELECT ${COLUMNS} FROM reports r WHERE r.patient_id = $1 ORDER BY r.created_at DESC, r.id LIMIT $2`, [patientId, limit])).rows.map(
            toReport
        ),

    listByStatus: async (status, limit = 200) =>
        (
            await query(
                `SELECT ${COLUMNS}, ${PATIENT_COLUMNS} FROM reports r JOIN users u ON u.id = r.patient_id
                 WHERE r.status = $1 ORDER BY r.created_at, r.id LIMIT $2`,
                [status, limit]
            )
        ).rows.map(toReport),

    async listProcessing({ patientId = null, limit = 50 } = {}) {
        const { rows } = await query(
            `SELECT ${COLUMNS} FROM reports r WHERE r.status = 'processing' AND ($1::text IS NULL OR r.patient_id = $1)
             ORDER BY r.created_at LIMIT $2`,
            [patientId, limit]
        );
        return rows.map(toReport);
    },

    latestApproved: async (patientId) =>
        toReport(
            (
                await query(
                    `SELECT ${COLUMNS} FROM reports r WHERE r.patient_id = $1 AND r.status = 'approved'
                     ORDER BY r.updated_at DESC LIMIT 1`,
                    [patientId]
                )
            ).rows[0]
        ) || null,

    /**
     * Persist the mutable fields of `report`. With `expectStatus`, the write only
     * happens if the stored status still equals it (two concurrent polls or two
     * reviewers cannot both apply a transition); returns false when it lost.
     */
    async save(report, { expectStatus } = {}) {
        const { rowCount } = await query(
            `UPDATE reports SET status = $2, job_id = $3, job_error = $4, interpretation = $5, escalation_level = $6,
                 review = $7, audit_trail = $8, updated_at = now()
             WHERE id = $1 AND ($9::text IS NULL OR status = $9)`,
            [
                report.id,
                report.status,
                report.jobId,
                report.jobError,
                json(report.interpretation),
                report.escalationLevel,
                json(report.review),
                json(report.auditTrail),
                expectStatus ?? null,
            ]
        );
        return rowCount === 1;
    },

    /** Atomically append one audit entry without rewriting the rest of the row. */
    appendAudit: (id, entry) =>
        query(`UPDATE reports SET audit_trail = audit_trail || $2::jsonb WHERE id = $1`, [id, JSON.stringify([entry])]),

    remove: (id) => query(`DELETE FROM reports WHERE id = $1`, [id]),
};

export default Report;
