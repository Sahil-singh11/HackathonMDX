/* Workstream 2 — grounding tests.
 *
 * The project has no frontend test runner, and adding one the night before
 * judging is not worth the shared-file churn. These run through esbuild + Node:
 *
 *   node scripts/run-grounding-tests.mjs
 *
 * What matters here is the fail-closed contract: an uncovered question must
 * never reach the model, and a covered one must carry the real rule text.
 */
import { buildPrompt, detectTopic, matchSpecies, retrieve, systemPrompt } from './grounding'

// This file runs in Node via scripts/run-grounding-tests.mjs. The frontend has
// no @types/node and adding it for one test file is not worth the dependency.
declare const process: { exit(code: number): never }

let passed = 0
let failed = 0

function check(name: string, condition: boolean, detail = '') {
  if (condition) { passed++; console.log(`  PASS  ${name}`) }
  else { failed++; console.log(`  FAIL  ${name}${detail ? ` — ${detail}` : ''}`) }
}

console.log('\nSpecies matching (Morisyen / English / French / scientific)')
check('English common name', matchSpecies('what size for day octopus?').some((s) => s.species_id === 'octopus_cyanea'))
check('Morisyen name', matchSpecies('ki groser pou ourite?').some((s) => s.species_id === 'octopus_cyanea'))
check('French keyword from catalogue', matchSpecies('quelle taille pour le poulpe?').some((s) => s.species_id === 'octopus_cyanea'))
check('scientific name', matchSpecies('Octopus cyanea minimum').some((s) => s.species_id === 'octopus_cyanea'))
check('other species (kapitenn)', matchSpecies('kapitenn size limit').some((s) => s.species_id === 'lethrinus_nebulosus'))
check('no false positive on unrelated text', matchSpecies('what is the weather tomorrow') .length === 0)

console.log('\nTopic detection across languages')
check('size (en)', detectTopic('what is the minimum length?') === 'size')
check('size (mfe)', detectTopic('ki longer minimum?') === 'size')
check('season (en)', detectTopic('when is the closed season?') === 'season')
check('season (mfe)', detectTopic('kan sezon ferme?') === 'season')
check('season (fr, accented)', detectTopic('quand est la fermeture?') === 'season')
check('declaration (en)', detectTopic('how do I submit my declaration?') === 'declaration')
check('declaration (mfe)', detectTopic('kouma mo fer mo deklarasion?') === 'declaration')
check('no topic on chit-chat', detectTopic('hello how are you') === null)

console.log('\nFail-closed coverage — the safety contract')
const offTopic = retrieve('what is the capital of France?')
check('off-topic is NOT covered', !offTopic.covered)
check('off-topic yields empty context', offTopic.context === '')
const weather = retrieve('will it rain tomorrow')
check('weather is NOT covered', !weather.covered)
const tuna = retrieve('what is the size limit for tuna?')
check('species outside the catalogue still refuses on species', tuna.species.length === 0)

console.log('\nCovered questions carry real, verbatim rule data')
const octopusSize = retrieve('ki groser minimum pou ourite?')
check('octopus size is covered', octopusSize.covered)
check('cites the GN 167/2016 minimum-size rule',
  octopusSize.rules.some((r) => r.rule_id === 'R-OCT-MINSIZE-2016'))
check('context carries the 7 cm figure', octopusSize.context.includes('7 cm'))
check('context carries the MANTLE measurement caveat',
  octopusSize.context.toLowerCase().includes('mantle'))
check('context carries the provisional status',
  octopusSize.context.includes('provisional'))

const octopusSeason = retrieve('when is octopus closed?')
check('octopus season is covered', octopusSeason.covered)
check('cites the closure rule', octopusSeason.rules.some((r) => r.rule_id === 'R-OCT-CLOSE-2016'))
check('context carries the closure window', octopusSeason.context.includes('08-15'))

const noRuleSpecies = retrieve('what size for naso unicornis?')
check('species with no verified rule is still covered', noRuleSpecies.covered)
check('and says no verified minimum exists',
  noRuleSpecies.context.toLowerCase().includes('no verified minimum'))

const decl = retrieve('how do I complete a declaration?')
check('declaration is covered', decl.covered)
check('declaration context states the submission is SIMULATED',
  decl.context.includes('SIMULATED'))

console.log('\nPrompt construction')
const sys = systemPrompt('en')
check('system prompt forbids inventing regulations', sys.includes('NEVER state a size limit'))
check('system prompt forbids memory-based answers', sys.toLowerCase().includes('do not know current mauritian fisheries law from memory'))
check('system prompt requires flagging provisional rules', sys.includes('provisional'))
check('mfe prompt asks for Kreol', systemPrompt('mfe').includes('Kreol Morisien'))
const prompt = buildPrompt('ki groser?', 'CTX')
check('prompt puts context before the question', prompt.indexOf('CTX') < prompt.indexOf('ki groser?'))

console.log(`\n${passed} passed, ${failed} failed\n`)
if (failed > 0) process.exit(1)
