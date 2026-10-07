import type { Recommendation } from './cloud';

export type ApprovalStatus = 'Pending Review' | 'Approved' | 'Scheduled' | 'Snoozed' | 'Rejected';
export type Risk = 'Low' | 'Medium' | 'High';
export type AuditEvent = { at: string; actor: string; text: string };

export type ReviewMeta = {
  risk: Risk;
  downtime: string;
  rollback: string;
  rule: string;
  mlSignal: string;
  rankScore: number;
  signoff: string;
};

// Demo review metadata derived per recommendation; replace with backend values when available.
export function reviewMeta(r: Recommendation): ReviewMeta {
  const risk: Risk = r.priority === 'High' && r.savings > 800 ? 'Medium' : r.confidence >= 90 ? 'Low' : r.priority === 'Low' ? 'Low' : 'Medium';
  return {
    risk,
    downtime: risk === 'Low' ? 'No downtime expected' : 'Short restart (about 5 minutes) may be required',
    rollback: risk === 'Low' ? 'Snapshot taken automatically before any change' : 'Previous configuration kept for one-click rollback',
    rule: `POLICY-${r.provider.toUpperCase()}-${r.id.replace(/\D/g, '').padStart(3, '0') || '001'}`,
    mlSignal: r.confidence >= 85 ? 'Usage consistently below forecast baseline' : 'Moderate deviation from expected usage pattern',
    rankScore: Math.min(99, Math.round(r.confidence * 0.7 + Math.min(r.savings / 40, 30))),
    signoff: r.savings >= 1000 ? 'Requires finance lead sign-off' : 'Self-serve approval',
  };
}

export function initialAudit(r: Recommendation): AuditEvent[] {
  return [
    { at: 'Oct 4, 14:20', actor: 'Policy check', text: `Flagged by ${reviewMeta(r).rule}` },
    { at: 'Oct 4, 14:21', actor: 'Usage model', text: reviewMeta(r).mlSignal },
    { at: 'Oct 4, 14:22', actor: 'Recommendation ranking', text: `Ranked ${reviewMeta(r).rankScore}/100 · ${r.confidence}% confidence` },
  ];
}

export const rejectReasons = ['Planned seasonal usage', 'Compliance or retention requirement', 'Owned by another team', 'Not accurate / false positive'];
export const snoozeOptions = [7, 14, 30];
