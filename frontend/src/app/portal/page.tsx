"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Home, Bell, Folder, User } from "lucide-react";
import { getMyProfile, getMyDossiers, getMyNotifications } from "@/lib/api";
import type { CandidateProfile, PortalDossierSummary, PortalNotification } from "@/lib/types";

export default function PortalHomePage() {
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [dossiers, setDossiers] = useState<PortalDossierSummary[]>([]);
  const [notifications, setNotifications] = useState<PortalNotification[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [profileData, dossiersData, notificationsData] = await Promise.all([
          getMyProfile(),
          getMyDossiers(),
          getMyNotifications(),
        ]);
        setProfile(profileData);
        setDossiers(dossiersData);
        setNotifications(notificationsData.slice(0, 5)); // Show only 5 most recent
      } catch (err) {
        console.error("Failed to load portal data:", err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-gray-600">Chargement...</div>
      </div>
    );
  }

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="mb-8 flex items-center gap-3">
          <Home className="h-8 w-8 text-blue-600" aria-hidden="true" />
          <h1 className="text-3xl font-bold text-gray-900">
            Bienvenue{profile ? `, ${profile.first_name}` : ""}
          </h1>
        </div>

        <div className="mb-8 grid gap-6 sm:grid-cols-3">
          <Link href="/portal/profile">
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md">
              <div className="flex items-center gap-3">
                <div className="rounded-full bg-blue-100 p-3">
                  <User className="h-6 w-6 text-blue-600" aria-hidden="true" />
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-500">Mon profil</div>
                  <div className="text-xl font-semibold text-gray-900">
                    {profile?.first_name} {profile?.last_name}
                  </div>
                </div>
              </div>
            </div>
          </Link>

          <Link href="/portal/dossiers">
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md">
              <div className="flex items-center gap-3">
                <div className="rounded-full bg-purple-100 p-3">
                  <Folder className="h-6 w-6 text-purple-600" aria-hidden="true" />
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-500">Mes dossiers</div>
                  <div className="text-xl font-semibold text-gray-900">
                    {dossiers.length}
                  </div>
                </div>
              </div>
            </div>
          </Link>

          <Link href="/portal/notifications">
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md">
              <div className="flex items-center gap-3">
                <div className="relative rounded-full bg-amber-100 p-3">
                  <Bell className="h-6 w-6 text-amber-600" aria-hidden="true" />
                  {unreadCount > 0 && (
                    <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs font-bold text-white">
                      {unreadCount}
                    </span>
                  )}
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-500">Notifications</div>
                  <div className="text-xl font-semibold text-gray-900">
                    {unreadCount} non lue{unreadCount !== 1 ? "s" : ""}
                  </div>
                </div>
              </div>
            </div>
          </Link>
        </div>

        {/* Recent Notifications */}
        {notifications.length > 0 && (
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Notifications récentes</h2>
              <Link
                href="/portal/notifications"
                className="text-sm font-medium text-blue-600 hover:text-blue-500"
              >
                Voir toutes
              </Link>
            </div>
            <div className="space-y-3">
              {notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`rounded-lg border p-4 ${
                    notification.is_read
                      ? "border-gray-100 bg-white"
                      : "border-blue-100 bg-blue-50"
                  }`}
                >
                  <div className="mb-1 flex items-start justify-between">
                    <div className="font-medium text-gray-900">{notification.title}</div>
                    {!notification.is_read && (
                      <span className="ml-2 h-2 w-2 flex-shrink-0 rounded-full bg-blue-600" />
                    )}
                  </div>
                  <p className="text-sm text-gray-600">{notification.message}</p>
                  {notification.created_at && (
                    <div className="mt-1 text-xs text-gray-400">
                      {new Date(notification.created_at).toLocaleString("fr-CA")}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Quick Links */}
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          <Link
            href="/portal/dossiers"
            className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-center font-medium text-blue-700 transition-colors hover:bg-blue-100"
          >
            Consulter mes dossiers
          </Link>
          <Link
            href="/crs"
            className="rounded-lg border border-purple-200 bg-purple-50 p-4 text-center font-medium text-purple-700 transition-colors hover:bg-purple-100"
          >
            Calculer mon score CRS
          </Link>
        </div>
      </div>
    </div>
  );
}
