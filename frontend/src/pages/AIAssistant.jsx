import React, {
  useEffect,
  useRef,
  useState,
} from "react";

import {
  Send,
  Plus,
  MessageSquare,
  Loader2,
  Bot,
  Upload,
  FileText,
  CheckCircle,
  AlertCircle,
} from "lucide-react";

import ReactMarkdown from "react-markdown";

import { COLORS } from "../styles/tokens.js";

import {
  getConversations,
  getConversationMessages,
  createConversation,
} from "../services/conversationService.js";

import {
  sendAIMessage,
  uploadDocument,
} from "../services/aiService.js";


export function AIAssistant() {

  const [conversations, setConversations] =
    useState([]);

  const [selectedConversation, setSelectedConversation] =
    useState(null);

  const [messages, setMessages] =
    useState([]);

  const [message, setMessage] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  const [loadingMessages, setLoadingMessages] =
    useState(false);

  /* =========================
     DOCUMENT UPLOAD STATE
  ========================= */

  const [uploading, setUploading] =
    useState(false);

  const [uploadStatus, setUploadStatus] =
    useState(null);

  const [uploadedFile, setUploadedFile] =
    useState(null);

  const fileInputRef =
    useRef(null);


  // =========================
  // LOAD CONVERSATIONS
  // =========================

  useEffect(() => {
    loadConversations();
  }, []);


  const loadConversations = async () => {

    try {

      const data =
        await getConversations();

      setConversations(data || []);

      if (
        data &&
        data.length > 0
      ) {

        await openConversation(
          data[0]
        );
      }

    } catch (error) {

      console.error(
        "Failed to load conversations:",
        error
      );
    }
  };


  // =========================
  // OPEN CONVERSATION
  // =========================

  const openConversation = async (
    conversation
  ) => {

    setSelectedConversation(
      conversation
    );

    setLoadingMessages(true);

    try {

      const data =
        await getConversationMessages(
          conversation.id
        );

      setMessages(
        data || []
      );

    } catch (error) {

      console.error(
        "Failed to load messages:",
        error
      );

      setMessages([]);

    } finally {

      setLoadingMessages(false);
    }
  };


  // =========================
  // NEW CHAT
  // =========================

  const handleNewChat = async () => {

    if (loading) {
      return;
    }

    try {

      const conversation =
        await createConversation();

      setConversations(
        (prev) => [
          conversation,
          ...prev,
        ]
      );

      setSelectedConversation(
        conversation
      );

      setMessages([]);

    } catch (error) {

      console.error(
        "Failed to create conversation:",
        error
      );
    }
  };


  // =========================
  // DOCUMENT UPLOAD
  // =========================

  const handleFileSelect = async (
    event
  ) => {

    const file =
      event.target.files?.[0];

    // Reset input so selecting
    // the same file again works.
    event.target.value = "";

    if (!file) {
      return;
    }


    // =========================
    // CLIENT-SIDE VALIDATION
    // =========================

    const allowedTypes = [
      "application/pdf",
      "text/plain",
    ];

    if (
      !allowedTypes.includes(
        file.type
      )
    ) {

      setUploadStatus({
        type: "error",
        message:
          "Only PDF and TXT files are supported.",
      });

      return;
    }


    // 10 MB limit
    if (
      file.size >
      10 * 1024 * 1024
    ) {

      setUploadStatus({
        type: "error",
        message:
          "File size must be 10 MB or less.",
      });

      return;
    }


    setUploading(true);

    setUploadStatus(null);

    setUploadedFile(file);


    try {

      const result =
        await uploadDocument(
          file
        );

      console.log(
        "Document uploaded:",
        result
      );

      setUploadStatus({
        type: "success",
        message:
          "Medical document uploaded and indexed successfully.",
      });

    } catch (error) {

      console.error(
        "Document upload error:",
        error
      );

      setUploadStatus({
        type: "error",
        message:
          error.message ||
          "Unable to upload document.",
      });

    } finally {

      setUploading(false);
    }
  };


  // =========================
  // SEND MESSAGE
  // =========================

  const handleSend = async (e) => {

    e?.preventDefault();

    const trimmed =
      message.trim();

    if (
      !trimmed ||
      loading ||
      !selectedConversation
    ) {
      return;
    }


    // Optimistic user message
    const tempMessage = {
      _id: `temp-${Date.now()}`,
      role: "user",
      content: trimmed,
      createdAt:
        new Date().toISOString(),
    };


    setMessages(
      (prev) => [
        ...prev,
        tempMessage,
      ]
    );

    setMessage("");

    setLoading(true);


    try {

      const response =
        await sendAIMessage(
          trimmed,
          selectedConversation.id
        );


      // Assistant response
      const assistantMessage = {
        _id: `assistant-${Date.now()}`,
        role: "assistant",
        content: response,
        createdAt:
          new Date().toISOString(),
      };


      setMessages(
        (prev) => [
          ...prev,
          assistantMessage,
        ]
      );


      // Refresh conversation list
      const updated =
        await getConversations();

      setConversations(
        updated || []
      );


      const updatedConversation =
        updated?.find(
          (conversation) =>
            conversation.id ===
            selectedConversation.id
        );


      if (updatedConversation) {

        setSelectedConversation(
          updatedConversation
        );
      }

    } catch (error) {

      console.error(
        "AI error:",
        error
      );


      setMessages(
        (prev) => [
          ...prev,
          {
            _id: `error-${Date.now()}`,
            role: "assistant",
            content:
              "Sorry, I couldn't connect to the AI service. Please try again.",
            createdAt:
              new Date().toISOString(),
          },
        ]
      );

    } finally {

      setLoading(false);
    }
  };


  // =========================
  // RENDER
  // =========================

  return (

    <div className="p-4 sm:p-6">

      <section
        className="rounded-2xl border overflow-hidden bg-white"
        style={{
          borderColor:
            COLORS.line,
        }}
      >

        {/* =========================
            HEADER
        ========================= */}

        <div
          className="flex items-center justify-between px-5 py-4 border-b"
          style={{
            borderColor:
              COLORS.line,
          }}
        >

          <div className="flex items-center gap-3">

            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{
                backgroundColor:
                  COLORS.tealSoft,
              }}
            >

              <Bot
                className="w-5 h-5"
                style={{
                  color:
                    COLORS.teal,
                }}
              />

            </div>


            <div>

              <h2
                className="text-base font-semibold"
                style={{
                  color:
                    COLORS.ink,
                }}
              >
                CareFlow AI
              </h2>


              <p
                className="text-xs"
                style={{
                  color:
                    COLORS.slate,
                }}
              >
                AI Assistant
              </p>

            </div>

          </div>


          <button
            onClick={
              handleNewChat
            }
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
            style={{
              backgroundColor:
                COLORS.teal,
            }}
          >

            <Plus className="w-4 h-4" />

            New Chat

          </button>

        </div>


        {/* =========================
            MAIN AREA
        ========================= */}

        <div className="grid lg:grid-cols-[240px_1fr] min-h-[600px]">


          {/* =========================
              CONVERSATIONS
          ========================= */}

          <aside
            className="border-b lg:border-b-0 lg:border-r"
            style={{
              borderColor:
                COLORS.line,
            }}
          >

            <div
              className="px-4 py-3 text-xs font-semibold uppercase tracking-wide"
              style={{
                color:
                  COLORS.slate,
              }}
            >
              Conversations
            </div>


            <div className="max-h-[500px] overflow-y-auto px-2 pb-3">

              {conversations.length === 0 && (

                <div
                  className="px-3 py-6 text-center text-xs"
                  style={{
                    color:
                      COLORS.slate,
                  }}
                >

                  No conversations yet.

                  <br />

                  Click "New Chat" to start.

                </div>
              )}


              {conversations.map(
                (conversation) => {

                  const active =
                    selectedConversation?.id ===
                    conversation.id;


                  return (

                    <button
                      key={
                        conversation.id
                      }
                      onClick={() =>
                        openConversation(
                          conversation
                        )
                      }
                      disabled={
                        loadingMessages
                      }
                      className="w-full flex items-start gap-3 px-3 py-3 rounded-xl text-left mb-1 transition hover:bg-slate-50"
                      style={{
                        backgroundColor:
                          active
                            ? COLORS.tealSoft
                            : "transparent",

                        color:
                          active
                            ? COLORS.teal
                            : COLORS.ink,
                      }}
                    >

                      <MessageSquare
                        className="w-4 h-4 mt-0.5 shrink-0"
                      />


                      <div className="min-w-0">

                        <div className="text-sm font-medium truncate">

                          {conversation.title ||
                            "New Conversation"}

                        </div>


                        <div
                          className="text-xs mt-1"
                          style={{
                            color:
                              COLORS.slate,
                          }}
                        >

                          {conversation.updatedAt
                            ? new Date(
                                conversation.updatedAt
                              ).toLocaleDateString()
                            : ""}

                        </div>

                      </div>

                    </button>
                  );
                }
              )}

            </div>

          </aside>


          {/* =========================
              CHAT
          ========================= */}

          <div className="flex flex-col min-w-0">


            {/* =========================
                NO CONVERSATION
            ========================= */}

            {!selectedConversation && (

              <div className="flex-1 min-h-[500px] flex items-center justify-center px-6">

                <div className="text-center">

                  <div
                    className="w-14 h-14 mx-auto mb-4 rounded-full flex items-center justify-center"
                    style={{
                      backgroundColor:
                        COLORS.tealSoft,
                    }}
                  >

                    <Bot
                      className="w-7 h-7"
                      style={{
                        color:
                          COLORS.teal,
                      }}
                    />

                  </div>


                  <h3
                    className="text-lg font-semibold"
                    style={{
                      color:
                        COLORS.ink,
                    }}
                  >
                    CareFlow AI
                  </h3>


                  <p
                    className="mt-2 text-sm"
                    style={{
                      color:
                        COLORS.slate,
                    }}
                  >
                    Start a conversation with
                    your AI assistant.
                  </p>


                  <button
                    onClick={
                      handleNewChat
                    }
                    className="mt-5 inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium text-white"
                    style={{
                      backgroundColor:
                        COLORS.teal,
                    }}
                  >

                    <Plus className="w-4 h-4" />

                    Start New Chat

                  </button>

                </div>

              </div>
            )}


            {/* =========================
                SELECTED CONVERSATION
            ========================= */}

            {selectedConversation && (

              <>

                {/* =========================
                    MESSAGES
                ========================= */}

                <div className="flex-1 min-h-[420px] max-h-[550px] overflow-y-auto px-5 py-6">

                  {loadingMessages && (

                    <div className="flex justify-center py-10">

                      <Loader2
                        className="w-5 h-5 animate-spin"
                        style={{
                          color:
                            COLORS.teal,
                        }}
                      />

                    </div>
                  )}


                  {!loadingMessages &&
                    messages.length === 0 && (

                      <div className="h-full flex items-center justify-center">

                        <div className="text-center">

                          <Bot
                            className="w-9 h-9 mx-auto mb-3"
                            style={{
                              color:
                                COLORS.teal,
                            }}
                          />


                          <h3
                            className="font-semibold"
                            style={{
                              color:
                                COLORS.ink,
                            }}
                          >
                            How can I help?
                          </h3>


                          <p
                            className="text-sm mt-1"
                            style={{
                              color:
                                COLORS.slate,
                            }}
                          >
                            Ask me about your
                            medical documents,
                            symptoms, reports,
                            or general medical
                            information.
                          </p>

                        </div>

                      </div>
                  )}


                  <div className="space-y-5">

                    {messages.map(
                      (msg) => {

                        const isUser =
                          msg.role ===
                          "user";


                        return (

                          <div
                            key={
                              msg._id
                            }
                            className={`flex ${
                              isUser
                                ? "justify-end"
                                : "justify-start"
                            }`}
                          >

                            <div
                              className="max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-6"
                              style={{
                                backgroundColor:
                                  isUser
                                    ? COLORS.teal
                                    : COLORS.bg,

                                color:
                                  isUser
                                    ? "white"
                                    : COLORS.ink,

                                border:
                                  isUser
                                    ? "none"
                                    : `1px solid ${COLORS.line}`,
                              }}
                            >

                              {isUser ? (

                                <div className="whitespace-pre-wrap">

                                  {msg.content}

                                </div>

                              ) : (

                                <ReactMarkdown
                                  components={{
                                    p: ({
                                      children,
                                    }) => (
                                      <p className="mb-2 last:mb-0">
                                        {children}
                                      </p>
                                    ),

                                    strong: ({
                                      children,
                                    }) => (
                                      <strong className="font-semibold">
                                        {children}
                                      </strong>
                                    ),

                                    ul: ({
                                      children,
                                    }) => (
                                      <ul className="list-disc pl-5 mb-2 space-y-1">
                                        {children}
                                      </ul>
                                    ),

                                    ol: ({
                                      children,
                                    }) => (
                                      <ol className="list-decimal pl-5 mb-2 space-y-1">
                                        {children}
                                      </ol>
                                    ),

                                    li: ({
                                      children,
                                    }) => (
                                      <li>
                                        {children}
                                      </li>
                                    ),

                                    h1: ({
                                      children,
                                    }) => (
                                      <h1 className="text-lg font-semibold mb-2">
                                        {children}
                                      </h1>
                                    ),

                                    h2: ({
                                      children,
                                    }) => (
                                      <h2 className="text-base font-semibold mb-2">
                                        {children}
                                      </h2>
                                    ),

                                    h3: ({
                                      children,
                                    }) => (
                                      <h3 className="font-semibold mb-1">
                                        {children}
                                      </h3>
                                    ),
                                  }}
                                >
                                  {msg.content}
                                </ReactMarkdown>

                              )}

                            </div>

                          </div>
                        );
                      }
                    )}


                    {/* AI LOADING */}

                    {loading && (

                      <div className="flex justify-start">

                        <div
                          className="rounded-2xl px-4 py-3 border"
                          style={{
                            borderColor:
                              COLORS.line,

                            backgroundColor:
                              COLORS.bg,
                          }}
                        >

                          <Loader2
                            className="w-4 h-4 animate-spin"
                            style={{
                              color:
                                COLORS.teal,
                            }}
                          />

                        </div>

                      </div>
                    )}

                  </div>

                </div>


                {/* =========================
                    UPLOAD STATUS
                ========================= */}

                {uploadStatus && (

                  <div
                    className="px-4 pb-2"
                  >

                    <div
                      className="flex items-center gap-2 text-xs rounded-lg px-3 py-2"
                      style={{
                        backgroundColor:
                          uploadStatus.type ===
                          "success"
                            ? "#f0fdf4"
                            : "#fef2f2",

                        color:
                          uploadStatus.type ===
                          "success"
                            ? "#166534"
                            : "#b91c1c",
                      }}
                    >

                      {uploadStatus.type ===
                      "success" ? (

                        <CheckCircle className="w-4 h-4 shrink-0" />

                      ) : (

                        <AlertCircle className="w-4 h-4 shrink-0" />

                      )}

                      <span>
                        {uploadStatus.message}
                      </span>

                    </div>

                  </div>
                )}


                {/* =========================
                    INPUT AREA
                ========================= */}

                <div
                  className="border-t p-4"
                  style={{
                    borderColor:
                      COLORS.line,
                  }}
                >

                  {/* Hidden file input */}

                  <input
                    ref={
                      fileInputRef
                    }
                    type="file"
                    accept=".pdf,.txt,application/pdf,text/plain"
                    onChange={
                      handleFileSelect
                    }
                    className="hidden"
                  />


                  {/* Selected file */}

                  {uploadedFile && (

                    <div className="mb-3 flex items-center gap-2 text-xs">

                      <FileText
                        className="w-4 h-4"
                        style={{
                          color:
                            COLORS.teal,
                        }}
                      />

                      <span
                        className="truncate"
                        style={{
                          color:
                            COLORS.slate,
                        }}
                      >
                        {uploadedFile.name}
                      </span>

                    </div>
                  )}


                  <form
                    onSubmit={
                      handleSend
                    }
                    className="flex gap-3"
                  >

                    {/* Upload button */}

                    <button
                      type="button"
                      onClick={() =>
                        fileInputRef.current?.click()
                      }
                      disabled={
                        uploading ||
                        loading
                      }
                      title="Upload medical document"
                      className="w-11 h-11 shrink-0 rounded-xl flex items-center justify-center border transition hover:bg-slate-50 disabled:opacity-50"
                      style={{
                        borderColor:
                          COLORS.line,

                        color:
                          COLORS.teal,
                      }}
                    >

                      {uploading ? (

                        <Loader2
                          className="w-4 h-4 animate-spin"
                        />

                      ) : (

                        <Upload
                          className="w-4 h-4"
                        />

                      )}

                    </button>


                    {/* Message input */}

                    <input
                      value={
                        message
                      }
                      onChange={(e) =>
                        setMessage(
                          e.target.value
                        )
                      }
                      disabled={
                        loading
                      }
                      placeholder="Ask CareFlow AI..."
                      className="flex-1 rounded-xl border px-4 py-3 text-sm outline-none focus:ring-2"
                      style={{
                        borderColor:
                          COLORS.line,

                        "--tw-ring-color":
                          COLORS.teal,
                      }}
                    />


                    {/* Send */}

                    <button
                      type="submit"
                      disabled={
                        loading ||
                        !message.trim()
                      }
                      className="w-11 h-11 shrink-0 rounded-xl flex items-center justify-center text-white disabled:opacity-50"
                      style={{
                        backgroundColor:
                          COLORS.teal,
                      }}
                    >

                      {loading ? (

                        <Loader2
                          className="w-4 h-4 animate-spin"
                        />

                      ) : (

                        <Send
                          className="w-4 h-4"
                        />

                      )}

                    </button>

                  </form>


                  {/* Upload hint */}

                  <p
                    className="mt-2 text-[11px]"
                    style={{
                      color:
                        COLORS.slate,
                    }}
                  >
                    Upload a medical report in PDF or TXT format.
                    Maximum size: 10 MB.
                  </p>

                </div>

              </>
            )}

          </div>

        </div>

      </section>

    </div>
  );
}


export default AIAssistant;