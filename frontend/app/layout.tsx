import type { Metadata } from "next"
import "./globals.css"
import Sidebar from "@/components/shared/Sidebar"
import { ThemeProvider } from "@/components/shared/ThemeProvider"
import QueryProvider from "@/components/providers/QueryProvider"

export const metadata: Metadata = {
  title: "Saarthi AI",
  description: "सारथी — Your Personal Guide",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-white text-gray-900 dark:bg-gray-950 dark:text-white flex min-h-screen transition-colors">
        <QueryProvider>
          <ThemeProvider>
            <Sidebar />
            <main className="flex-1 flex flex-col min-h-screen overflow-auto bg-gray-50 dark:bg-gray-950 transition-colors">
              {children}
            </main>
          </ThemeProvider>
        </QueryProvider>
      </body>
    </html>
  )
}
