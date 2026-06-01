import { defineStore } from 'pinia'

const FONT_SIZE_KEY = 'rssreader.readerFontSize'
const THEME_KEY = 'rssreader.readerTheme'
const STARTUP_SYNC_KEY = 'rssreader.startupSyncEnabled'
const TIMED_SYNC_KEY = 'rssreader.timedSyncEnabled'
const TIMED_SYNC_INTERVAL_KEY = 'rssreader.timedSyncIntervalMinutes'
const LAST_STARTUP_SYNC_KEY = 'rssreader.lastStartupSyncAt'

export type ReaderTheme = 'light' | 'dark'

function storedFontSize() {
  const raw = localStorage.getItem(FONT_SIZE_KEY)
  if (raw === null) {
    return 16
  }
  const value = Number(raw)
  return Number.isFinite(value) && value > 0 ? value : 16
}

function storedTheme(): ReaderTheme {
  return localStorage.getItem(THEME_KEY) === 'dark' ? 'dark' : 'light'
}

function storedBoolean(key: string, fallback: boolean) {
  const raw = localStorage.getItem(key)
  if (raw === null) {
    return fallback
  }
  return raw === 'true'
}

function storedSyncInterval() {
  const raw = localStorage.getItem(TIMED_SYNC_INTERVAL_KEY)
  if (raw === null) {
    return 60
  }
  const value = Number(raw)
  return Number.isFinite(value) && value >= 5 ? value : 60
}

export const usePreferencesStore = defineStore('preferences', {
  state: () => ({
    readerFontSize: storedFontSize(),
    readerTheme: storedTheme(),
    startupSyncEnabled: storedBoolean(STARTUP_SYNC_KEY, true),
    timedSyncEnabled: storedBoolean(TIMED_SYNC_KEY, false),
    timedSyncIntervalMinutes: storedSyncInterval()
  }),
  actions: {
    applyPreferences() {
      document.documentElement.style.setProperty('--reader-font-size', `${this.readerFontSize}px`)
      document.body.classList.toggle('theme-dark', this.readerTheme === 'dark')
    },
    setReaderFontSize(value: number) {
      this.readerFontSize = value
      localStorage.setItem(FONT_SIZE_KEY, String(value))
      this.applyPreferences()
    },
    setReaderTheme(value: ReaderTheme) {
      this.readerTheme = value
      localStorage.setItem(THEME_KEY, value)
      this.applyPreferences()
    },
    setStartupSyncEnabled(value: boolean) {
      this.startupSyncEnabled = value
      localStorage.setItem(STARTUP_SYNC_KEY, String(value))
    },
    setTimedSyncEnabled(value: boolean) {
      this.timedSyncEnabled = value
      localStorage.setItem(TIMED_SYNC_KEY, String(value))
    },
    setTimedSyncIntervalMinutes(value: number) {
      const normalized = Number.isFinite(value) && value >= 5 ? Math.floor(value) : 60
      this.timedSyncIntervalMinutes = normalized
      localStorage.setItem(TIMED_SYNC_INTERVAL_KEY, String(normalized))
    },
    shouldRunStartupSync(cooldownMs = 10 * 60 * 1000) {
      const raw = localStorage.getItem(LAST_STARTUP_SYNC_KEY)
      const lastSyncAt = raw ? Number(raw) : 0
      return !Number.isFinite(lastSyncAt) || Date.now() - lastSyncAt >= cooldownMs
    },
    recordStartupSync(timestamp = Date.now()) {
      localStorage.setItem(LAST_STARTUP_SYNC_KEY, String(timestamp))
    }
  }
})
