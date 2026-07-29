import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface FunctionTraceEntry {
  function: string
  argument_names: string[]
  result_status: string
  duration_ms: number
  final_action: string
}

export interface ProviderInfo {
  mode: 'hosted' | 'local' | 'mock'
  provider_name: string
  model: string
  real_inference: boolean
  latency_ms: number
}

interface AppState {
  language: 'en' | 'mfe'
  profileName: string
  fishingArea: string
  onboarded: boolean
  online: boolean
  lastProvider: ProviderInfo | null
  lastTrace: FunctionTraceEntry[]
  setLanguage: (l: 'en' | 'mfe') => void
  setProfile: (name: string, area: string) => void
  setOnboarded: (v: boolean) => void
  setOnline: (v: boolean) => void
  setLastAnalysis: (p: ProviderInfo, t: FunctionTraceEntry[]) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      language: 'mfe',
      profileName: '',
      fishingArea: '',
      onboarded: false,
      online: typeof navigator !== 'undefined' ? navigator.onLine : true,
      lastProvider: null,
      lastTrace: [],
      setLanguage: (language) => set({ language }),
      setProfile: (profileName, fishingArea) => set({ profileName, fishingArea }),
      setOnboarded: (onboarded) => set({ onboarded }),
      setOnline: (online) => set({ online }),
      setLastAnalysis: (lastProvider, lastTrace) => set({ lastProvider, lastTrace }),
    }),
    { name: 'lamer-konekte', partialize: (s) => ({
      language: s.language, profileName: s.profileName,
      fishingArea: s.fishingArea, onboarded: s.onboarded,
    }) },
  ),
)
