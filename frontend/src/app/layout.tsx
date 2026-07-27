import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VisaCanada - Gestion d'immigration intelligente",
  description:
    "Plateforme IA pour accompagner les candidats à l'immigration canadienne",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body className="min-h-screen bg-background font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
