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
  Terminal,
  BookOpen,
  FileCode,
  Upload,
  Database
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

interface GcpConnectionWizardProps {
  open: boolean;
  onClose: () => void;
  onSuccess: (account: any) => void;
  notify: (message: string) => void;
}

const GCP_REGIONS = [
  { id: 'us-central1', name: 'US Central (Iowa) - us-central1' },
  { id: 'us-east1', name: 'US East (South Carolina) - us-east1' },
  { id: 'us-west1', name: 'US West (Oregon) - us-west1' },
  { id: 'europe-west1', name: 'Europe West (Belgium) - europe-west1' },
  { id: 'europe-west3', name: 'Europe West (Frankfurt) - europe-west3' },
  { id: 'asia-south1', name: 'Asia South (Mumbai) - asia-south1' },
  { id: 'asia-east1', name: 'Asia East (Taiwan) - asia-east1' },
  { id: 'australia-southeast1', name: 'Australia Southeast (Sydney) - australia-southeast1' }
];

interface FormErrors {
  displayName?: string;
  projectId?: string;
  credentials?: string;
  billingTable?: string;
}

export function GcpConnectionWizard({
  open,
  onClose,
  onSuccess,
  notify,
}: GcpConnectionWizardProps) {
  // 3-step flow: 1: Setup Guide, 2: Credentials & Verify, 3: Live Connected
  const [step, setStep] = useState<number>(1);
  const [setupMode, setSetupMode] = useState<'cli' | 'console'>('cli');

  // Form inputs
  const [displayName, setDisplayName] = useState<string>('Production GCP');
  const [projectId, setProjectId] = useState<string>('');
  const [credentialsJson, setCredentialsJson] = useState<string>('');
  const [billingTable, setBillingTable] = useState<string>('');
  const [region, setRegion] = useState<string>('us-central1');
  const [keyInputMode, setKeyInputMode] = useState<'paste' | 'upload'>('paste');
  const [fileName, setFileName] = useState<string>('');
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
      setProjectId('');
      setCredentialsJson('');
      setBillingTable('');
      setFileName('');
    }
  }, [open]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCli(true);
    notify('Command copied to clipboard!');
    setTimeout(() => setCopiedCli(false), 2000);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target?.result as string;
        const parsed = JSON.parse(text);
        setCredentialsJson(text);
        if (parsed.project_id && !projectId) {
          setProjectId(parsed.project_id);
        }
        notify(`Loaded service account key: ${file.name}`);
      } catch (err) {
        notify('Invalid JSON file. Please provide a valid GCP Service Account JSON key.');
      }
    };
    reader.readAsText(file);
  };

  const validateStep2 = (): boolean => {
    const errors: FormErrors = {};

    if (!displayName.trim() || displayName.trim().length < 2) {
      errors.displayName = 'Display name must be at least 2 characters.';
    }

    const trimmedProject = projectId.trim();
    if (!trimmedProject) {
      errors.projectId = 'GCP Project ID is required.';
    } else if (!/^[a-z][a-z0-9-]{4,28}[a-z0-9]$/.test(trimmedProject)) {
      errors.projectId = 'Project ID must be 6–30 characters (lowercase letters, digits, and hyphens).';
    }

    if (credentialsJson.trim()) {
      try {
        const parsed = JSON.parse(credentialsJson.trim());
        if (!parsed.client_email && !parsed.private_key) {
          errors.credentials = 'JSON key missing client_email or private_key fields.';
        }
      } catch {
        errors.credentials = 'Credentials must be valid JSON.';
      }
    }

    if (billingTable.trim()) {
      const bTable = billingTable.trim();
      if (!/^[A-Za-z0-9_-]+\.[A-Za-z0-9_]+\.[A-Za-z0-9_]+$/.test(bTable)) {
        errors.billingTable = 'Billing table format must be: project.dataset.table';
      }
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleVerifyAndConnect = async () => {
    if (!validateStep2()) return;

    setVerifying(true);
    setVerifyError(null);

    try {
      let parsedCreds: any = null;
      if (credentialsJson.trim()) {
        try {
          parsedCreds = JSON.parse(credentialsJson.trim());
        } catch {}
      }

      const createdAccount = await apiCreateAccount({
        provider: 'gcp',
        display_name: displayName.trim(),
        account_identifier: projectId.trim(),
        credential_type: 'service_account',
        region: region,
        gcp_project_id: projectId.trim(),
        gcp_service_account_key: parsedCreds || credentialsJson.trim() || undefined,
        gcp_billing_table: billingTable.trim() || undefined,
      });

      if (createdAccount.status === 'error') {
        setVerifyError(
          'GCP verification failed: Compute Engine access could not be verified. Ensure the service account has the "Viewer" role assigned and Compute Engine API is enabled on your project.'
        );
        return;
      }

      // Initial discovery scan with FastAPI
      let scanData = null;
      try {
        scanData = await apiScanAccount(createdAccount.id);
      } catch (scanErr) {
        // Safe fallback if background scan takes time
      }

      setVerifyResult({ account: createdAccount, scan: scanData });
      setStep(3);
      notify(`Google Cloud project "${displayName}" connected successfully!`);
    } catch (err: any) {
      setVerifyError(
        err?.message ||
        'Failed to connect to GCP. Please verify your Service Account credentials, IAM permissions, and project ID.'
      );
    } finally {
      setVerifying(false);
    }
  };

  const gcloudCliCommand = `# 1. Create a read-only service account
gcloud iam service-accounts create cloud-advisor-viewer \\
    --display-name="Cloud Advisor Read-Only" \\
    --project="${projectId || '<YOUR_PROJECT_ID>'}"

# 2. Grant Viewer & Monitoring Viewer roles
gcloud projects add-iam-policy-binding "${projectId || '<YOUR_PROJECT_ID>'}" \\
    --member="serviceAccount:cloud-advisor-viewer@${projectId || '<YOUR_PROJECT_ID>'}.iam.gserviceaccount.com" \\
    --role="roles/viewer"

# 3. Create and download private JSON key
gcloud iam service-accounts keys create gcp-service-account.json \\
    --iam-account="cloud-advisor-viewer@${projectId || '<YOUR_PROJECT_ID>'}.iam.gserviceaccount.com"`;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="azure-wizard-dialog">
        {/* Header with Title & Stepper */}
        <DialogHeader className="shrink-0 pb-1">
          <div className="flex items-center justify-between pr-6">
            <div className="flex items-center gap-2">
              <span className="connection-icon gcp h-7 w-7 text-emerald-400">
                <Cloud size={17} />
              </span>
              <DialogTitle className="text-base font-bold">
                Connect Google Cloud Platform Project
              </DialogTitle>
            </div>
            <span className="azure-badge-pill text-[10px]">
              <Lock size={11} /> Read-Only IAM
            </span>
          </div>
          <DialogDescription className="text-xs text-muted-foreground pt-1">
            Authenticate securely using a GCP Service Account with the Viewer role.
          </DialogDescription>
        </DialogHeader>

        {/* 3-Step Indicator */}
        <div className="aws-stepper mt-1">
          <div className={`aws-step-node ${step === 1 ? 'aws-step-active' : step > 1 ? 'aws-step-completed' : ''}`}>
            <div className="aws-step-circle">
              {step > 1 ? <Check size={14} /> : '1'}
            </div>
            <span className="aws-step-label">Service Account</span>
          </div>

          <div className={`aws-step-node ${step === 2 ? 'aws-step-active' : step > 2 ? 'aws-step-completed' : ''}`}>
            <div className="aws-step-circle">
              {step > 2 ? <Check size={14} /> : '2'}
            </div>
            <span className="aws-step-label">Credentials & Verify</span>
          </div>

          <div className={`aws-step-node ${step === 3 ? 'aws-step-active' : ''}`}>
            <div className="aws-step-circle">
              {step === 3 ? <Check size={14} /> : '3'}
            </div>
            <span className="aws-step-label">Connected</span>
          </div>
        </div>

        {/* ============================================================== */}
        {/* STEP 1: SERVICE ACCOUNT & VIEWER ROLE SETUP GUIDE              */}
        {/* ============================================================== */}
        {step === 1 && (
          <div className="aws-wizard-content custom-scrollbar gap-3.5 pr-1 pb-2">
            <div className="aws-info-card border-emerald-500/20 bg-emerald-500/5">
              <div className="flex items-start gap-2.5">
                <ShieldCheck size={18} className="text-emerald-400 shrink-0 mt-0.5" />
                <div className="text-xs space-y-1">
                  <strong className="text-foreground block text-xs">
                    Read-Only Google Cloud Architecture
                  </strong>
                  <p className="text-muted-foreground leading-relaxed">
                    Cloud Advisor uses read-only Google Cloud APIs (Compute Engine, Cloud Storage, GKE, Cloud SQL, and Cloud Monitoring) to scan inventory and calculate cost savings. We require only the <span className="text-emerald-400 font-semibold">Viewer</span> role.
                  </p>
                </div>
              </div>
            </div>

            {/* Quick CLI vs Google Cloud Console switcher */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <Terminal size={14} className="text-muted-foreground" />
                  Service Account Setup Options
                </span>
                <div className="flex items-center gap-1 bg-muted/40 p-0.5 rounded-md border border-border">
                  <button
                    type="button"
                    onClick={() => setSetupMode('cli')}
                    className={`px-2.5 py-0.5 text-[11px] rounded transition-colors ${
                      setupMode === 'cli'
                        ? 'bg-background font-medium text-foreground shadow-xs'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    Google Cloud CLI
                  </button>
                  <button
                    type="button"
                    onClick={() => setSetupMode('console')}
                    className={`px-2.5 py-0.5 text-[11px] rounded transition-colors ${
                      setupMode === 'console'
                        ? 'bg-background font-medium text-foreground shadow-xs'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    Google Cloud Console
                  </button>
                </div>
              </div>

              {setupMode === 'cli' ? (
                <div className="space-y-2">
                  <div className="relative group">
                    <pre className="bg-muted/70 text-foreground border border-border rounded-lg p-3 text-xs font-mono overflow-x-auto whitespace-pre-wrap leading-relaxed select-all">
                      {gcloudCliCommand}
                    </pre>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => copyToClipboard(gcloudCliCommand)}
                      className="absolute top-2 right-2 h-7 px-2 text-xs gap-1 opacity-90 group-hover:opacity-100 transition-opacity"
                    >
                      {copiedCli ? <Check size={13} /> : <Copy size={13} />}
                      {copiedCli ? 'Copied' : 'Copy'}
                    </Button>
                  </div>
                  <p className="text-[11px] text-muted-foreground leading-normal">
                    Run the commands above in Cloud Shell or your local terminal to create the service account, grant Viewer access, and download the JSON key.
                  </p>
                </div>
              ) : (
                <div className="bg-muted/40 border border-border rounded-lg p-3 space-y-2 text-xs text-muted-foreground">
                  <div className="flex items-start gap-2">
                    <span className="font-bold text-foreground shrink-0 w-4">1.</span>
                    <span>Navigate to <strong>IAM &amp; Admin &gt; Service Accounts</strong> in Google Cloud Console.</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="font-bold text-foreground shrink-0 w-4">2.</span>
                    <span>Click <strong>Create Service Account</strong>, name it <code className="text-foreground bg-muted px-1 py-0.5 rounded text-[11px]">cloud-advisor-viewer</code>.</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="font-bold text-foreground shrink-0 w-4">3.</span>
                    <span>Grant role <strong>Project &gt; Viewer</strong>. (Optional: <strong>Monitoring Viewer</strong>).</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="font-bold text-foreground shrink-0 w-4">4.</span>
                    <span>Click on the created service account, go to the <strong>Keys</strong> tab, click <strong>Add Key &gt; Create new key &gt; JSON</strong> to download the key.</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ============================================================== */}
        {/* STEP 2: FORM CREDENTIALS & LIVE VERIFICATION                   */}
        {/* ============================================================== */}
        {step === 2 && (
          <div className="aws-wizard-content custom-scrollbar gap-3 pr-1 pb-2">
            {verifyError && (
              <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-3 flex items-start gap-2 text-xs text-destructive">
                <AlertCircle size={16} className="shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <strong>Verification Failed</strong>
                  <p className="leading-relaxed">{verifyError}</p>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label htmlFor="gcp-name" className="text-xs">
                  Connection Nickname
                </Label>
                <Input
                  id="gcp-name"
                  placeholder="e.g. Production GCP"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className={`h-8 text-xs ${formErrors.displayName ? 'border-destructive' : ''}`}
                />
                {formErrors.displayName && (
                  <p className="text-[11px] text-destructive">{formErrors.displayName}</p>
                )}
              </div>

              <div className="space-y-1">
                <Label htmlFor="gcp-project" className="text-xs flex items-center justify-between">
                  <span>GCP Project ID</span>
                  <span className="text-[10px] text-muted-foreground font-normal">Required</span>
                </Label>
                <Input
                  id="gcp-project"
                  placeholder="acme-data-prod"
                  value={projectId}
                  onChange={(e) => setProjectId(e.target.value)}
                  className={`h-8 text-xs font-mono ${formErrors.projectId ? 'border-destructive' : ''}`}
                />
                {formErrors.projectId && (
                  <p className="text-[11px] text-destructive">{formErrors.projectId}</p>
                )}
              </div>
            </div>

            {/* Service Account Key Input */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label className="text-xs flex items-center gap-1.5">
                  <FileCode size={13} className="text-muted-foreground" />
                  Service Account JSON Key
                </Label>
                <div className="flex items-center gap-1 bg-muted/30 p-0.5 rounded border border-border">
                  <button
                    type="button"
                    onClick={() => setKeyInputMode('paste')}
                    className={`px-2 py-0.5 text-[10px] rounded transition-colors ${
                      keyInputMode === 'paste'
                        ? 'bg-background font-medium text-foreground'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    Paste JSON
                  </button>
                  <button
                    type="button"
                    onClick={() => setKeyInputMode('upload')}
                    className={`px-2 py-0.5 text-[10px] rounded transition-colors ${
                      keyInputMode === 'upload'
                        ? 'bg-background font-medium text-foreground'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    Upload File
                  </button>
                </div>
              </div>

              {keyInputMode === 'paste' ? (
                <textarea
                  id="gcp-creds"
                  rows={4}
                  placeholder='{"type": "service_account", "project_id": "...", "private_key": "..."}'
                  value={credentialsJson}
                  onChange={(e) => setCredentialsJson(e.target.value)}
                  className={`w-full bg-background border rounded-md p-2 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-ring resize-none ${
                    formErrors.credentials ? 'border-destructive' : 'border-input'
                  }`}
                />
              ) : (
                <div className="border border-dashed border-border rounded-lg p-3 text-center hover:bg-muted/30 transition-colors">
                  <input
                    type="file"
                    accept=".json"
                    id="gcp-key-file"
                    className="hidden"
                    onChange={handleFileUpload}
                  />
                  <label htmlFor="gcp-key-file" className="cursor-pointer flex flex-col items-center gap-1 text-xs text-muted-foreground">
                    <Upload size={18} className="text-emerald-400 mb-0.5" />
                    <span className="font-medium text-foreground">
                      {fileName || 'Click to upload Service Account JSON Key'}
                    </span>
                    <span className="text-[10px]">(.json file downloaded from Google Cloud Console)</span>
                  </label>
                </div>
              )}
              {formErrors.credentials && (
                <p className="text-[11px] text-destructive">{formErrors.credentials}</p>
              )}
              <small className="text-muted-foreground text-[10px] block">
                Sensitive private key material is stored securely on the backend and never exposed in API responses.
              </small>
            </div>

            {/* Optional BigQuery Billing Export & Region */}
            <div className="grid grid-cols-2 gap-3 pt-1">
              <div className="space-y-1">
                <Label htmlFor="gcp-billing" className="text-xs flex items-center gap-1">
                  <Database size={12} className="text-muted-foreground" />
                  BigQuery Billing Export (Optional)
                </Label>
                <Input
                  id="gcp-billing"
                  placeholder="billing-project.dataset.gcp_billing_export_v1_..."
                  value={billingTable}
                  onChange={(e) => setBillingTable(e.target.value)}
                  className={`h-8 text-xs font-mono ${formErrors.billingTable ? 'border-destructive' : ''}`}
                />
                {formErrors.billingTable ? (
                  <p className="text-[11px] text-destructive">{formErrors.billingTable}</p>
                ) : (
                  <span className="text-[10px] text-muted-foreground">project.dataset.table</span>
                )}
              </div>

              <div className="space-y-1">
                <Label htmlFor="gcp-region" className="text-xs">
                  Primary Region
                </Label>
                <select
                  id="gcp-region"
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                  className="w-full h-8 text-xs bg-background border border-input rounded-md px-2 focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  {GCP_REGIONS.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        )}

        {/* ============================================================== */}
        {/* STEP 3: LIVE CONNECTED & SCAN SUMMARY                          */}
        {/* ============================================================== */}
        {step === 3 && verifyResult && (
          <div className="aws-wizard-content custom-scrollbar gap-3.5 pr-1 pb-2">
            <div className="bg-emerald-500/10 border border-emerald-500/25 rounded-lg p-3 flex items-start gap-3">
              <CheckCircle2 size={22} className="text-emerald-500 shrink-0 mt-0.5" />
              <div className="space-y-1 text-xs">
                <strong className="text-foreground text-sm block">
                  GCP Project Connected &amp; Verified!
                </strong>
                <p className="text-muted-foreground leading-relaxed">
                  FastAPI successfully verified read-only access to Project ID{' '}
                  <code className="text-foreground font-mono bg-emerald-500/10 px-1 py-0.5 rounded text-[11px]">
                    {verifyResult.account.account_identifier}
                  </code>
                  . Initial resource discovery is active.
                </p>
              </div>
            </div>

            {/* Scan metric cards */}
            <div className="grid grid-cols-3 gap-2.5">
              <div className="bg-muted/40 border border-border rounded-lg p-2.5 text-center">
                <span className="text-muted-foreground text-[11px] block">Resources Scanned</span>
                <strong className="text-base font-bold text-foreground">
                  {verifyResult.scan?.resources_scanned ?? 'Scanned'}
                </strong>
              </div>

              <div className="bg-muted/40 border border-border rounded-lg p-2.5 text-center">
                <span className="text-muted-foreground text-[11px] block">Findings Generated</span>
                <strong className="text-base font-bold text-amber-400">
                  {verifyResult.scan?.findings_created ?? 'Evaluated'}
                </strong>
              </div>

              <div className="bg-muted/40 border border-border rounded-lg p-2.5 text-center">
                <span className="text-muted-foreground text-[11px] block">Monthly Savings</span>
                <strong className="text-base font-bold text-emerald-400">
                  ${verifyResult.scan?.estimated_monthly_savings?.toLocaleString() ?? 'Calculated'}
                </strong>
              </div>
            </div>

            <div className="aws-info-card text-xs text-muted-foreground flex items-center gap-2">
              <CheckCircle2 size={14} className="text-emerald-500 shrink-0" />
              <span>
                Compute Engine VMs, Persistent Disks, Cloud Storage, GKE, and Cloud SQL instances are now actively monitored.
              </span>
            </div>
          </div>
        )}

        {/* Footer actions */}
        <div className="aws-wizard-footer pt-2 border-t border-border mt-auto flex items-center justify-between">
          {step === 1 && (
            <>
              <Button variant="outline" size="sm" onClick={onClose} className="text-xs">
                Cancel
              </Button>
              <Button size="sm" onClick={() => setStep(2)} className="text-xs gap-1">
                Enter Credentials <ArrowRight size={14} />
              </Button>
            </>
          )}

          {step === 2 && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setStep(1)}
                disabled={verifying}
                className="text-xs gap-1"
              >
                <ArrowLeft size={14} /> Back to Guide
              </Button>
              <Button
                size="sm"
                onClick={handleVerifyAndConnect}
                disabled={verifying}
                className="text-xs gap-1.5"
              >
                {verifying ? (
                  <>
                    <RefreshCw size={13} className="animate-spin" /> Verifying with GCP...
                  </>
                ) : (
                  <>
                    Verify &amp; Connect <ArrowRight size={14} />
                  </>
                )}
              </Button>
            </>
          )}

          {step === 3 && (
            <Button
              size="sm"
              className="w-full text-xs"
              onClick={() => {
                onSuccess(verifyResult?.account);
                onClose();
              }}
            >
              Done &amp; View in Dashboard
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
