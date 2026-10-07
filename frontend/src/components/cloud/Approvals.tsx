import { useState } from 'react';
import { CalendarClock, Check, Clock3, History, ShieldAlert, ShieldCheck, Undo2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { money, type Recommendation } from '@/mockData/cloud';
import { reviewMeta, rejectReasons, snoozeOptions, type ApprovalStatus, type AuditEvent } from '@/mockData/approvals';
import { ProviderBadge } from './AppShell';
import { cn } from '@/lib/utils';

export const statusTone: Record<ApprovalStatus, string> = {
  'Pending Review': 'bg-warning/15 text-warning',
  Approved: 'bg-primary/15 text-primary',
  Scheduled: 'bg-accent text-accent-foreground',
  Snoozed: 'bg-muted text-muted-foreground',
  Rejected: 'bg-destructive/15 text-destructive',
};
const riskTone = { Low: 'text-success', Medium: 'text-warning', High: 'text-destructive' };

export function StatusPill({ status }: { status: ApprovalStatus }) {
  return <span className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium', statusTone[status])}>{status}</span>;
}

type Props = {
  item: Recommendation | null;
  status: ApprovalStatus;
  audit: AuditEvent[];
  onClose: () => void;
  onDecision: (status: ApprovalStatus, text: string) => void;
};

export function ApprovalDrawer({ item, status, audit, onClose, onDecision }: Props) {
  const [mode, setMode] = useState<'none' | 'snooze' | 'reject'>('none');
  const [days, setDays] = useState('14');
  const [reason, setReason] = useState<string>(rejectReasons[0] ?? '');
  const [note, setNote] = useState('');
  const meta = item ? reviewMeta(item) : null;
  const decide = (s: ApprovalStatus, text: string) => { onDecision(s, note.trim() ? `${text} — “${note.trim()}”` : text); setMode('none'); setNote(''); };

  return (
    <Sheet open={!!item} onOpenChange={o => { if (!o) { setMode('none'); onClose(); } }}>
      <SheetContent className="detail-drawer overflow-y-auto w-full sm:max-w-[520px]">
        <SheetHeader>
          <div className="drawer-kicker">HUMAN REVIEW</div>
          <SheetTitle>{item?.title}</SheetTitle>
          <SheetDescription>{item?.resource} · {item?.provider}</SheetDescription>
        </SheetHeader>
        {item && meta && (
          <div className="drawer-body">
            <div className="flex flex-wrap items-center gap-2"><StatusPill status={status} /><ProviderBadge provider={item.provider} /><span className="text-xs text-muted-foreground">{meta.signoff}</span></div>

            <div className="drawer-metrics">
              <div><small>POTENTIAL SAVINGS</small><strong className="text-success">{money(item.savings)}</strong></div>
              <div><small>RISK LEVEL</small><strong className={riskTone[meta.risk]}>{meta.risk}</strong></div>
            </div>

            <div className="drawer-section">
              <h3>How this was detected</h3>
              <ul className="space-y-2 text-sm">
                <li className="flex justify-between gap-3"><span className="text-muted-foreground">Policy check</span><span className="font-mono text-xs">{meta.rule}</span></li>
                <li className="flex justify-between gap-3"><span className="text-muted-foreground">Usage model</span><span className="text-right">{meta.mlSignal}</span></li>
                <li className="flex justify-between gap-3"><span className="text-muted-foreground">Ranking score</span><span>{meta.rankScore}/100 · {item.confidence}% confidence</span></li>
              </ul>
            </div>

            <div className="drawer-section">
              <h3>Risk assessment</h3>
              <ul className="space-y-2 text-sm">
                <li className="flex gap-2"><ShieldAlert size={15} className={cn('mt-0.5 shrink-0', riskTone[meta.risk])} /> {meta.downtime}</li>
                <li className="flex gap-2"><Undo2 size={15} className="mt-0.5 shrink-0 text-primary" /> {meta.rollback}</li>
                <li className="flex gap-2"><ShieldCheck size={15} className="mt-0.5 shrink-0 text-success" /> {item.action}</li>
              </ul>
            </div>

            <div className="drawer-section">
              <h3>Review note (optional)</h3>
              <Textarea value={note} onChange={e => setNote(e.target.value)} placeholder="Add context for your team…" maxLength={300} />
            </div>

            {mode === 'snooze' && (
              <div className="flex gap-2">
                <Select value={days} onValueChange={setDays}><SelectTrigger className="flex-1"><SelectValue /></SelectTrigger><SelectContent>{snoozeOptions.map(d => <SelectItem key={d} value={String(d)}>Snooze {d} days</SelectItem>)}</SelectContent></Select>
                <Button onClick={() => decide('Snoozed', `Snoozed for ${days} days`)}>Confirm</Button>
              </div>
            )}
            {mode === 'reject' && (
              <div className="flex gap-2">
                <Select value={reason} onValueChange={setReason}><SelectTrigger className="flex-1"><SelectValue /></SelectTrigger><SelectContent>{rejectReasons.map(r => <SelectItem key={r} value={r}>{r}</SelectItem>)}</SelectContent></Select>
                <Button variant="destructive" onClick={() => decide('Rejected', `Rejected: ${reason}`)}>Reject</Button>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2">
              <Button onClick={() => decide('Approved', 'Approved for execution')}><Check size={15} /> Approve</Button>
              <Button variant="outline" onClick={() => decide('Scheduled', 'Scheduled for Sunday 02:00 UTC maintenance window')}><CalendarClock size={15} /> Schedule</Button>
              <Button variant="outline" onClick={() => setMode(mode === 'snooze' ? 'none' : 'snooze')}><Clock3 size={15} /> Snooze</Button>
              <Button variant="outline" className="text-destructive" onClick={() => setMode(mode === 'reject' ? 'none' : 'reject')}><X size={15} /> Reject</Button>
            </div>

            <div className="drawer-section">
              <h3 className="flex items-center gap-2"><History size={15} /> Audit trail</h3>
              <ol className="space-y-3 border-l border-border pl-4">
                {[...audit].reverse().map((e, i) => (
                  <li key={i} className="text-sm"><div className="text-xs text-muted-foreground">{e.at} · {e.actor}</div><div>{e.text}</div></li>
                ))}
              </ol>
            </div>
            <div className="drawer-note">Decisions are simulated in demo mode. No changes are made to your cloud accounts.</div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
