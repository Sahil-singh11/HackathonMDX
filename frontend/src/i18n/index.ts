import en from './en.json'
import mfe from './mfe.json'
import { useAppStore } from '../store/app'

export type Lang = 'en' | 'mfe'
const dictionaries: Record<Lang, Record<string, string>> = { en, mfe }

export function useT() {
  const lang = useAppStore((s) => s.language)
  return (key: string): string => dictionaries[lang][key] ?? dictionaries.en[key] ?? key
}
