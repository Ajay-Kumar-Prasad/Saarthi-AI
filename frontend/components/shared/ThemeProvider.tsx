"use client"

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react"

type Theme = "light" | "dark"

type ThemeContextValue = {
  hydrated: boolean
  theme: Theme
  setTheme: (theme: Theme) => void
}

const STORAGE_KEY = "saarthi-theme"

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined)

function readStoredTheme(): Theme {
  if (typeof window === "undefined") return "dark"

  const savedTheme = window.localStorage.getItem(STORAGE_KEY)
  return savedTheme === "light" || savedTheme === "dark" ? savedTheme : "dark"
}

function subscribeHydration() {
  return () => undefined
}

function applyTheme(theme: Theme) {
  if (typeof document === "undefined") return

  document.documentElement.classList.toggle("dark", theme === "dark")
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(readStoredTheme)
  const hydrated = useSyncExternalStore(
    subscribeHydration,
    () => true,
    () => false,
  )

  useEffect(() => {
    applyTheme(readStoredTheme())

    const syncTheme = () => {
      const nextTheme = readStoredTheme()
      setThemeState(nextTheme)
      applyTheme(nextTheme)
    }

    window.addEventListener("storage", syncTheme)
    return () => window.removeEventListener("storage", syncTheme)
  }, [])

  useEffect(() => {
    if (!hydrated) return

    window.localStorage.setItem(STORAGE_KEY, theme)
    applyTheme(theme)
  }, [hydrated, theme])

  const setTheme = (nextTheme: Theme) => {
    setThemeState(nextTheme)
  }

  return (
    <ThemeContext.Provider
      value={{
        hydrated,
        theme,
        setTheme,
      }}
    >
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)

  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider")
  }

  return context
}
