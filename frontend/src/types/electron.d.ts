export {}

declare global {
  interface DesktopMarkdownSaveResult {
    canceled: boolean
    filePath?: string
  }

  interface Window {
    rssReaderDesktop?: {
      apiBaseUrl: string
      platform: string
      saveMarkdown?: (payload: { content: string; suggestedFilename: string }) => Promise<DesktopMarkdownSaveResult>
    }
  }
}
