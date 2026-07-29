/* Workstream 2 — retrieval grounding for the offline assistant.
 *
 * THE RULE THIS FILE ENFORCES: the model must never answer a Mauritian
 * fisheries question from its training data. Gemma has read the open web; it
 * has not read the current Mauritian gazette, and a plausible-sounding invented
 * size limit is the single most damaging thing this product could output.
 *
 * So the flow is retrieval-first and fails closed:
 *   1. match the question against the bundled catalogue + rules
 *   2. if nothing matches, DO NOT CALL THE MODEL — return a deterministic
 *      refusal pointing at the rules browser. A refusal that never reaches the
 *      model cannot be hallucinated around.
 *   3. if something matches, inject those entries verbatim and instruct the
 *      model to answer only from them.
 *
 * Retrieval is keyword-based, not embedding-based: the catalogue already ships
 * hand-written `keywords` per species covering Morisyen, French and English
 * (e.g. octopus / ourite / poulpe), the corpus is 5 species and 7 rules, and a
 * deterministic matcher is auditable in a way a similarity score is not.
 */
import { rules, sources, species, type RuleEntry, type SpeciesEntry } from './rulesData'

export type Topic = 'size' | 'season' | 'declaration' | 'species' | null

export interface GroundingResult {
  /** False => refuse deterministically, never call the model. */
  covered: boolean
  topic: Topic
  species: SpeciesEntry[]
  rules: RuleEntry[]
  /** Verbatim context block injected into the prompt; '' when not covered. */
  context: string
}

/* Topic cues in the three languages a fisher may type. Deliberately generous:
 * a false positive costs a wasted retrieval, a false negative wrongly refuses. */
const SIZE_CUES = [
  'size', 'length', 'minimum', 'small', 'undersized', 'cm', 'measure', 'big', 'how long',
  'groser', 'longer', 'minimum', 'tipti', 'mezir', 'mantle', 'mantel',
  'taille', 'longueur', 'petit', 'mesure', 'combien',
]
const SEASON_CUES = [
  'season', 'closed', 'closure', 'when', 'ban', 'allowed', 'month', 'open', 'fishing period',
  'sezon', 'ferme', 'fermtir', 'kan', 'permet', 'mwa', 'ouver', 'lasas',
  'saison', 'fermeture', 'quand', 'mois', 'interdit', 'autorise',
]
const DECLARATION_CUES = [
  'declaration', 'declare', 'submit', 'report', 'form', 'paperwork', 'ministry', 'permit',
  'deklarasion', 'deklar', 'soumet', 'rapor', 'formil', 'minister',
  'déclaration', 'declarer', 'soumettre', 'rapport', 'formulaire', 'ministere',
]

/** Fold accents and case so "déclaration" matches "deklarasion" cues. */
function normalise(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9\s]/g, ' ')
}

function hasCue(haystack: string, cues: string[]): boolean {
  return cues.some((cue) => haystack.includes(normalise(cue)))
}

/** Species whose name or keywords appear in the question. */
export function matchSpecies(question: string): SpeciesEntry[] {
  const q = normalise(question)
  return species.filter((sp) => {
    const terms = [sp.english, sp.morisyen, sp.scientific, ...(sp.keywords ?? [])]
    return terms.some((term) => {
      const t = normalise(String(term))
      // Require a word-boundary hit so "vye" does not match inside another word.
      return t.length > 2 && new RegExp(`\\b${t.replace(/\s+/g, '\\s+')}\\b`).test(q)
    })
  })
}

export function detectTopic(question: string): Topic {
  const q = normalise(question)
  if (hasCue(q, DECLARATION_CUES)) return 'declaration'
  if (hasCue(q, SEASON_CUES)) return 'season'
  if (hasCue(q, SIZE_CUES)) return 'size'
  return null
}

/** Render one rule as verbatim, attributed context. Never paraphrased. */
function ruleToContext(rule: RuleEntry): string {
  const sp = species.find((s) => s.species_id === rule.species_id)
  const name = sp ? `${sp.english} (${sp.morisyen}, ${sp.scientific})` : rule.species_id
  const lines = [`- Species: ${name}`, `  Rule ${rule.rule_id} (${rule.rule_type})`]

  if (rule.rule_type === 'seasonal_closure' || rule.rule_type === 'historical_note') {
    lines.push(`  Closed from ${rule.closed_from} to ${rule.closed_to} (month-day)`)
  }
  if (rule.minimum_length_cm != null) {
    lines.push(`  Minimum ${rule.minimum_length_cm} cm, measured as: ${rule.measurement ?? 'unspecified'}`)
  } else if (rule.rule_type === 'minimum_size') {
    lines.push('  No verified minimum size found for this species.')
  }
  lines.push(`  Verification status: ${rule.verification_status}`)
  if (rule.note) lines.push(`  Note: ${rule.note}`)
  if (rule.scope_note) lines.push(`  Scope: ${rule.scope_note}`)
  const src = sources[rule.source_id]
  if (src) lines.push(`  Source ${rule.source_id}: ${src.title}`)
  return lines.join('\n')
}

