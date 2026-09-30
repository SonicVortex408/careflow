import { isId, newId, query } from "../config/db.js";

const COLUMNS = "id, user_id, original_name, mime_type, size, storage_path, job_id, status, created_at, updated_at";

const toDocument = (r) =>
    r && {
        id: r.id,
        userId: r.user_id,
        originalName: r.original_name,
        mimeType: r.mime_type,
        size: r.size,
        storagePath: r.storage_path,
        jobId: r.job_id,
        status: r.status,
        createdAt: r.created_at,
        updatedAt: r.updated_at,
    };

const Document = {
    create: async ({ userId, originalName, mimeType, size, storagePath, status = "uploaded" }) =>
        toDocument(
            (
                await query(
                    `INSERT INTO documents (id, user_id, original_name, mime_type, size, storage_path, status)
                     VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING ${COLUMNS}`,
                    [newId(), userId, originalName, mimeType, size, storagePath, status]
                )
            ).rows[0]
        ),

    findOwn: async (id, userId) =>
        isId(id)
            ? toDocument((await query(`SELECT ${COLUMNS} FROM documents WHERE id = $1 AND user_id = $2`, [id, userId])).rows[0]) || null
            : null,

    update: async (id, { status, jobId }) =>
        toDocument(
            (
                await query(
                    `UPDATE documents SET status = COALESCE($2, status), job_id = COALESCE($3, job_id), updated_at = now()
                     WHERE id = $1 RETURNING ${COLUMNS}`,
                    [id, status ?? null, jobId ?? null]
                )
            ).rows[0]
        ),
};

export default Document;
