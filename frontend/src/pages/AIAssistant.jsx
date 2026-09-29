import React, { useEffect, useState } from "react";

import { COLORS } from "../styles/tokens.js";
import { createConversation, getConversationMessages, getConversations } from "../services/conversationService.js";
import { getDocumentStatus, sendAIMessage, uploadDocument } from "../services/aiService.js";
import { Card } from "../components/shared/Card.jsx";
import { ConversationList } from "../components/assistant/ConversationList.jsx";
import { MessageList } from "../components/assistant/MessageList.jsx";
import { Composer } from "../components/assistant/Composer.jsx";

const DOC_TYPES = ["application/pdf", "text/plain"];

/** GraphRAG assistant. Replies are generated server-side behind deterministic guardrails. */
export function AIAssistant({ role = "patient" }) {
  const [conversations, setConversations] = useState([]);
  const [selected, setSelected] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [error, setError] = useState("");

  const open = async (conversation) => {
    setSelected(conversation);
    setLoadingMessages(true);
    try {
      setMessages((await getConversationMessages(conversation.id)) || []);
    } catch (e) {
      setError(e.message);
      setMessages([]);
    } finally {
      setLoadingMessages(false);
    }
  };

  useEffect(() => {
    getConversations()
      .then((list) => {
        setConversations(list || []);
        if (list?.length) open(list[0]);
      })
      .catch((e) => setError(e.message));
  }, []);

  const newChat = async () => {
    const c = await createConversation();
    setConversations((prev) => [c, ...prev]);
    setSelected(c);
    setMessages([]);
    return c;
  };

  const send = async (text = draft) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;
    setError("");
    const conversation = selected || (await newChat());
    setMessages((prev) => [...prev, { _id: `temp-${Date.now()}`, role: "user", content: trimmed }]);
    setDraft("");
    setLoading(true);
    try {
      const { response, escalation } = await sendAIMessage(trimmed, conversation.id);
      setMessages((prev) => [...prev, { _id: `a-${Date.now()}`, role: "assistant", content: response, escalation }]);
      setConversations((prev) => prev.map((c) => (c.id === conversation.id && c.title === "New Conversation" ? { ...c, title: trimmed.slice(0, 100) } : c)));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const upload = async (file) => {
    if (!DOC_TYPES.includes(file.type)) return setUploadStatus({ type: "error", message: "Only PDF and TXT files are supported." });
    if (file.size > 10 * 1024 * 1024) return setUploadStatus({ type: "error", message: "File size must be 10 MB or less." });
    setUploading(true);
    setUploadStatus(null);
    try {
      const { document } = await uploadDocument(file);
      let status = document.status;
      for (let i = 0; i < 30 && status === "processing"; i += 1) {
        await new Promise((r) => setTimeout(r, 2000));
        status = (await getDocumentStatus(document.id)).status;
      }
      setUploadStatus(status === "ready"
        ? { type: "success", message: `${file.name} is ready. The assistant can now refer to it.` }
        : { type: status === "failed" ? "error" : "success", message: status === "failed" ? "The document could not be processed." : "Still processing; it will be available shortly." });
    } catch (e) {
      setUploadStatus({ type: "error", message: e.message });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto">
      <header className="mb-4">
        <h1 className="text-2xl font-bold" style={{ color: COLORS.ink }}>AI assistant</h1>
        <p className="text-sm mt-1" style={{ color: COLORS.slate }}>
          Plain-language answers grounded in the clinical knowledge graph and reviewed reference pages.
        </p>
      </header>
      {error && <p role="alert" className="mb-3 text-sm" style={{ color: COLORS.critical }}>{error}</p>}
      <Card className="flex flex-col lg:flex-row overflow-hidden" style={{ minHeight: "65vh" }}>
        <ConversationList conversations={conversations} selectedId={selected?.id} onSelect={open} onNew={newChat} disabled={loading} />
        <section className="flex-1 flex flex-col min-w-0">
          <MessageList messages={messages} loading={loading} loadingMessages={loadingMessages} onSuggestion={(s) => send(s)} />
          <Composer
            value={draft}
            onChange={setDraft}
            onSend={() => send()}
            disabled={loading}
            canUpload={role === "patient"}
            onUpload={upload}
            uploading={uploading}
            uploadStatus={uploadStatus}
          />
        </section>
      </Card>
    </div>
  );
}

export default AIAssistant;