const DECLARATION_CONTEXT = `- Completing a declaration (process, not regulation):
  1. Record each catch as it is landed: photo, confirm the species yourself, enter the measured length. Works offline; records queue on the device.
  2. Before the period ends, check the catch log: confirm everything synced and correct any wrong species.
  3. Choose the period and review the record count, species breakdown and total.
  4. Submit and keep the reference number and printable summary.
  IMPORTANT: in this app the submission is SIMULATED. It is not a real government filing.`

/**
 * Retrieve grounding for a question.
 *
 * Coverage rules:
 *   - a named species always counts as covered (we can cite its rules, even if
 *     the answer is "no verified rule exists")
 *   - a declaration question is covered by the process text
 *   - a size/season question with no species is covered by all rules of that
 *     type, so "what are the closed seasons?" works
 *   - anything else is NOT covered
 */
export function retrieve(question: string): GroundingResult {
  const matched = matchSpecies(question)
  const topic = detectTopic(question)

  if (topic === 'declaration') {
    return { covered: true, topic, species: [], rules: [], context: DECLARATION_CONTEXT }
  }

  let relevant: RuleEntry[] = []
  if (matched.length > 0) {
    const ids = new Set(matched.map((s) => s.species_id))
    relevant = rules.filter((r) => ids.has(r.species_id))
    if (topic === 'size') relevant = relevant.filter((r) => r.rule_type === 'minimum_size')
    if (topic === 'season') {
      relevant = relevant.filter((r) => r.rule_type === 'seasonal_closure' || r.rule_type === 'historical_note')
    }
    // A species with no rule of the asked-for type still gets its full set, so
    // the model can say "no size rule, but there is a closure" rather than
    // going silent.
    if (relevant.length === 0) relevant = rules.filter((r) => ids.has(r.species_id))
  } else if (topic === 'size') {
    relevant = rules.filter((r) => r.rule_type === 'minimum_size')
  } else if (topic === 'season') {
    relevant = rules.filter((r) => r.rule_type === 'seasonal_closure' || r.rule_type === 'historical_note')
  }

  const covered = matched.length > 0 || relevant.length > 0
  const context = covered
    ? [
      relevant.map(ruleToContext).join('\n'),
      matched.length > 0
        ? `\nSpecies details:\n${matched.map((s) => `- ${s.english} (${s.morisyen}, ${s.scientific}) — habitat: ${s.habitat}`).join('\n')}`
        : '',
    ].filter(Boolean).join('\n')
    : ''

  return { covered, topic, species: matched, rules: relevant, context }
}

/** Languages the assistant answers in, keyed to the app's language setting. */
export type AnswerLanguage = 'en' | 'mfe'

/**
 * The system instruction. Deliberately blunt about the one failure mode that
 * matters: inventing a regulation.
 */
export function systemPrompt(language: AnswerLanguage): string {
  return [
    'You are the offline assistant inside Lamer Konekte, an app for small-scale fishers in Mauritius.',
    '',
    'ABSOLUTE RULES:',
    '1. Answer ONLY from the CONTEXT provided in the user message. The context is the app\'s regulatory data.',
    '2. NEVER state a size limit, closed season, penalty or regulation that is not in the context. You do not know current Mauritian fisheries law from memory, and guessing could cause a fisher to break the law or lose a catch.',
    '3. If the context does not answer the question, say so plainly and tell the user to open the Rules tab. Do not improvise.',
    '4. When the context marks a rule "provisional" or "unavailable", say so in your answer. Never present a provisional rule as settled law.',
    '5. Keep answers short — two or three sentences. A fisher is reading this on a phone on a boat.',
    '6. Never claim to have submitted anything to the government. Declarations in this app are simulated.',
    '',
    language === 'mfe'
      ? 'Answer in Kreol Morisien. If you cannot express something accurately in Kreol Morisien, use English rather than writing something confusing.'
      : 'Answer in English.',
  ].join('\n')
}

/** The user-side message: context first, question last. */
export function buildPrompt(question: string, context: string): string {
  return `CONTEXT (the app's regulatory data — the only source you may use):\n${context}\n\nQUESTION: ${question}`
}
