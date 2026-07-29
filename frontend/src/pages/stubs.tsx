/**
 * Route stubs for surfaces nobody has built yet.
 *
 * These exist so the router can register every route in Phase 0 and never be
 * touched again — that is what stops three developers colliding in App.tsx.
 *
 * Each stub says plainly that it is unbuilt and who owns it, and neither
 * fabricates a result — an invented green "verified" would be a fake compliance
 * claim, which is the one thing this product cannot ship.
 *
 * The backend is READY: the traceability-ledger commit added a real hash chain
 * and the endpoints these pages need — /api/ledger, /api/ledger/verify,
 * /api/verify/{record_id}, /api/submissions, /api/submissions/{id} — all wired
 * up in api/client.ts as ledger(), verifyLedger(), verifyCertificate(),
 * listSubmissions() and getSubmission(). Nothing here is blocked any more.
 *
 * Shirish: replace the body, keep the export name and file path. Render the
 * scope_note every endpoint returns; do not paraphrase it into something
 * stronger than it says.
 */
import { Card, EmptyState } from '../components/ui'
import { Construction } from 'lucide-react'

function Stub({ title, owner, note }: { title: string; owner: string; note: string }) {
  return (
    <div className="lk-scope">
      <Card>
        <EmptyState
          icon={<Construction size={48} aria-hidden="true" />}
          title={`${title} — not built yet`}
          body={<>
            {note}
            <br /><br />
            <strong>Owner:</strong> {owner}
          </>}
        />
      </Card>
    </div>
  )
}

export function AuthorityStub() {
  return <Stub
    title="Authority dashboard"
    owner="Shirish (components/authority)"
    note="Officer review, submissions table, map view and the ledger chain inspector live here. The backend is ready: api.listSubmissions(), api.getSubmission(id), api.ledger() and api.verifyLedger() are all live." />
}

export function VerifyStub() {
  return <Stub
    title="Certificate verification"
    owner="Shirish (components/verify)"
    note="Public QR-landing page showing whether a record is unaltered since it was logged. The backend is ready: api.verifyCertificate(recordId) returns verified / not_found / chain_broken, plus a scope_note stating what the check does NOT prove. Render that note." />
}
