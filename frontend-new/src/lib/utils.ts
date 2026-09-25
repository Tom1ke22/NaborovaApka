import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** „pekaren-novak" → „Pekáreň Novák" sa nedá, ale „Pekaren Novak" áno. */
export function companyNameFromSlug(slug: string | undefined): string {
  if (!slug) return 'Firma'
  return slug
    .replace(/[-_]+/g, ' ')
    .trim()
    .replace(/(^|\s)(\p{L})/gu, (_, sep: string, char: string) => sep + char.toUpperCase())
}

/** Slovenské skloňovanie po číslovke: 1 miesto, 2–4 miesta, 5+ miest. */
export function plural(count: number, one: string, few: string, many: string): string {
  if (count === 1) return one
  if (count >= 2 && count <= 4) return few
  return many
}

/** 1 234 € — nezalomiteľná medzera medzi číslom a menou. */
export function formatMoney(amount: number | string): string {
  return `${Number(amount).toLocaleString('sk-SK')} €`
}

export function formatDate(value: string): string {
  return new Date(value).toLocaleDateString('sk-SK', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

export function formatDateShort(value: string): string {
  return new Date(value).toLocaleDateString('sk-SK')
}

export function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('sk-SK', {
    day: 'numeric',
    month: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
