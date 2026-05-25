import { defineStore } from 'pinia'

const FONT_SIZE_KEY = 'rssreader.readerFontSize'
const THEME_KEY = 'rssreader.readerTheme'

export type ReaderTheme = 'light' | 'dark'

function storedFontSize() {
  const value = Number(localStorage.getItem(FONT_SIZE_KEY))
  return Number.isFinite(value) ? value : 16
}

function storedTheme(): ReaderTheme {
  return localStorage.getItem(THEME_KEY) === 'dark' ? 'dark' : 'light'
}

export const usePreferencesStore = defineStore('preferences', {
  state: () => ({
    readerFontSize: storedFontSize(),
    readerTheme: storedTheme()
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
    }
  }
})
