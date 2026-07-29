import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { AnnounceProvider } from './lib/announce'
import { ThemeProvider } from './theme'
// Load order is load-bearing. tokens defines the design system, base adds the
// new-code layer, and styles.css (the pre-existing sheet) loads LAST so its
// rules win any collision — that is what keeps existing pages pixel-identical.
import './styles/tokens.css'
import './styles/base.css'
import './styles.css'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AnnounceProvider>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </AnnounceProvider>
      </ThemeProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)

if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => undefined)
  })
}
