import { useState, useEffect } from 'react';
import {
  CheckCircle2,
  Copy,
  Check,
  Cloud,
  ShieldCheck,
  AlertCircle,
  ArrowRight,
  ArrowLeft,
  RefreshCw,
  Lock,
  KeyRound,
  Eye,
  EyeOff,
  Terminal,
  BookOpen
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import {
  apiCreateAccount,
  apiScanAccount
} from '@/config/api';

interface AzureConnectionWizardProps {
  open: boolean;
  onClose: () => void;
  onSuccess: (account: any) => void;
  notify: (message: string) => void;
}

const AZURE_REGIONS = [
  { id: 'eastus', name: 'East US (Virginia) - eastus' },
  { id: 'westeurope', name: 'West Europe (Netherlands) - westeurope' },
  { id: 'centralindia', name: 'Central India (Pune) - centralindia' },
  { id: 'southeastasia', name: 'Southeast Asia (Singapore) - southeastasia' },
  { id: 'eastus2', name: 'East US 2 (Virginia) - eastus2' },
  { id: 'uksouth', name: 'UK South (London) - uksouth' },
  { id: 'westus2', name: 'West US 2 (Washington) - westus2' },
  { id: 'northeurope', name: 'North Europe (Ireland) - northeurope' }
];

interface FormErrors {
  displayName?: string;
  subscriptionId?: string;
  tenantId?: string;
  clientId?: string;
  clientSecret?: string;
}

export function AzureConnectionWizard({
  open,
  onClose,
  onSuccess,
  notify,
}: AzureConnectionWizardProps) {
  // 3-step flow: 1: Setup Guide, 2: Credentials & Verify, 3: Live Connected
  const [step, setStep] = useState<number>(1);
  const [setupMode, setSetupMode] = useState<'cli' | 'portal'>('cli');

  // Form inputs
  const [displayName, setDisplayName] = useState<string>('Production Azure');
  const [subscriptionId, setSubscriptionId] = useState<string>('');
  const [tenantId, setTenantId] = useState<string>('');
  const [clientId, setClientId] = useState<string>('');
  const [clientSecret, setClientSecret] = useState<string>('');
  const [region, setRegion] = useState<string>('westeurope');
  const [showSecret, setShowSecret] = useState<boolean>(false);
  const [formErrors, setFormErrors] = useState<FormErrors>({});

  const [verifying, setVerifying] = useState<boolean>(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [verifyResult, setVerifyResult] = useState<{ account: any; scan?: any } | null>(null);

  const [copiedCli, setCopiedCli] = useState<boolean>(false);

  useEffect(() => {
    if (open) {
      setStep(1);
      setVerifyError(null);
      setVerifyResult(null);
      setFormErrors({});
      setSubscriptionId('');
      setTenantId('');
      setClientId('');
      setClientSecret('');
    }
  }, [open]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCli(true);
    setTimeout(() => setCopiedCli(false), 2000);
    notify('Copied to clipboard');
  };

  const validateStep2 = (): boolean => {
    const errs: FormErrors = {};
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

    if (!displayName.trim() || displayName.length < 2) {
      errs.displayName = 'Nickname must be between 2 and 40 characters.';
    }

    if (!subscriptionId.trim() || !uuidRegex.test(subscriptionId.trim())) {
      errs.subscriptionId = 'Enter a valid 36-character Azure Subscription GUID (e.g. 00000000-0000-0000-0000-000000000000).';
    }

    if (!tenantId.trim() || !uuidRegex.test(tenantId.trim())) {
      errs.tenantId = 'Enter a valid Directory / Tenant GUID (e.g. 00000000-0000-0000-0000-000000000000).';
    }

    if (!clientId.trim() || !uuidRegex.test(clientId.trim())) {
      errs.clientId = 'Enter a valid Application / Client GUID (e.g. 00000000-0000-0000-0000-000000000000).';
    }

    if (!clientSecret.trim() || clientSecret.length < 4) {
      errs.clientSecret = 'Enter the client secret value generated in your Microsoft Entra app registration.';
    }

    setFormErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleVerifyAndConnect = async () => {
    if (!validateStep2()) return;

    setVerifying(true);
    setVerifyError(null);

    try {
      // 1. Call FastAPI backend to register and verify credentials against Microsoft Entra
      const createdAccount = await apiCreateAccount({
        provider: 'azure',
        display_name: displayName.trim(),
        account_identifier: subscriptionId.trim(),
        region: region,
        credential_type: 'client_secret',
        azure_tenant_id: tenantId.trim(),
        azure_client_id: clientId.trim(),
        azure_client_secret: clientSecret.trim(),
      });

      if (createdAccount.status === 'error') {
        setVerifyError(
          'Azure verification failed: Entra ID rejected the credentials or the Service Principal does not have the "Reader" role assigned on the subscription. Please check your Tenant ID, Client ID, Client Secret, and subscription role assignment.'
        );
        return;
      }

      // 2. Initial discovery scan with FastAPI
      let scanData = null;
      try {
        scanData = await apiScanAccount(createdAccount.id);
      } catch (scanErr) {
        // Safe fallback if scan takes time
      }

      setVerifyResult({ account: createdAccount, scan: scanData });
      setStep(3);
      notify(`Azure subscription "${displayName}" connected successfully!`);
    } catch (err: any) {
      setVerifyError(
        err?.message ||
        'Failed to connect to Azure. Please verify your Entra ID credentials and subscription permissions.'
      );
    } finally {
      setVerifying(false);
    }
  };

  const azCliCommand = `az ad sp create-for-rbac --name "CloudAdvisorReader" --role "Reader" --scopes "/subscriptions/${subscriptionId || '<YOUR_SUBSCRIPTION_ID>'}"`;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="azure-wizard-dialog">
        {/* Header with Title & Stepper */}
        <DialogHeader className="shrink-0 pb-1">
          <div className="flex items-center justify-between pr-6">
            <div className="flex items-center gap-2">
              <span className="connection-icon azure h-7 w-7 text-azure">
                <Cloud size={17} />
              </span>
              <DialogTitle className="text-base font-bold">
                Connect Microsoft Azure Subscription
              </DialogTitle>
            </div>
            <span className="azure-badge-pill text-[10px]">
              <Lock size={11} /> Read-Only RBAC
            </span>
          </div>
          <DialogDescription className="text-xs text-muted-foreground pt-1">
            Authenticate securely using a Microsoft Entra Service Principal with the Reader role.
          </DialogDescription>
        </DialogHeader>

        {/* 3-Step Indicator */}
        <div className="aws-stepper mt-1">
          <div className={`aws-step-node ${step === 1 ? 'aws-step-active azure-step-active' : step > 1 ? 'aws-step-completed' : ''}`}>
            <div className="aws-step-circle">
              {step > 1 ? <Check size={14} /> : '1'}
            </div>
            <span className="aws-step-label">Service Principal</span>
          </div>

          <div className={`aws-step-node ${step === 2 ? 'aws-step-active azure-step-active' : step > 2 ? 'aws-step-completed' : ''}`}>
            <div className="aws-step-circle">
              {step > 2 ? <Check size={14} /> : '2'}
            </div>
            <span className="aws-step-label">Credentials & Verify</span>
          </div>

          <div className={`aws-step-node ${step === 3 ? 'aws-step-active azure-step-active' : ''}`}>
            <div className="aws-step-circle">
              {step === 3 ? <Check size={14} /> : '3'}
            </div>
            <span className="aws-step-label">Connected</span>
          </div>
        </div>

        {/* ============================================================== */}
        {/* STEP 1: SERVICE PRINCIPAL & READER ROLE SETUP GUIDE             */}
        {/* ============================================================== */}
        {step === 1 && (
          <div className="aws-wizard-content custom-scrollbar gap-3.5 pr-1 pb-2">
            <div className="aws-info-card border-azure/20 bg-azure/5">
              <div className="flex items-start gap-2.5">
                <ShieldCheck size={18} className="text-azure shrink-0 mt-0.5" />
                <div className="text-xs space-y-1">
                  <strong className="text-foreground block text-xs">
                    Read-Only Azure Architecture
                  </strong>
                  <p className="text-muted-foreground leading-relaxed">
                    Cloud Advisor uses standard Azure Resource Manager APIs to inspect resource sizes and analyze cost metrics. We only need the standard <span className="text-azure font-semibold">Reader</span> role assigned to your subscription.
                  </p>
                </div>
              </div>
            </div>

            {/* Quick CLI vs Azure Portal switcher */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-foreground">Choose Setup Method:</span>
                <div className="flex gap-1.5 p-0.5 rounded-md bg-secondary border border-border">
                  <button
                    type="button"
                    onClick={() => setSetupMode('cli')}
                    className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors flex items-center gap-1.5 ${setupMode === 'cli' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
                  >
                    <Terminal size={12} /> Azure CLI (Fastest)
                  </button>
                  <button
                    type="button"
                    onClick={() => setSetupMode('portal')}
                    className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors flex items-center gap-1.5 ${setupMode === 'portal' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
                  >
                    <BookOpen size={12} /> Azure Portal
                  </button>
                </div>
              </div>

              {setupMode === 'cli' ? (
                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Open Azure Cloud Shell or your local terminal, and run this single command to create the Service Principal with Reader permissions:
                  </p>
                  <div className="azure-copy-box">
                    <span className="text-[11px] text-foreground font-mono">{azCliCommand}</span>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => copyToClipboard(azCliCommand)}
                      className="h-7 px-2 shrink-0 text-muted-foreground hover:text-foreground"
                    >
                      {copiedCli ? <Check size={13} className="text-success" /> : <Copy size={13} />}
                    </Button>
                  </div>
                  <div className="text-[11px] text-muted-foreground bg-secondary/60 p-2.5 rounded-md border border-border space-y-1">
                    <span className="font-semibold text-foreground block">Command Output Maps Directly to Step 2:</span>
                    <ul className="list-disc pl-4 space-y-0.5">
                      <li><code>"tenant"</code> → Directory (Tenant) ID</li>
                      <li><code>"appId"</code> → Application (Client) ID</li>
                      <li><code>"password"</code> → Client Secret Value</li>
                    </ul>
                  </div>
                </div>
              ) : (
                <div className="space-y-2 text-xs">
                  <div className="bg-secondary/60 p-2.5 rounded-md border border-border space-y-2">
                    <div className="flex gap-2">
                      <span className="h-4 w-4 rounded-full bg-azure/20 text-azure flex items-center justify-center font-bold text-[10px] shrink-0 mt-0.5">1</span>
                      <p className="text-muted-foreground">In <strong>Microsoft Entra ID</strong>, navigate to <strong>App registrations</strong> &gt; <strong>New registration</strong>. Name it <em>CloudAdvisor</em> and click Register.</p>
                    </div>
                    <div className="flex gap-2">
                      <span className="h-4 w-4 rounded-full bg-azure/20 text-azure flex items-center justify-center font-bold text-[10px] shrink-0 mt-0.5">2</span>
                      <p className="text-muted-foreground">Under <strong>Certificates & secrets</strong>, create a <strong>New client secret</strong>. Copy the secret <em>Value</em> immediately.</p>
                    </div>
                    <div className="flex gap-2">
                      <span className="h-4 w-4 rounded-full bg-azure/20 text-azure flex items-center justify-center font-bold text-[10px] shrink-0 mt-0.5">3</span>
                      <p className="text-muted-foreground">In <strong>Subscriptions</strong>, select your target subscription &gt; <strong>Access control (IAM)</strong> &gt; <strong>Add role assignment</strong>. Assign the <strong>Reader</strong> role to <em>CloudAdvisor</em>.</p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Footer action */}
            <div className="pt-2 flex justify-end gap-2 border-t border-border mt-auto shrink-0">
              <Button variant="outline" onClick={onClose} size="sm">Cancel</Button>
              <Button onClick={() => setStep(2)} size="sm" className="gap-1.5 bg-azure text-white hover:bg-azure/90">
                Next: Enter Credentials <ArrowRight size={13} />
              </Button>
            </div>
          </div>
        )}

        {/* ============================================================== */}
        {/* STEP 2: CREDENTIALS & LIVE VERIFICATION                        */}
        {/* ============================================================== */}
        {step === 2 && (
          <div className="aws-wizard-content custom-scrollbar gap-3.5 pr-1 pb-2">
            {verifyError && (
              <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-md text-destructive text-xs flex gap-2.5 items-start">
                <AlertCircle size={16} className="shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <strong>Verification Error</strong>
                  <p className="text-[11px] leading-relaxed text-destructive/90">{verifyError}</p>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label htmlFor="az-name" className="text-xs font-semibold">Account Nickname</Label>
                <Input
                  id="az-name"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Production Azure"
                  className="h-8 text-xs"
                />
                {formErrors.displayName && <p className="text-[10px] text-destructive">{formErrors.displayName}</p>}
              </div>

              <div className="space-y-1">
                <Label htmlFor="az-region" className="text-xs font-semibold">Primary Region</Label>
                <select
                  id="az-region"
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                  className="w-full h-8 px-2 text-xs rounded-md border border-border bg-card text-foreground"
                >
                  {AZURE_REGIONS.map((r) => (
                    <option key={r.id} value={r.id}>{r.name}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="space-y-1">
              <Label htmlFor="az-sub" className="text-xs font-semibold">Azure Subscription ID (GUID)</Label>
              <Input
                id="az-sub"
                value={subscriptionId}
                onChange={(e) => setSubscriptionId(e.target.value)}
                placeholder="00000000-0000-0000-0000-000000000000"
                className="h-8 text-xs font-mono"
              />
              {formErrors.subscriptionId ? (
                <p className="text-[10px] text-destructive">{formErrors.subscriptionId}</p>
              ) : (
                <p className="text-[10px] text-muted-foreground">Target subscription to discover resources & evaluate cost rules.</p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label htmlFor="az-tenant" className="text-xs font-semibold">Directory (Tenant) ID</Label>
                <Input
                  id="az-tenant"
                  value={tenantId}
                  onChange={(e) => setTenantId(e.target.value)}
                  placeholder="00000000-0000-0000-0000-000000000000"
                  className="h-8 text-xs font-mono"
                />
                {formErrors.tenantId && <p className="text-[10px] text-destructive">{formErrors.tenantId}</p>}
              </div>

              <div className="space-y-1">
                <Label htmlFor="az-client" className="text-xs font-semibold">Application (Client) ID</Label>
                <Input
                  id="az-client"
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                  placeholder="00000000-0000-0000-0000-000000000000"
                  className="h-8 text-xs font-mono"
                />
                {formErrors.clientId && <p className="text-[10px] text-destructive">{formErrors.clientId}</p>}
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <Label htmlFor="az-secret" className="text-xs font-semibold">Client Secret Value</Label>
                <button
                  type="button"
                  onClick={() => setShowSecret(!showSecret)}
                  className="text-[11px] text-muted-foreground hover:text-foreground flex items-center gap-1"
                >
                  {showSecret ? <EyeOff size={11} /> : <Eye size={11} />}
                  {showSecret ? 'Hide' : 'Show'}
                </button>
              </div>
              <Input
                id="az-secret"
                type={showSecret ? 'text' : 'password'}
                value={clientSecret}
                onChange={(e) => setClientSecret(e.target.value)}
                placeholder="Enter client secret value"
                className="h-8 text-xs font-mono"
              />
              {formErrors.clientSecret ? (
                <p className="text-[10px] text-destructive">{formErrors.clientSecret}</p>
              ) : (
                <p className="text-[10px] text-muted-foreground">Generated in Entra ID &gt; Certificates & secrets.</p>
              )}
            </div>

            <div className="flex items-center gap-2 text-xs text-muted-foreground pt-1">
              <Lock size={12} className="text-azure shrink-0" />
              <span>Credentials are encrypted and processed securely by the FastAPI backend SDK.</span>
            </div>

            {/* Footer action */}
            <div className="pt-2 flex justify-between items-center border-t border-border mt-auto shrink-0">
              <Button variant="outline" onClick={() => setStep(1)} size="sm" className="gap-1.5">
                <ArrowLeft size={13} /> Back
              </Button>
              <Button
                onClick={handleVerifyAndConnect}
                disabled={verifying}
                size="sm"
                className="gap-1.5 bg-azure text-white hover:bg-azure/90"
              >
                {verifying ? (
                  <>
                    <RefreshCw size={13} className="animate-spin" /> Verifying Entra ID...
                  </>
                ) : (
                  <>
                    <KeyRound size={13} /> Verify & Connect
                  </>
                )}
              </Button>
            </div>
          </div>
        )}

        {/* ============================================================== */}
        {/* STEP 3: SUCCESS & DISCOVERY SUMMARY                            */}
        {/* ============================================================== */}
        {step === 3 && (
          <div className="aws-wizard-content custom-scrollbar items-center text-center py-2 gap-4 pr-1 pb-2">
            <div className="h-12 w-12 rounded-full bg-success/20 text-success flex items-center justify-center">
              <CheckCircle2 size={26} />
            </div>

            <div className="space-y-1">
              <h3 className="text-base font-bold text-foreground">Azure Subscription Connected!</h3>
              <p className="text-xs text-muted-foreground">
                Successfully authenticated with Microsoft Entra ID and verified Subscription Reader permissions.
              </p>
            </div>

            {/* Stats Band */}
            <div className="grid grid-cols-3 gap-3 w-full max-w-md bg-secondary/60 p-3 rounded-lg border border-border">
              <div>
                <small className="text-[10px] text-muted-foreground font-semibold block">RESOURCES SCANNED</small>
                <strong className="text-lg font-bold text-foreground">
                  {verifyResult?.scan?.resources_scanned ?? 0}
                </strong>
              </div>
              <div>
                <small className="text-[10px] text-muted-foreground font-semibold block">FINDINGS GENERATED</small>
                <strong className="text-lg font-bold text-foreground">
                  {verifyResult?.scan?.findings_created ?? 0}
                </strong>
              </div>
              <div>
                <small className="text-[10px] text-muted-foreground font-semibold block">POTENTIAL SAVINGS</small>
                <strong className="text-lg font-bold text-success">
                  ${verifyResult?.scan?.estimated_monthly_savings ?? '0.00'}/mo
                </strong>
              </div>
            </div>

            {/* Connection Details Pill */}
            <div className="w-full max-w-md bg-card p-3 rounded-lg border border-border text-left text-xs space-y-1.5">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Subscription ID:</span>
                <span className="font-mono font-medium">•••• •••• {subscriptionId.slice(-4)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Directory (Tenant):</span>
                <span className="font-mono font-medium">•••• •••• {tenantId.slice(-4)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Region:</span>
                <span className="font-medium">{region}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Role:</span>
                <span className="text-azure font-medium">Reader (Read-Only)</span>
              </div>
            </div>

            {/* Footer action */}
            <div className="pt-2 w-full flex justify-end border-t border-border mt-auto shrink-0">
              <Button
                onClick={() => {
                  if (verifyResult?.account) {
                    onSuccess(verifyResult.account);
                  }
                  onClose();
                }}
                size="sm"
                className="gap-1.5 bg-azure text-white hover:bg-azure/90"
              >
                View Connected Accounts <ArrowRight size={13} />
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
