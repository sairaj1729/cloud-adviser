import { useState } from 'react';
import { CheckCircle2, Cloud, Lock, Plus, RefreshCw, ShieldCheck, Trash2, XCircle, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { SectionHeading, useCloudApp } from './AppShell';
import { providerMeta, type Cloud as CloudType } from '@/mockData/cloud';
import { cn } from '@/lib/utils';

type Status = 'Connected' | 'Disconnected' | 'Error';
type Conn = { id: string; provider: CloudType; name: string; ref: string; status: Status; lastSync: string };

const cardCopy: Record<CloudType, { tagline: string; label: string }> = {
  AWS: { tagline: 'Connect your AWS accounts', label: 'Connect AWS' },
  Azure: { tagline: 'Connect your Azure subscriptions', label: 'Connect Azure' },
  GCP: { tagline: 'Connect your Google Cloud projects', label: 'Connect GCP' },
};
// Only non-secret identifiers are collected here; credentials are handled by the backend.
const fields: Record<CloudType, { id: string; label: string; placeholder: string; pattern: RegExp; hint: string }[]> = {
  AWS: [
    { id: 'name', label: 'Account nickname', placeholder: 'Production', pattern: /^.{2,40}$/, hint: '2–40 characters' },
    { id: 'ref', label: 'AWS account ID', placeholder: '123456789012', pattern: /^\d{12}$/, hint: '12-digit account ID' },
    { id: 'role', label: 'Read-only IAM role ARN', placeholder: 'arn:aws:iam::123456789012:role/CloudAdvisorReadOnly', pattern: /^arn:aws:iam::\d{12}:role\/[\w+=,.@\/-]{1,64}$/, hint: 'arn:aws:iam::<account>:role/<name>' },
  ],
  Azure: [
    { id: 'name', label: 'Subscription nickname', placeholder: 'Analytics', pattern: /^.{2,40}$/, hint: '2–40 characters' },
    { id: 'ref', label: 'Subscription ID', placeholder: '00000000-0000-0000-0000-000000000000', pattern: /^[0-9a-f-]{36}$/i, hint: 'GUID format' },
    { id: 'tenant', label: 'Tenant ID', placeholder: '00000000-0000-0000-0000-000000000000', pattern: /^[0-9a-f-]{36}$/i, hint: 'GUID format' },
  ],
  GCP: [
    { id: 'name', label: 'Project nickname', placeholder: 'Data platform', pattern: /^.{2,40}$/, hint: '2–40 characters' },
    { id: 'ref', label: 'Project ID', placeholder: 'acme-data-prod', pattern: /^[a-z][a-z0-9-]{4,28}[a-z0-9]$/, hint: '6–30 lowercase letters, digits, hyphens' },
  ],
};
const initial: Conn[] = [
  { id: 'c1', provider: 'AWS', name: 'Production', ref: '•••• •••• 4821', status: 'Connected', lastSync: '4 min ago' },
  { id: 'c2', provider: 'Azure', name: 'Analytics', ref: 'Subscription •••• 9f2a', status: 'Error', lastSync: '2 days ago' },
  { id: 'c3', provider: 'GCP', name: 'Data platform', ref: 'acme-data-prod', status: 'Disconnected', lastSync: 'Never' },
];
const mask = (p: CloudType, ref: string) => p === 'AWS' ? `•••• •••• ${ref.slice(-4)}` : p === 'Azure' ? `Subscription •••• ${ref.slice(-4)}` : ref;

function StatusPill({ status }: { status: Status }) {
  const Icon = status === 'Connected' ? CheckCircle2 : status === 'Error' ? AlertTriangle : XCircle;
  return <span className={cn('conn-pill', `conn-${status.toLowerCase()}`)}><Icon size={13} />{status}</span>;
}

export function ConnectionsPanel() {
  const { notify } = useCloudApp();
  const [conns, setConns] = useState<Conn[]>(initial);
  const [open, setOpen] = useState<CloudType | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [remove, setRemove] = useState<Conn | null>(null);

  const start = (p: CloudType) => { setOpen(p); setValues({}); setErrors({}); };
  const submit = () => {
    if (!open) return;
    const errs: Record<string, string> = {};
    fields[open].forEach(f => { if (!f.pattern.test((values[f.id] ?? '').trim())) errs[f.id] = `Enter a valid value (${f.hint}).`; });
    setErrors(errs);
    if (Object.keys(errs).length) return;
    const p = open; setBusy('new');
    setTimeout(() => {
      setConns(c => [...c, { id: `c${Date.now()}`, provider: p, name: values['name']!.trim(), ref: mask(p, values['ref']!.trim()), status: 'Connected', lastSync: 'Just now' }]);
      setBusy(null); setOpen(null); notify(`${p} connection added in demo mode. Live verification runs once the backend is available.`);
    }, 900);
  };
  const test = (c: Conn) => {
    setBusy(c.id);
    setTimeout(() => { setBusy(null); setConns(l => l.map(x => x.id === c.id ? { ...x, status: 'Connected', lastSync: 'Just now' } : x)); notify(`${c.name} connection check passed (demo).`); }, 900);
  };

  return <>
    <section className="surface account-section">
      <SectionHeading title="Cloud connections" detail="Connect read-only access to your cloud providers" />
      <div className="provider-cards">
        {(['AWS', 'Azure', 'GCP'] as CloudType[]).map(p => {
          const count = conns.filter(c => c.provider === p).length;
          return <div key={p} className="provider-card">
            <span className={cn('connection-icon', p.toLowerCase())}><Cloud size={21} /></span>
            <div className="min-w-0"><strong>{providerMeta[p].name}</strong><small>{cardCopy[p].tagline}</small><small className="text-muted-foreground">{count} connected</small></div>
            <Button onClick={() => start(p)} className="gap-1.5"><Plus size={15} />{cardCopy[p].label}</Button>
          </div>;
        })}
      </div>
    </section>

    <section className="surface account-section">
      <SectionHeading title="Connected accounts" detail={`${conns.length} connection${conns.length === 1 ? '' : 's'} in this workspace`} />
      {conns.length === 0 ? <div className="empty-state"><Cloud size={25} /><strong>No connections yet</strong><span>Connect a provider above to start analysing spend.</span></div> :
        <div className="connection-list">{conns.map(c => <div className="connection-row conn-row" key={c.id}>
          <span className={cn('connection-icon', c.provider.toLowerCase())}><Cloud size={21} /></span>
          <div className="min-w-0"><strong>{c.name} <span className="text-muted-foreground font-normal">· {c.provider}</span></strong><small>{c.ref} · Last synced {c.lastSync}</small>
            {c.status === 'Error' && <small className="conn-error-text">Access could not be verified. Check the read-only role, then test again.</small>}</div>
          <StatusPill status={c.status} />
          <div className="conn-actions">
            <Button size="sm" variant="outline" onClick={() => test(c)} disabled={busy === c.id} className="gap-1.5"><RefreshCw size={13} className={busy === c.id ? 'animate-spin' : ''} />{c.status === 'Connected' ? 'Test' : 'Reconnect'}</Button>
            <Button size="sm" variant="ghost" onClick={() => setRemove(c)} aria-label={`Disconnect ${c.name}`} className="text-muted-foreground"><Trash2 size={14} /></Button>
          </div>
        </div>)}</div>}
    </section>

    <div className="callout"><ShieldCheck size={17} /><span>Cloud Advisor uses read-only access wherever possible. Credentials and sensitive authentication material are handled by the backend and are never exposed in the frontend.</span></div>

    <Dialog open={!!open} onOpenChange={o => !o && setOpen(null)}>
      <DialogContent>
        <DialogHeader><DialogTitle>{open && cardCopy[open].label}</DialogTitle><DialogDescription>Enter identifiers only. Grant Cloud Advisor a read-only role in your {open} console — no secret keys are entered here.</DialogDescription></DialogHeader>
        <div className="grid gap-4">{open && fields[open].map(f => <div key={f.id} className="grid gap-1.5">
          <Label htmlFor={f.id}>{f.label}</Label>
          <Input id={f.id} placeholder={f.placeholder} maxLength={120} value={values[f.id] ?? ''} onChange={e => setValues(v => ({ ...v, [f.id]: e.target.value }))} aria-invalid={!!errors[f.id]} />
          {errors[f.id] ? <small className="conn-error-text">{errors[f.id]}</small> : <small className="text-muted-foreground text-xs">{f.hint}</small>}
        </div>)}
          <div className="flex items-center gap-2 text-xs text-muted-foreground"><Lock size={13} />Demo mode — connection is simulated until the backend is reachable.</div>
        </div>
        <DialogFooter><Button variant="outline" onClick={() => setOpen(null)}>Cancel</Button><Button onClick={submit} disabled={busy === 'new'}>{busy === 'new' ? 'Verifying…' : 'Connect'}</Button></DialogFooter>
      </DialogContent>
    </Dialog>

    <AlertDialog open={!!remove} onOpenChange={o => !o && setRemove(null)}>
      <AlertDialogContent>
        <AlertDialogHeader><AlertDialogTitle>Disconnect {remove?.name}?</AlertDialogTitle><AlertDialogDescription>Cloud Advisor will stop collecting cost data from this account. Existing cloud resources are not affected, and you can reconnect at any time.</AlertDialogDescription></AlertDialogHeader>
        <AlertDialogFooter><AlertDialogCancel>Cancel</AlertDialogCancel><AlertDialogAction onClick={() => { if (remove) { setConns(l => l.filter(x => x.id !== remove.id)); notify(`${remove.name} disconnected.`); } setRemove(null); }}>Disconnect</AlertDialogAction></AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  </>;
}
