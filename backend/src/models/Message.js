import { newId, query } from "../config/db.js";

const COLUMNS = "id, conversation_id, role, content, escalation, created_at, updated_at";

const toMessage = (r) =>
    r && {
        id: r.id,
        conversation: r.conversation_id,
        role: r.role,
        content: r.content,
        // Deterministic escalation computed by the ai-service guardrails.
        escalation: r.escalation,
        createdAt: r.created_at,
        updatedAt: r.updated_at,
    };

const Message = {
    create: async ({ conversationId, role, content, escalation = null }) =>
        toMessage(
            (
                await query(
                    `INSERT INTO messages (id, conversation_id, role, content, escalation) VALUES ($1, $2, $3, $4, $5) RETURNING ${COLUMNS}`,
                    [newId(), conversationId, role, content, escalation === null ? null : JSON.stringify(escalation)]
                )
            ).rows[0]
        ),

    listForConversation: async (conversationId) =>
        (await query(`SELECT ${COLUMNS} FROM messages WHERE conversation_id = $1 ORDER BY created_at, id`, [conversationId])).rows.map(
            toMessage
        ),
};

export default Message;
