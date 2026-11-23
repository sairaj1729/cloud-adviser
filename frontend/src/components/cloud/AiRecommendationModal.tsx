import React, { useState, useEffect } from 'react';
import { 
  Sparkles, Check, Copy, ArrowRight, Zap, ShieldCheck, 
  ShieldAlert, Terminal, RefreshCw, Layers, TrendingDown,
  Info, CheckCircle2, ChevronRight, X, AlertTriangle
} from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  apiGetAIRecommendation, 
  apiUpdateAIRecommendationStatus,
  type AIRecommendationData 
} from '@/config/api';
import { money, getCategoryForRecommendation, getServiceForRecommendation, type Recommendation, type Cloud as CloudType } from '@/mockData/cloud';

interface AiRecommendationModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  recommendation: Recommendation | null;
  onApproveSuccess?: (recId: string, updatedAiData: AIRecommendationData) => void;
  onGenerated?: (recId: string, data: AIRecommendationData) => void;
  onNotify?: (msg: string) => void;
}

export function AiRecommendationModal({
  open,
  onOpenChange,
  recommendation,
  onApproveSuccess,
  onGenerated,
  onNotify
}: AiRecommendationModalProps) {
  const [loading, setLoading] = useState<boolean>(false);
  const [aiData, setAiData] = useState<AIRecommendationData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [selectedProvider, setSelectedProvider] = useState<string>('auto');
  const [approving, setApproving] = useState<boolean>(false);

  // When modal opens or recommendation changes, initialize or fetch AI analysis
  useEffect(() => {
    if (!open || !recommendation) {
      setAiData(null);
      setError(null);
      setCopied(false);
      return;
    }

    // Check if recommendation already has pre-cached AI data
    if (recommendation.ai_recommendation) {
      setAiData(recommendation.ai_recommendation);
      setError(null);
    } else {
      // Fetch live AI recommendation
      fetchAi(selectedProvider);
    }
  }, [open, recommendation]);

  const fetchAi = async (provider: string = 'auto') => {
    if (!recommendation) return;
    setLoading(true);
    setError(null);

    const resourceId = recommendation.resource_id || recommendation.resource || recommendation.id;
    const findingId = recommendation.id;

    try {
      const data = await apiGetAIRecommendation(
        resourceId, 
        findingId, 
        provider === 'auto' ? undefined : provider
      );
      setAiData(data);
      if (onGenerated && recommendation) {
        onGenerated(recommendation.id, data);
      }
      if (onNotify) {
        onNotify(`AI Analysis generated using ${data.llm_provider_used} (${data.llm_model_used})`);
      }
    } catch (err: any) {
      console.error('Failed to generate AI recommendation:', err);
      setError(err?.message || 'Failed to generate AI recommendation. Please check your connection.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyCommand = (command: string) => {
    if (!command) return;
    navigator.clipboard.writeText(command);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
    if (onNotify) onNotify('Remediation command copied to clipboard!');
  };

  const handleApprove = async () => {
    if (!recommendation || !aiData) return;
    setApproving(true);
    const resourceId = aiData.resource_id || recommendation.resource_id || recommendation.resource;
    try {
      await apiUpdateAIRecommendationStatus(resourceId, 'APPROVED');
      const updated: AIRecommendationData = { ...aiData, status: 'APPROVED' };
      setAiData(updated);
      if (onApproveSuccess) {
        onApproveSuccess(recommendation.id, updated);
      }
      if (onNotify) {
        onNotify(`Recommendation for ${recommendation.resource} approved!`);
      }
    } catch (err: any) {
      console.error('Approval failed:', err);
      if (onNotify) onNotify(`Approval error: ${err?.message || 'Could not update status'}`);
    } finally {
      setApproving(false);
    }
  };

  if (!recommendation) return null;

  const currentCost = aiData?.current_monthly_cost || recommendation.cost || 0;
  const savings = aiData?.estimated_monthly_savings || recommendation.savings || 0;
  const savingsPct = aiData?.estimated_savings_percentage || (currentCost > 0 ? Math.round((savings / currentCost) * 100) : 0);
  const isApproved = aiData?.status === 'APPROVED';

  const getRiskBadge = (risk: string) => {
    const r = (risk || 'LOW').toUpperCase();
    if (r === 'HIGH') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20">
          <ShieldAlert size={13} className="text-red-400" /> High Risk
        </span>
      );
    }
    if (r === 'MEDIUM') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <AlertTriangle size={13} className="text-amber-400" /> Medium Risk
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
        <ShieldCheck size={13} className="text-emerald-400" /> Low Risk
      </span>
    );
  };

  const getActionBadge = (action: string) => {
    const a = (action || 'RIGHTSIZE').toUpperCase();
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-bold tracking-wide uppercase bg-primary/10 text-primary border border-primary/20">
        <Zap size={11} /> {a}
      </span>
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl sm:max-w-3xl border-border bg-card shadow-2xl p-0 overflow-hidden rounded-xl">
        {/* Glow Header */}
        <div className="relative border-b border-border bg-gradient-to-r from-primary/10 via-background to-secondary/30 p-6 sm:p-7">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-2">
            <div className="flex items-center gap-2">
              <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary/20 text-primary border border-primary/30 shadow-sm">
                <Sparkles size={16} className="text-primary animate-pulse" />
              </span>
              <span className="text-[11px] font-mono uppercase tracking-wider font-bold text-primary">
                AI FinOps Optimization Engine
              </span>
            </div>

            {/* Provider Switcher Selector */}
            <div className="flex items-center gap-2">
              <Select 
                value={selectedProvider} 
                onValueChange={(val) => {
                  setSelectedProvider(val);
                  fetchAi(val);
                }}
              >
                <SelectTrigger className="h-8 text-xs font-medium bg-card/80 border-border w-[180px]">
                  <SelectValue placeholder="Model Provider" />
                </SelectTrigger>
                <SelectContent className="bg-card border-border">
                  <SelectItem value="auto">Auto (Failover Chain)</SelectItem>
                  <SelectItem value="openrouter">OpenRouter (Gemini 2.5)</SelectItem>
                  <SelectItem value="groq">Groq (Qwen 27B LPU)</SelectItem>
                  <SelectItem value="gemini">Gemini Direct</SelectItem>
                  <SelectItem value="mock">Deterministic Policy Engine</SelectItem>
                </SelectContent>
              </Select>

              <Button 
                variant="ghost" 
                size="icon" 
                className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-accent/40"
                onClick={() => fetchAi(selectedProvider)}
                disabled={loading}
                title="Re-run AI Analysis"
              >
                <RefreshCw size={14} className={loading ? 'animate-spin text-primary' : ''} />
              </Button>
            </div>
          </div>

          <DialogTitle className="text-xl sm:text-2xl font-bold tracking-tight text-foreground flex flex-wrap items-center gap-2.5">
            <span>{recommendation.title}</span>
            <Badge variant="outline" className="text-xs uppercase font-mono px-2 py-0.5 border-border">
              {recommendation.provider}
            </Badge>
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground mt-1 flex flex-wrap items-center gap-2">
            <span>Resource: <strong className="text-foreground font-mono">{recommendation.resource}</strong></span>
            <span className="text-[10px] bg-secondary/90 text-foreground px-2 py-0.5 rounded border border-border font-semibold">
              {getCategoryForRecommendation(aiData || recommendation)}
            </span>
            <span>·</span>
            <span className="text-foreground/90 font-medium">{getServiceForRecommendation(aiData || recommendation)}</span>
            <span>·</span>
            <span className="font-mono text-muted-foreground">ID: {recommendation.id}</span>
          </DialogDescription>
        </div>

        {/* Content Body */}
        <div className="p-6 sm:p-7 space-y-6 max-h-[72vh] overflow-y-auto custom-scrollbar">
          {loading ? (
            <div className="py-14 flex flex-col items-center justify-center text-center space-y-4">
              <div className="relative">
                <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/30 flex items-center justify-center shadow-lg animate-pulse">
                  <Sparkles size={28} className="text-primary animate-spin" />
                </div>
              </div>
              <div>
                <h4 className="text-sm font-semibold text-foreground">Analyzing Multi-Cloud Telemetry...</h4>
                <p className="text-xs text-muted-foreground max-w-sm mt-1">
                  Synthesizing 30-day CPU, RAM, and IOPS metrics against the FinOps Prompt Library via LLM.
                </p>
              </div>
            </div>
          ) : error ? (
            <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive space-y-2">
              <div className="flex items-center gap-2 font-semibold text-sm">
                <AlertTriangle size={16} /> Error Generating AI Recommendation
              </div>
              <p className="text-xs opacity-90">{error}</p>
              <Button size="sm" variant="outline" onClick={() => fetchAi(selectedProvider)} className="mt-2 text-xs">
                Retry Analysis
              </Button>
            </div>
          ) : aiData ? (
            <>
              {/* Asset Identity Banner */}
              <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-secondary/30 border border-border/70 text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground font-medium">Category:</span>
                  <span className="px-2 py-0.5 rounded font-semibold bg-secondary text-foreground border border-border text-[11px]">
                    {getCategoryForRecommendation(aiData || recommendation)}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground font-medium">Cloud Service:</span>
                  <strong className="text-foreground font-semibold">{getServiceForRecommendation(aiData || recommendation)}</strong>
                </div>
                <div className="flex items-center gap-2 text-muted-foreground">
                  <span>Provider:</span>
                  <strong className="text-foreground font-sans font-medium">{aiData.provider || recommendation.provider}</strong>
                </div>
              </div>

              {/* Top 3 KPI Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {/* 1. Proposed Action & Sizing */}
                <div className="p-4 rounded-xl border border-border bg-card/60 shadow-sm flex flex-col justify-between">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground font-bold flex items-center justify-between">
                    PROPOSED ACTION
                    {getActionBadge(aiData.action)}
                  </span>
                  <div className="mt-3">
                    <div className="text-base font-bold text-foreground flex items-center gap-2">
                      <span className="line-through text-muted-foreground text-xs font-mono">
                        {aiData.current_sku || 'Current'}
                      </span>
                      {aiData.target_sku ? (
                        <>
                          <ArrowRight size={13} className="text-primary shrink-0" />
                          <span className="text-primary font-mono font-bold text-sm bg-primary/10 px-2 py-0.5 rounded border border-primary/20">
                            {aiData.target_sku}
                          </span>
                        </>
                      ) : (
                        <span className="text-foreground text-xs font-mono">Decommission</span>
                      )}
                    </div>
                  </div>
                </div>

                {/* 2. Projected Financial Impact */}
                <div className="p-4 rounded-xl border border-border bg-card/60 shadow-sm flex flex-col justify-between">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground font-bold">
                    POTENTIAL SAVINGS
                  </span>
                  <div className="mt-2">
                    <div className="flex items-baseline gap-1.5">
                      <span className="text-2xl font-bold text-emerald-400">
                        {money(savings)}
                      </span>
                      <span className="text-xs text-muted-foreground">/mo</span>
                    </div>
                    <span className="text-[11px] font-semibold text-emerald-500/90 flex items-center gap-1 mt-0.5">
                      <TrendingDown size={12} /> {savingsPct}% monthly cost cut
                    </span>
                  </div>
                </div>

                {/* 3. Operational Risk Level */}
                <div className="p-4 rounded-xl border border-border bg-card/60 shadow-sm flex flex-col justify-between">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground font-bold">
                    OPERATIONAL RISK
                  </span>
                  <div className="mt-2 flex items-center justify-between">
                    <div>{getRiskBadge(aiData.risk_level)}</div>
                    <span className="text-[10px] text-muted-foreground font-mono">
                      {isApproved ? '✅ Approved' : 'Pending Review'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Technical Justification Section */}
              <div className="p-4 rounded-xl border border-border bg-secondary/20 space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-foreground">
                  <Info size={15} className="text-primary" />
                  <span>Technical Justification (Ground Telemetry & Safety Buffer)</span>
                </div>
                <p className="text-xs sm:text-sm text-foreground/90 leading-relaxed pl-6">
                  {aiData.justification}
                </p>
              </div>

              {/* Remediation Steps Checklist */}
              {aiData.remediation_steps && aiData.remediation_steps.length > 0 && (
                <div className="space-y-2.5">
                  <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                    <Layers size={14} className="text-primary" />
                    Recommended Implementation Sequence
                  </h4>
                  <div className="grid gap-2 pl-1">
                    {aiData.remediation_steps.map((step, idx) => (
                      <div 
                        key={idx} 
                        className="flex items-start gap-2.5 text-xs text-foreground/90 p-2.5 rounded-lg border border-border/70 bg-card/40"
                      >
                        <span className="flex items-center justify-center w-5 h-5 rounded-full bg-primary/10 text-primary text-[10px] font-bold shrink-0 mt-0.5">
                          {idx + 1}
                        </span>
                        <span className="leading-snug">{step}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Copyable CLI Command Box */}
              {aiData.remediation_command && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                      <Terminal size={14} className="text-primary" />
                      Executable Remediation CLI Command
                    </span>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleCopyCommand(aiData.remediation_command || '')}
                      className="h-7 text-xs gap-1.5 text-primary hover:bg-primary/10"
                    >
                      {copied ? (
                        <>
                          <Check size={13} className="text-emerald-400" />
                          <span className="text-emerald-400 font-semibold">Copied!</span>
                        </>
                      ) : (
                        <>
                          <Copy size={13} />
                          <span>Copy CLI</span>
                        </>
                      )}
                    </Button>
                  </div>
                  <div className="relative rounded-lg bg-zinc-950 p-3.5 border border-zinc-800 text-zinc-100 font-mono text-xs overflow-x-auto shadow-inner leading-relaxed">
                    <code>{aiData.remediation_command}</code>
                  </div>
                </div>
              )}

              {/* Model & Audit Meta Pill */}
              <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-border text-[11px] text-muted-foreground font-mono">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block animate-ping" />
                  Synthesized via: <strong className="text-foreground">{aiData.llm_provider_used}</strong> ({aiData.llm_model_used})
                </span>
                <span>
                  Analyzed at: {new Date(aiData.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            </>
          ) : (
            <div className="py-8 text-center text-xs text-muted-foreground">
              Click below to initiate live AI analysis on this cloud resource.
            </div>
          )}
        </div>

        {/* Modal Footer Toolbar */}
        <div className="border-t border-border bg-card p-4 sm:p-5 flex flex-wrap items-center justify-between gap-3">
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => onOpenChange(false)}
            className="text-muted-foreground hover:text-foreground text-xs"
          >
            Close
          </Button>

          <div className="flex items-center gap-2">
            {aiData?.remediation_command && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleCopyCommand(aiData.remediation_command || '')}
                className="text-xs gap-1.5"
              >
                {copied ? <Check size={13} /> : <Copy size={13} />}
                {copied ? 'Copied' : 'Copy CLI'}
              </Button>
            )}

            <Button
              variant={isApproved ? 'secondary' : 'default'}
              size="sm"
              disabled={approving || isApproved}
              onClick={handleApprove}
              className="text-xs font-semibold gap-1.5 shadow-sm"
            >
              {approving ? (
                <RefreshCw size={13} className="animate-spin" />
              ) : isApproved ? (
                <CheckCircle2 size={13} className="text-emerald-400" />
              ) : (
                <Check size={13} />
              )}
              {isApproved ? 'Approved & Ready' : 'Approve Recommendation'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
