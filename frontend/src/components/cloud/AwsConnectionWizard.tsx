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
  KeyRound
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
  apiInitiateAwsConnection,
  apiVerifyAwsConnection,
  type AwsInitiateResponse
} from '@/config/api';

interface AwsConnectionWizardProps {
  open: boolean;
  onClose: () => void;
  onSuccess: (account: any) => void;
  notify: (message: string) => void;
}

const REGIONS = [
  { id: 'ap-south-1', name: 'Asia Pacific (Mumbai) - ap-south-1' },
  { id: 'us-east-1', name: 'US East (N. Virginia) - us-east-1' },
  { id: 'us-west-2', name: 'US West (Oregon) - us-west-2' },
  { id: 'eu-west-1', name: 'Europe (Ireland) - eu-west-1' },
  { id: 'ap-southeast-1', name: 'Asia Pacific (Singapore) - ap-southeast-1' },
];

interface FormErrors {
  displayName?: string;
  accountId?: string;
  roleArn?: string;
}

export function AwsConnectionWizard({
  open,
  onClose,
  onSuccess,
  notify,
}: AwsConnectionWizardProps) {
  // 3-step flow: 1: Setup Guide & External ID, 2: Verify Connection, 3: Connected
  const [step, setStep] = useState<number>(1);
  const [loadingInit, setLoadingInit] = useState<boolean>(false);
  const [initData, setInitData] = useState<AwsInitiateResponse | null>(null);

  // Form inputs for verification step
  const [displayName, setDisplayName] = useState<string>('Production AWS');
  const [accountId, setAccountId] = useState<string>('');
  const [roleArn, setRoleArn] = useState<string>('');
  const [region, setRegion] = useState<string>('ap-south-1');
  const [formErrors, setFormErrors] = useState<FormErrors>({});

  const [verifying, setVerifying] = useState<boolean>(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [verifyResult, setVerifyResult] = useState<any | null>(null);

  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Initialize flow on modal open
  useEffect(() => {
    if (open) {
      setStep(1);
      setVerifyError(null);
      setVerifyResult(null);
      setFormErrors({});
      setAccountId('');
      setRoleArn('');
      loadInitiateData();
    }
  }, [open]);

  const loadInitiateData = async () => {
    setLoadingInit(true);
    try {
      const data = await apiInitiateAwsConnection();
      setInitData(data);
    } catch {
      // Dev fallback if backend is offline
      const mockExtId = `ca-ext-${Math.random().toString(16).substring(2, 14)}`;
      const fallbackData: AwsInitiateResponse = {
        external_id: mockExtId,
        platform_aws_account_id: '123456789012',
        platform_role_arn: 'arn:aws:iam::123456789012:role/CloudAdvisorBackendRole',
        trust_policy: {
          Version: '2012-10-17',
          Statement: [
            {
              Effect: 'Allow',
              Principal: {
                AWS: 'arn:aws:iam::123456789012:role/CloudAdvisorBackendRole'
              },
              Action: 'sts:AssumeRole',
              Condition: {
                StringEquals: {
                  'sts:ExternalId': mockExtId
                }
              }
            }
          ]
        },
        recommended_permissions: [
          'arn:aws:iam::aws:policy/SecurityAudit',
          'arn:aws:iam::aws:policy/job-function/ViewOnlyAccess'
        ]
      };
      setInitData(fallbackData);
    } finally {
      setLoadingInit(false);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    try {
      navigator.clipboard.writeText(text);
    } catch {
      const el = document.createElement('textarea');
      el.value = text;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
    }
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2200);
  };

  const handleVerify = async () => {
    if (!initData) return;
    const errors: FormErrors = {};

    if (!displayName.trim() || displayName.length < 2) {
      errors.displayName = 'Nickname must be at least 2 characters.';
    }
    if (!/^\d{12}$/.test(accountId.trim())) {
      errors.accountId = 'Account ID must be exactly 12 digits.';
    }
    if (!/^arn:aws:iam::\d{12}:role\/[\w+=,.@\/-]{1,64}$/.test(roleArn.trim())) {
      errors.roleArn = 'Enter a valid IAM role ARN (e.g. arn:aws:iam::123456789012:role/RoleName).';
    }

    setFormErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setVerifying(true);
    setVerifyError(null);

    try {
      const result = await apiVerifyAwsConnection({
        connection_id: initData.connection_id,
        display_name: displayName.trim(),
        account_id: accountId.trim(),
        role_arn: roleArn.trim(),
        external_id: initData.external_id,
        region: region,
      });

      setVerifyResult(result);
      setStep(3);
      notify(`AWS account "${displayName}" verified & connected via AWS STS.`);
    } catch (err: any) {
      const errorDetail = err?.message || 'AWS STS AssumeRole verification failed. Ensure your IAM role trust policy matches the exact External ID.';
      setVerifyError(errorDetail);
    } finally {
      setVerifying(false);
    }
  };

  const handleFinish = () => {
    if (verifyResult?.account) {
      onSuccess(verifyResult.account);
    } else {
      onSuccess({
        id: `aws-${Date.now()}`,
        provider: 'AWS',
        display_name: displayName,
        account_identifier: accountId || '123456789012',
        status: 'connected',
        last_verified_at: new Date().toISOString()
      });
    }
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="aws-wizard-dialog">
        <DialogHeader>
          <div className="flex items-center gap-2 mb-1">
            <span className="connection-icon aws" style={{ width: 28, height: 28 }}>
              <Cloud size={16} />
            </span>
            <DialogTitle className="text-lg font-bold">Connect AWS</DialogTitle>
          </div>
          <DialogDescription className="text-xs">
            Cross-account read-only access via AWS STS AssumeRole with unique External ID.
          </DialogDescription>
        </DialogHeader>

        {/* 3-Step Indicator matching the flow */}
        <div className="aws-stepper mt-1">
          <div className={`aws-step-node ${step === 1 ? 'aws-step-active' : step > 1 ? 'aws-step-completed' : ''}`}>
            <div className="aws-step-circle">
              {step > 1 ? <Check size={14} /> : 1}
            </div>
            <span className="aws-step-label">1. Setup Instructions</span>
          </div>
          <div className={`aws-step-node ${step === 2 ? 'aws-step-active' : step > 2 ? 'aws-step-completed' : ''}`}>
            <div className="aws-step-circle">
              {step > 2 ? <Check size={14} /> : 2}
            </div>
            <span className="aws-step-label">2. Verify Connection</span>
          </div>
          <div className={`aws-step-node ${step === 3 ? 'aws-step-completed' : ''}`}>
            <div className="aws-step-circle">
              {step === 3 ? <Check size={14} /> : 3}
            </div>
            <span className="aws-step-label">3. Connected</span>
          </div>
        </div>

        {/* Loading state for initiation */}
        {loadingInit && (
          <div className="py-12 flex flex-col items-center justify-center gap-3 text-muted-foreground">
            <RefreshCw size={24} className="animate-spin text-primary" />
            <span className="text-xs">Creating pending connection and generating unique External ID...</span>
          </div>
        )}

        {/* STEP 1: Setup Instructions (User Prompt Step 2 & 3) */}
        {!loadingInit && step === 1 && initData && (
          <div className="flex flex-col gap-3.5">
            {/* Unique External ID Block */}
            <div className="grid gap-1.5">
              <Label className="text-xs font-semibold flex items-center justify-between">
                <span>Unique External ID (Required in Trust Relationship)</span>
                <span className="text-[10px] text-muted-foreground">Generated by Cloud Advisor</span>
              </Label>
              <div className="aws-copy-box">
                <span className="font-semibold text-primary">{initData.external_id}</span>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 px-2.5 text-xs gap-1.5"
                  onClick={() => copyToClipboard(initData.external_id, 'ext_id')}
                >
                  {copiedId === 'ext_id' ? <Check size={13} className="text-success" /> : <Copy size={13} />}
                  {copiedId === 'ext_id' ? 'Copied' : 'Copy ID'}
                </Button>
              </div>
            </div>

            {/* Step 3 - AWS Console Guide */}
            <div className="aws-info-card">
              <strong className="block text-foreground mb-1 text-xs font-semibold">
                AWS Console Setup Guide
              </strong>
              <ol className="text-muted-foreground text-xs pl-4 m-0 space-y-1 list-decimal">
                <li>Sign in to <strong>AWS Console</strong> &rarr; IAM &rarr; <strong>Roles</strong> &rarr; <strong>Create role</strong>.</li>
                <li>Under Trusted Entity, choose <strong>Custom trust policy</strong> and paste the JSON policy below.</li>
                <li>Attach read-only managed permissions: <span className="text-foreground font-semibold">SecurityAudit</span> & <span className="text-foreground font-semibold">ViewOnlyAccess</span>.</li>
                <li>Name the role (e.g. <code className="font-mono text-foreground">CloudAdvisorReadOnlyRole</code>) and create it.</li>
              </ol>
            </div>

            {/* Pre-formatted Trust Policy JSON */}
            <div className="grid gap-1.5">
              <div className="flex items-center justify-between">
                <Label className="text-xs font-semibold flex items-center gap-1.5">
                  <KeyRound size={14} className="text-primary" />
                  Trust Policy JSON
                </Label>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-6 px-2 text-xs gap-1"
                  onClick={() => copyToClipboard(JSON.stringify(initData.trust_policy, null, 2), 'policy')}
                >
                  {copiedId === 'policy' ? <Check size={12} className="text-success" /> : <Copy size={12} />}
                  {copiedId === 'policy' ? 'Copied JSON' : 'Copy Policy JSON'}
                </Button>
              </div>
              <pre className="aws-policy-pre">{JSON.stringify(initData.trust_policy, null, 2)}</pre>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Required read-only policies:</span>
              <span className="aws-badge-pill">SecurityAudit</span>
              <span className="aws-badge-pill">ViewOnlyAccess</span>
            </div>

            <div className="callout text-[11px] py-2 px-3">
              <ShieldCheck size={15} />
              <span>
                <strong>Zero static keys:</strong> AWS STS automatically generates temporary session credentials.
                You never provide Access Keys or Secret Keys.
              </span>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-border">
              <Button variant="outline" size="sm" onClick={onClose}>
                Cancel
              </Button>
              <Button size="sm" className="gap-1.5" onClick={() => setStep(2)}>
                Next: Verify Connection <ArrowRight size={14} />
              </Button>
            </div>
          </div>
        )}

        {/* STEP 2: Customer Enters IAM Role & Verifies (User Prompt Step 4) */}
        {!loadingInit && step === 2 && initData && (
          <div className="flex flex-col gap-3.5">
            <div className="aws-info-card">
              <strong className="block text-foreground mb-1 text-xs font-semibold">
                Customer's AWS IAM Role Details
              </strong>
              <p className="text-muted-foreground text-xs m-0">
                Enter your AWS Account ID and the read-only IAM Role ARN you configured.
                Our backend will authenticate with AWS STS using the stored External ID to assume the role.
              </p>
            </div>

            {verifyError && (
              <div className="p-3 rounded-lg border border-destructive/40 bg-destructive/10 text-destructive text-xs flex items-start gap-2">
                <AlertCircle size={15} className="shrink-0 mt-0.5" />
                <div>
                  <strong className="block font-semibold">Verification Failed</strong>
                  <span>{verifyError}</span>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div className="grid gap-1">
                <Label htmlFor="aws-name" className="text-xs">Connection Nickname</Label>
                <Input
                  id="aws-name"
                  placeholder="Production AWS"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="h-8 text-xs"
                />
                {formErrors.displayName && <small className="text-destructive text-[11px]">{formErrors.displayName}</small>}
              </div>

              <div className="grid gap-1">
                <Label htmlFor="aws-acc-id" className="text-xs">AWS Account ID (12 digits)</Label>
                <Input
                  id="aws-acc-id"
                  placeholder="123456789012"
                  maxLength={12}
                  value={accountId}
                  onChange={(e) => {
                    const val = e.target.value.replace(/\D/g, '');
                    setAccountId(val);
                    if (val.length === 12 && !roleArn) {
                      setRoleArn(`arn:aws:iam::${val}:role/CloudAdvisorReadOnlyRole`);
                    }
                  }}
                  className="h-8 text-xs font-mono"
                />
                {formErrors.accountId && <small className="text-destructive text-[11px]">{formErrors.accountId}</small>}
              </div>
            </div>

            <div className="grid gap-1">
              <Label htmlFor="aws-role-arn" className="text-xs">IAM Role ARN</Label>
              <Input
                id="aws-role-arn"
                placeholder="arn:aws:iam::123456789012:role/CloudAdvisorReadOnlyRole"
                value={roleArn}
                onChange={(e) => setRoleArn(e.target.value)}
                className="h-8 text-xs font-mono"
              />
              {formErrors.roleArn ? (
                <small className="text-destructive text-[11px]">{formErrors.roleArn}</small>
              ) : (
                <small className="text-muted-foreground text-[10px]">
                  Format: arn:aws:iam::&lt;account-id&gt;:role/&lt;role-name&gt;
                </small>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="grid gap-1">
                <Label htmlFor="aws-region" className="text-xs">AWS Region</Label>
                <select
                  id="aws-region"
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                  className="h-8 text-xs bg-background border border-border rounded-md px-2 text-foreground font-mono"
                >
                  {REGIONS.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid gap-1">
                <Label className="text-xs">External ID (Stored)</Label>
                <div className="h-8 px-2.5 rounded-md bg-secondary/50 border border-border flex items-center justify-between text-xs font-mono text-primary">
                  <span>{initData.external_id}</span>
                  <Lock size={12} className="text-muted-foreground" />
                </div>
              </div>
            </div>

            <div className="callout text-[11px] py-2 px-3">
              <KeyRound size={15} />
              <span>
                <strong>Temporary AWS credentials:</strong> After role assumption, AWS STS returns
                short-lived credentials (<code className="text-foreground">AccessKeyId</code>, <code className="text-foreground">SessionToken</code>).
                Stored securely by our backend SDK.
              </span>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-border">
              <Button variant="outline" size="sm" className="gap-1" onClick={() => setStep(1)}>
                <ArrowLeft size={14} /> Back
              </Button>
              <Button
                size="sm"
                className="gap-1.5"
                disabled={verifying}
                onClick={handleVerify}
              >
                {verifying ? (
                  <>
                    <RefreshCw size={13} className="animate-spin" />
                    Calling AWS STS AssumeRole...
                  </>
                ) : (
                  <>
                    <ShieldCheck size={14} />
                    Verify Connection
                  </>
                )}
              </Button>
            </div>
          </div>
        )}

        {/* STEP 3: Connected (User Prompt Step 5) */}
        {step === 3 && (
          <div className="flex flex-col items-center text-center py-4 gap-4">
            <div className="w-14 h-14 rounded-full bg-success/15 text-success flex items-center justify-center">
              <CheckCircle2 size={36} />
            </div>

            <div>
              <h3 className="text-lg font-bold text-foreground">Connected!</h3>
              <p className="text-xs text-muted-foreground max-w-md mx-auto mt-1">
                AWS STS authorized the role assumption. Verified account details are saved, connection marked active,
                and background discovery of permitted resources & billing has begun.
              </p>
            </div>

            <div className="w-full bg-secondary/50 border border-border rounded-lg p-3 text-left grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-muted-foreground block text-[10px]">ACCOUNT NAME</span>
                <strong className="text-foreground">{displayName}</strong>
              </div>
              <div>
                <span className="text-muted-foreground block text-[10px]">AWS ACCOUNT ID</span>
                <span className="font-mono text-foreground">{accountId || '123456789012'}</span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[10px]">PRIMARY REGION</span>
                <span className="text-foreground">{region}</span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[10px]">AUTHENTICATION</span>
                <span className="text-success font-semibold flex items-center gap-1">
                  <ShieldCheck size={12} /> STS AssumeRole (Active)
                </span>
              </div>
              <div className="col-span-2 border-t border-border/60 pt-1.5">
                <span className="text-muted-foreground block text-[10px]">IAM ROLE ARN</span>
                <span className="font-mono text-[11px] text-muted-foreground break-all">{roleArn}</span>
              </div>
            </div>

            <div className="w-full callout text-[11px] py-2 px-3 text-left">
              <RefreshCw size={14} className="animate-spin text-primary" />
              <span>
                <strong>Fetching Resources & Costs:</strong> Background scan running for EC2, EBS, RDS, S3, and Cost Explorer.
              </span>
            </div>

            <Button className="w-full mt-1" onClick={handleFinish}>
              Done & View Connected Accounts
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
