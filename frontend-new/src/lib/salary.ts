/**
 * Mzda z textového poľa.
 *
 * Zámerne nie `type="number"`: pri slovenskom zápise „1 250,50" ho prehliadač
 * vyhodnotí ako prázdny a mzda by sa ticho neuložila. Tu prijmeme čiarku aj
 * medzery a pri čomkoľvek inom vrátime chybu, ktorá sa ukáže pri poli.
 */
export function parseSalary(raw: string): { value: number | null } | { error: string } {
  const text = raw.replace(/[\s\u00a0]/g, '').replace(',', '.')
  if (!text) return { value: null }
  if (!/^\d{1,8}(\.\d{1,2})?$/.test(text)) {
    return { error: 'Zadajte sumu v eurách, napr. 1250 alebo 1 250,50 (najviac 2 desatinné miesta).' }
  }
  return { value: Number(text) }
}
