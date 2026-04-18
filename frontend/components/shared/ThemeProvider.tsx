"use client"

import { ThemeProvider as NextThemesProvider, useTheme } from "next-themes"
import type { ReactNode } from "react"

export function ThemeProvider({ children }: { children: ReactNode }) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="dark"
      enableSystem={false}
      enableColorScheme={false}
      storageKey="saarthi-theme"
    >
      {children}
    </NextThemesProvider>
  )
}

export { useTheme }
