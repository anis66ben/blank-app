import type { Metadata } from "next";
import { Sidebar } from "@/components/layout/sidebar";
import { ThemeProvider } from "@/components/layout/theme-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Concierge Flow — Tour de contrôle",
  description:
    "SaaS de gestion de conciergerie et de location saisonnière : réservations, missions ménage, prestataires, incidents et WhatsApp dans une seule interface.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <body>
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          enableSystem
          disableTransitionOnChange
        >
          <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <div className="flex min-w-0 flex-1 flex-col overflow-y-auto scrollbar-thin">
              {children}
            </div>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
