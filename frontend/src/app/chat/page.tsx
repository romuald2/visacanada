"use client";

import { useCallback, useEffect, useState } from "react";
import { Send, Loader2, BookOpen, Trash2, Plus } from "lucide-react";
import { useAuth } from "@/components/auth/AuthProvider";
import {
  askQuestion,
  getConversations,
  getConversation,
  deleteConversation,
} from "@/lib/api";
import type {
  ConversationSummary,
  Conversation,
  ChatMessage,
} from "@/lib/types";

export default function ChatPage() {
  const { token } = useAuth();
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [currentConversation, setCurrentConversation] =
    useState<Conversation | null>(null);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadConversations = useCallback(async () => {
    if (!token) return;
    try {
      const data = await getConversations({ token });
      setConversations(data);
    } catch (err) {
      console.error("Failed to load conversations:", err);
    } finally {
      setLoadingConversations(false);
    }
  }, [token]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const loadConversation = useCallback(
    async (conversationId: number) => {
      if (!token) return;
      try {
        const data = await getConversation(conversationId, { token });
        setCurrentConversation(data);
        setError(null);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Erreur de chargement";
        setError(message);
      }
    },
    [token],
  );

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || !token || loading) return;

    setLoading(true);
    setError(null);

    try {
      const response = await askQuestion(
        {
          question: question.trim(),
          conversation_id: currentConversation?.id ?? null,
          top_k: 5,
        },
        { token },
      );

      // Reload the conversation to get the updated messages
      await loadConversation(response.conversation_id);

      // If this was a new conversation, reload the list
      if (!currentConversation) {
        await loadConversations();
      }

      setQuestion("");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur d'envoi";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteConversation = async (conversationId: number) => {
    if (!token || !confirm("Supprimer cette conversation ?")) return;

    try {
      await deleteConversation(conversationId, { token });
      await loadConversations();
      if (currentConversation?.id === conversationId) {
        setCurrentConversation(null);
      }
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Erreur de suppression";
      setError(message);
    }
  };

  const handleNewConversation = () => {
    setCurrentConversation(null);
    setQuestion("");
    setError(null);
  };

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Sidebar - Conversations list */}
      <div className="w-80 border-r border-gray-200 bg-gray-50 p-4 overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Conversations</h2>
          <button
            onClick={handleNewConversation}
            className="h-8 w-8 rounded border border-gray-300 hover:bg-gray-100 flex items-center justify-center"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>

        {loadingConversations ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        ) : conversations.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-8">
            Aucune conversation
          </p>
        ) : (
          <div className="space-y-2">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                className={`rounded-lg border p-3 cursor-pointer hover:bg-gray-100 transition-colors ${
                  currentConversation?.id === conv.id
                    ? "bg-gray-100 border-blue-500"
                    : "border-gray-200 bg-white"
                }`}
                onClick={() => loadConversation(conv.id)}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{conv.title}</p>
                    {conv.updated_at && (
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(conv.updated_at).toLocaleDateString("fr-CA")}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={(e: React.MouseEvent) => {
                      e.stopPropagation();
                      handleDeleteConversation(conv.id);
                    }}
                    className="h-6 w-6 rounded hover:bg-gray-200 hover:text-red-600 flex items-center justify-center"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="border-b border-gray-200 p-4 bg-white">
          <div className="flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-blue-600" />
            <h1 className="text-xl font-semibold">
              {currentConversation
                ? currentConversation.title
                : "Assistant IRCC"}
            </h1>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Posez vos questions sur l&apos;immigration canadienne
          </p>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {!currentConversation ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <BookOpen className="h-16 w-16 text-gray-400 mb-4" />
              <h2 className="text-xl font-semibold mb-2">
                Bienvenue sur l&apos;assistant IRCC
              </h2>
              <p className="text-sm text-gray-500 max-w-md">
                Posez vos questions sur les programmes d&apos;immigration, les
                délais de traitement, les exigences documentaires et les
                procédures IRCC.
              </p>
            </div>
          ) : (
            currentConversation.messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))
          )}

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 p-4 bg-white">
          <form onSubmit={handleAsk} className="flex gap-2">
            <input
              type="text"
              value={question}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setQuestion(e.target.value)
              }
              placeholder="Posez votre question..."
              disabled={loading}
              className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
            />
            <button
              type="submit"
              disabled={loading || !question.trim()}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-lg border p-4 ${
          isUser
            ? "bg-blue-600 text-white border-blue-600"
            : "bg-white border-gray-200"
        }`}
      >
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>

        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <p className="text-xs font-medium mb-2 text-gray-600">Sources :</p>
            <div className="space-y-1">
              {message.citations.map((citation, idx) => (
                <div key={idx} className="text-xs text-gray-500">
                  {citation.source_url ? (
                    <a
                      href={citation.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:underline"
                    >
                      [{idx + 1}] {citation.title}
                    </a>
                  ) : (
                    <span>
                      [{idx + 1}] {citation.title}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {message.created_at && (
          <p
            className={`text-xs mt-2 ${isUser ? "text-blue-100" : "text-gray-400"}`}
          >
            {new Date(message.created_at).toLocaleTimeString("fr-CA", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        )}
      </div>
    </div>
  );
}
