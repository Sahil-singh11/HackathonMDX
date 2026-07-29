/**
 * Route stubs for surfaces nobody has built yet.
 *
 * These exist so the router can register every route in Phase 0 and never be
 * touched again — that is what stops three developers colliding in App.tsx.
 *
 * Each stub says plainly that it is unbuilt and who owns it. None of them
 * fabricate data: /authority and /verify depend on a ledger and certificate
 * backend that does not exist yet (there is no ledger table, no officer
 * accounts, no certificate concept in the FastAPI app), so showing a mock
 * "verified" result here would be inventing a compliance claim.
 *
 * Dhanesh / Shirish: replace the body, keep the export name and file path.
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
    note="Officer review, submissions table, map view and the ledger chain view live here. Blocked on a backend: there is currently no submissions, officer or ledger API to read from." />
}

export function VerifyStub() {
  return <Stub
    title="Certificate verification"
    owner="Shirish (components/verify)"
    note="Public QR-landing page showing whether a certificate's record is unaltered. Blocked on the same missing ledger/certificate backend — this page must never claim 'verified' without a real chain to check." />
}
