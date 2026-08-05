"use client";

import { useEffect, useState } from "react";
import { Bell, Check } from "lucide-react";
import { getMyNotifications, markNotificationRead } from "@/lib/api";
import type { PortalNotification } from "@/lib/types";

const NOTIFICATION_TYPES: Record<string, { label: string; color: string }> = {
  deadline_reminder: { label: "Rappel d'échéance", color: "text-amber-600" },
  document_approved: { label: "Document approuvé", color: "text-green-600" },
  document_rejected: { label: "Document rejeté", color: "text-red-600" },
  status_change: { label: "Changement de statut", color: "text-blue-600" },
  message: { label: "Message", color: "text-purple-600" },
  system: { label: "Système", color: "text-gray-600" },
};

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<PortalNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [markingRead, setMarkingRead] = useState<number | null>(null);

  const load = async () => {
    try {
      const data = await getMyNotifications();
      setNotifications(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur de chargement";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleMarkRead = async (notificationId: number) => {
    setMarkingRead(notificationId);
    try {
      await markNotificationRead(notificationId);
      setNotifications((prev) =>
        prev.map((n) => (n.id === notificationId ? { ...n, is_read: true } : n)),
      );
    } catch (err) {
      console.error("Failed to mark notification as read:", err);
    } finally {
      setMarkingRead(null);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-gray-600">Chargement...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
          {error}
        </div>
      </div>
    );
  }

  const unreadNotifications = notifications.filter((n) => !n.is_read);
  const readNotifications = notifications.filter((n) => n.is_read);

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
        <div className="mb-6 flex items-center gap-3">
          <Bell className="h-8 w-8 text-blue-600" aria-hidden="true" />
          <h1 className="text-3xl font-bold text-gray-900">Notifications</h1>
        </div>

        {notifications.length === 0 ? (
          <div className="rounded-lg border border-gray-200 bg-white p-12 text-center">
            <Bell className="mx-auto mb-4 h-12 w-12 text-gray-400" aria-hidden="true" />
            <p className="text-gray-600">Aucune notification</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Unread */}
            {unreadNotifications.length > 0 && (
              <div>
                <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
                  Non lues ({unreadNotifications.length})
                </h2>
                <div className="space-y-3">
                  {unreadNotifications.map((notification) => {
                    const typeConfig =
                      NOTIFICATION_TYPES[notification.type] || NOTIFICATION_TYPES.system;
                    return (
                      <div
                        key={notification.id}
                        className="rounded-lg border border-blue-200 bg-blue-50 p-4"
                      >
                        <div className="mb-2 flex items-start justify-between">
                          <div>
                            <div className="mb-1 font-medium text-gray-900">
                              {notification.title}
                            </div>
                            <div className={`text-xs font-medium ${typeConfig.color}`}>
                              {typeConfig.label}
                            </div>
                          </div>
                          <button
                            onClick={() => handleMarkRead(notification.id)}
                            disabled={markingRead === notification.id}
                            className="flex items-center gap-1 rounded-md bg-blue-600 px-3 py-1 text-sm font-medium text-white hover:bg-blue-500 disabled:bg-gray-400"
                            aria-label="Marquer comme lu"
                          >
                            <Check className="h-4 w-4" aria-hidden="true" />
                            {markingRead === notification.id ? "..." : "Marquer lu"}
                          </button>
                        </div>
                        <p className="text-sm text-gray-700">{notification.message}</p>
                        {notification.created_at && (
                          <div className="mt-2 text-xs text-gray-500">
                            {new Date(notification.created_at).toLocaleString("fr-CA")}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Read */}
            {readNotifications.length > 0 && (
              <div>
                <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
                  Lues ({readNotifications.length})
                </h2>
                <div className="space-y-3">
                  {readNotifications.map((notification) => {
                    const typeConfig =
                      NOTIFICATION_TYPES[notification.type] || NOTIFICATION_TYPES.system;
                    return (
                      <div
                        key={notification.id}
                        className="rounded-lg border border-gray-100 bg-white p-4"
                      >
                        <div className="mb-2">
                          <div className="mb-1 font-medium text-gray-900">
                            {notification.title}
                          </div>
                          <div className={`text-xs font-medium ${typeConfig.color}`}>
                            {typeConfig.label}
                          </div>
                        </div>
                        <p className="text-sm text-gray-600">{notification.message}</p>
                        {notification.created_at && (
                          <div className="mt-2 text-xs text-gray-400">
                            {new Date(notification.created_at).toLocaleString("fr-CA")}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
