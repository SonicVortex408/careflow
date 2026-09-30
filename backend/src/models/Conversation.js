import { isId, newId, query } from "../config/db.js";

const COLUMNS = "id, user_id, title, thread_id, created_at, updated_at";

const toConversation = (r) =>
    r && { id: r.id, userId: r.user_id, title: r.title, threadId: r.thread_id, createdAt: r.created_at, updatedAt: r.updated_at };

const Conversation = {
    create: async ({ userId, title = "New Conversation", threadId }) =>
        toConversation(
            (
                await query(
                    `INSERT INTO conversations (id, user_id, title, thread_id) VALUES ($1, $2, $3, $4) RETURNING ${COLUMNS}`,
                    [newId(), userId, String(title).trim().slice(0, 100), threadId]
                )
            ).rows[0]
        ),

    /** The conversation, only if it belongs to userId. */
    findOwn: async (id, userId) =>
        isId(id)
            ? toConversation((await query(`SELECT ${COLUMNS} FROM conversations WHERE id = $1 AND user_id = $2`, [id, userId])).rows[0]) || null
            : null,

    listForUser: async (userId) =>
        (await query(`SELECT ${COLUMNS} FROM conversations WHERE user_id = $1 ORDER BY updated_at DESC`, [userId])).rows.map(
            toConversation
        ),

    /** Bump updated_at, optionally renaming. */
    touch: async (id, title) =>
        query(`UPDATE conversations SET title = COALESCE($2, title), updated_at = now() WHERE id = $1`, [
            id,
            title ? String(title).trim().slice(0, 100) : null,
        ]),
};

export default Conversation;
