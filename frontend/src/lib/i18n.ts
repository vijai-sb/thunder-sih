/* Citizen-warning i18n. Technical dashboard stays English by design.
   Add a language = add one block to warnings.json with identical keys. */
import data from './warnings.json';

export type Lang = 'en' | 'ta' | 'hi';
export const LANGS: { id: Lang; label: string }[] = [
  { id: 'en', label: 'English' },
  { id: 'ta', label: 'தமிழ்' },
  { id: 'hi', label: 'हिन्दी' },
];

type Dict = Record<string, string>;
const table = data as unknown as Record<Lang, Dict>;

export function t(lang: Lang, key: string, vars?: Record<string, string | number>): string {
  let s = table[lang]?.[key] ?? table.en[key] ?? key;
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.replace(`{${k}}`, String(v));
  return s;
}

export function riskKey(risk: string): string {
  return `risk_${risk}`;
}
