/**
 * Toast — FROZEN.
 *
 * Setup (already done in the shell):  <ToastProvider>…</ToastProvider>
 * Usage:  const toast = useToast(); toast.show('Catch saved', 'success')
 *
 * show(message, tone?, ms?)
 *   tone: 'info' | 'success' | 'warning' | 'danger'   (default 'info')
 *   ms:   auto-dismiss delay, default 5000; pass 0 to require manual dismissal
 *
 * Toasts are announced via the live region, and each carries an icon as well as
 * a colour so the tone survives greyscale. Never put an action a user MUST take
 * in a toast — it disappears.
 */
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { AlertTriangle, CheckCircle2, Info, X, XCircle } from 'lucide-react'
import { useAnnounce } from '../../lib/announce'

export type ToastTone = 'info' | 'success' | 'warning' | 'danger'

interface ToastItem { id: number; message: string; tone: ToastTone }

interface ToastApi { show: (message: string, tone?: ToastTone, ms?: number) => void }

const ToastContext = createContext<ToastApi | null>(null)

const ICONS: Record<ToastTone, ReactNode> = {
  info: <Info size={20} aria-hidden="true" />,
  success: <CheckCircle2 size={20} aria-hidden="true" />,
  warning: <AlertTriangle size={20} aria-hidden="true" />,
  danger: <XCircle size={20} aria-hidden="true" />,
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])
  const announce = useAnnounce()

  const dismiss = useCallback((id: number) => setItems((l) => l.filter((t) => t.id !== id)), [])

  const show = useCallback((message: string, tone: ToastTone = 'info', ms = 5000) => {
    const id = Date.now() + Math.random()
    setItems((l) => [...l, { id, message, tone }])
    announce(message, tone === 'danger' ? 'assertive' : 'polite')
    if (ms > 0) window.setTimeout(() => dismiss(id), ms)
  }, [announce, dismiss])

  const api = useMemo(() => ({ show }), [show])

  return (
    <ToastContext.Provider value={api}>
      {children}
      {items.length > 0 && (
        <div className="lk-toast-region">
          {items.map((t) => (
            <div key={t.id} className={`lk-toast lk-toast--${t.tone}`}>
              {ICONS[t.tone]}
              <span className="lk-toast__body">{t.message}</span>
              <button type="button" className="lk-btn lk-btn--ghost" onClick={() => dismiss(t.id)} aria-label="Dismiss">
                <X size={18} aria-hidden="true" />
              </button>
            </div>
          ))}
        </div>
      )}
    </ToastContext.Provider>
  )
}

/** Degrades to a no-op outside the provider rather than throwing. */
export function useToast(): ToastApi {
  return useContext(ToastContext) ?? { show: () => undefined }
}
