/**
 * Prenos chatu z /chat na /apply.
 *
 * `session_id` ani `claim_token` nesmú byť v URL. Z URL unikajú do histórie
 * prehliadača, cez hlavičku Referer aj do access logov. Kto by ich získal, mohol
 * by si cudzí rozhovor pripojiť k vlastnej prihláške.
 *
 * sessionStorage je viazaný na kartu: prežije prechod na prihlášku aj reload,
 * ale nezdieľa sa s inými kartami a zmizne po zatvorení karty.
 */

export interface ChatClaim {
  session_id: string
  claim_token: string
}

const key = (slug: string, positionId: string) => `chat-claim:${slug}:${positionId}`

export function saveChatClaim(slug: string, positionId: string, claim: ChatClaim) {
  try {
    sessionStorage.setItem(key(slug, positionId), JSON.stringify(claim))
  } catch {
    // Bez úložiska (súkromné okno, zablokované dáta) prihláška odíde bez chatu.
  }
}

export function loadChatClaim(slug: string, positionId: string): ChatClaim | null {
  try {
    const raw = sessionStorage.getItem(key(slug, positionId))
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<ChatClaim>
    if (typeof parsed.session_id !== 'string' || typeof parsed.claim_token !== 'string') return null
    return { session_id: parsed.session_id, claim_token: parsed.claim_token }
  } catch {
    return null
  }
}

export function clearChatClaim(slug: string, positionId: string) {
  try {
    sessionStorage.removeItem(key(slug, positionId))
  } catch {
    // nič
  }
}
