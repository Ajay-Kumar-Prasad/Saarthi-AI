import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import Sidebar from "@/components/shared/Sidebar"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "Saarthi AI",
  description: "Your personal AI guide",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-gray-950 text-white flex min-h-screen`}>
        <Sidebar />
        <main className="flex-1 flex flex-col min-h-screen overflow-auto">
          {children}
        </main>
      </body>
    </html>
  )
}
