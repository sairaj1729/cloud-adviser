export type Cloud = 'AWS' | 'Azure' | 'GCP';
export type Period = 'Daily' | 'Monthly' | 'Custom';
export const providers: Cloud[] = ['AWS', 'Azure', 'GCP'];
export const providerMeta = {
  AWS: { name: 'Amazon Web Services', short: 'AWS', color: 'var(--aws)', total: 42875, average: 39420, serviceCount: 38, change: 8.2 },
  Azure: { name: 'Microsoft Azure', short: 'Azure', color: 'var(--azure)', total: 31482, average: 29750, serviceCount: 29, change: 5.8 },
  GCP: { name: 'Google Cloud Platform', short: 'GCP', color: 'var(--gcp)', total: 18634, average: 17240, serviceCount: 22, change: -2.4 },
};
export const money = (n: number) => '$' + n.toLocaleString('en-US', { maximumFractionDigits: 0 });
export const trend = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].map((month, i) => ({ month, AWS: ([29,31,30,33,35,34,37,36,39,38,41,42.9][i] ?? 0) * 1000, Azure: ([22,23,24,23,26,25,27,28,27,29,30,31.5][i] ?? 0) * 1000, GCP: ([12,13,13,14,15,14,16,16,17,17,18,18.6][i] ?? 0) * 1000 }));
export type Service = { name: string; cost: number; change: number; trend: number[] };
export const services: Record<Cloud, Service[]> = {
  AWS: [
    {name:'Amazon EC2',cost:18420,change:12.4,trend:[4,5,4,6,5,7,6,8]}, {name:'Amazon RDS',cost:9840,change:6.8,trend:[3,4,3,4,5,5,6,6]}, {name:'Amazon S3',cost:5260,change:-3.2,trend:[6,6,5,5,4,5,4,4]}, {name:'AWS Lambda',cost:3540,change:9.1,trend:[2,3,3,4,3,5,4,6]}, {name:'CloudFront',cost:2480,change:2.6,trend:[3,3,4,3,4,4,4,5]}, {name:'ElastiCache',cost:1820,change:-1.8,trend:[5,5,4,4,5,4,4,3]}, {name:'Amazon ECS',cost:1515,change:4.2,trend:[2,2,3,3,3,4,4,4]}],
  Azure: [
    {name:'Virtual Machines',cost:12860,change:7.4,trend:[3,4,4,5,5,6,6,7]}, {name:'Azure SQL Database',cost:7410,change:4.1,trend:[3,3,4,4,4,5,5,5]}, {name:'Blob Storage',cost:4260,change:-2.8,trend:[5,5,5,4,4,4,3,3]}, {name:'App Service',cost:3120,change:8.3,trend:[2,3,3,3,4,4,5,5]}, {name:'Azure Kubernetes',cost:2140,change:3.7,trend:[2,3,2,4,3,4,4,5]}, {name:'Azure Functions',cost:1692,change:-1.2,trend:[4,4,4,3,4,3,3,3]}],
  GCP: [
    {name:'Compute Engine',cost:7690,change:3.4,trend:[2,3,3,4,4,4,5,5]}, {name:'BigQuery',cost:4320,change:-5.6,trend:[6,6,5,5,5,4,4,3]}, {name:'Cloud Storage',cost:2680,change:2.1,trend:[2,3,3,3,4,4,4,5]}, {name:'Cloud SQL',cost:1840,change:-1.9,trend:[5,5,5,4,4,4,3,3]}, {name:'GKE',cost:1290,change:6.7,trend:[2,2,3,3,4,4,5,5]}, {name:'Cloud Run',cost:814,change:4.2,trend:[2,3,3,4,3,4,5,5]}]
};
export type Finding = { id: string; name: string; provider: Cloud; service: string; cost: number; lastActivity: string; status: string; evidence: string; action: string; history: number[] };
export const unused: Finding[] = [
  {id:'u1',name:'staging-db-replica',provider:'AWS',service:'Amazon RDS',cost:284,lastActivity:'32 days ago',status:'Potentially Unused',evidence:'No read queries recorded in the past 30 days. Replication is still active.',action:'Confirm with the database owner before removing this replica.',history:[310,306,301,294,289,284]},
  {id:'u2',name:'legacy-assets-bucket',provider:'AWS',service:'Amazon S3',cost:96,lastActivity:'21 days ago',status:'Low Activity Detected',evidence:'No GET requests in the last 21 days; storage volume remains unchanged.',action:'Check retention requirements and application references before archiving.',history:[98,97,98,97,96,96]},
  {id:'u3',name:'dev-test-vm-04',provider:'Azure',service:'Virtual Machines',cost:173,lastActivity:'18 days ago',status:'Review Recommended',evidence:'No interactive sign-ins and near-zero network traffic for 18 days.',action:'Confirm the VM is not scheduled for an upcoming test cycle.',history:[172,173,173,173,173,173]},
  {id:'u4',name:'analytics-snapshot-2024',provider:'GCP',service:'Cloud Storage',cost:64,lastActivity:'45 days ago',status:'Potentially Unused',evidence:'No object reads in 45 days. Data may be subject to retention policy.',action:'Verify retention policy before moving to archival storage.',history:[68,67,66,65,64,64]},
  {id:'u5',name:'preview-cache-cluster',provider:'Azure',service:'Azure Cache',cost:212,lastActivity:'11 days ago',status:'Low Activity Detected',evidence:'Request volume declined by 94% over the past month.',action:'Ask the application team whether this environment is still required.',history:[217,216,215,214,213,212]},
  {id:'u6',name:'temp-processing-node',provider:'GCP',service:'Compute Engine',cost:138,lastActivity:'27 days ago',status:'Review Recommended',evidence:'No jobs scheduled and minimal outbound traffic in 27 days.',action:'Validate job schedules before stopping the instance.',history:[141,140,140,139,138,138]},
];
export type Resource = { id:string; name:string; provider:Cloud; service:string; cpu:number; memory:number; cost:number; savings:number; recommendation:string };
export const resources: Resource[] = [
  {id:'r1',name:'prod-api-worker-03',provider:'AWS',service:'EC2 · m5.2xlarge',cpu:4.8,memory:11.3,cost:112,savings:67,recommendation:'Right-size instance'},
  {id:'r2',name:'analytics-node-01',provider:'Azure',service:'VM · D8s v5',cpu:12.4,memory:23.1,cost:386,savings:174,recommendation:'Move to smaller SKU'},
  {id:'r3',name:'batch-processor-eu',provider:'GCP',service:'Compute Engine',cpu:8.2,memory:18.6,cost:294,savings:132,recommendation:'Right-size machine'},
  {id:'r4',name:'staging-web-02',provider:'AWS',service:'EC2 · t3.xlarge',cpu:6.1,memory:14.2,cost:154,savings:72,recommendation:'Downsize instance'},
  {id:'r5',name:'reporting-db-read',provider:'Azure',service:'Azure SQL',cpu:19.3,memory:28.4,cost:428,savings:118,recommendation:'Reduce provisioned capacity'},
  {id:'r6',name:'search-index-node',provider:'GCP',service:'GKE · n2-standard-8',cpu:14.7,memory:21.5,cost:241,savings:94,recommendation:'Adjust node pool'},
];
export type Recommendation = { id:string; title:string; provider:Cloud; resource:string; problem:string; evidence:string; savings:number; priority:'High'|'Medium'|'Low'; confidence:number; action:string; cost:number };
export const recommendations: Recommendation[] = [
  {id:'rec1',title:'Right-size EC2 instance',provider:'AWS',resource:'prod-api-worker-03',problem:'Instance capacity exceeds observed demand.',evidence:'CPU 4.8% · Memory 11.3% over the last 30 days',savings:67,priority:'High',confidence:96,action:'Move from m5.2xlarge to m5.xlarge after validating peak traffic.',cost:112},
  {id:'rec2',title:'Resize Azure virtual machine',provider:'Azure',resource:'analytics-node-01',problem:'Compute capacity is consistently underused.',evidence:'CPU 12.4% · Memory 23.1% over the last 30 days',savings:174,priority:'High',confidence:92,action:'Evaluate D4s v5 and test analytics jobs during peak windows.',cost:386},
  {id:'rec3',title:'Adjust GCP machine type',provider:'GCP',resource:'batch-processor-eu',problem:'Batch compute has significant idle capacity.',evidence:'CPU 8.2% · Memory 18.6% over the last 30 days',savings:132,priority:'High',confidence:89,action:'Test a smaller machine type against batch completion targets.',cost:294},
  {id:'rec4',title:'Review inactive RDS replica',provider:'AWS',resource:'staging-db-replica',problem:'No observed read traffic on the replica.',evidence:'No read queries in 30 days · Last activity 32 days ago',savings:284,priority:'Medium',confidence:82,action:'Confirm with the database owner before removing replication.',cost:284},
  {id:'rec5',title:'Optimize Azure SQL capacity',provider:'Azure',resource:'reporting-db-read',problem:'Provisioned database capacity exceeds demand.',evidence:'CPU 19.3% · Memory 28.4% over the last 30 days',savings:118,priority:'Medium',confidence:86,action:'Review a lower service tier and verify query performance.',cost:428},
  {id:'rec6',title:'Archive older cloud storage',provider:'GCP',resource:'analytics-snapshot-2024',problem:'Stored objects have not been accessed recently.',evidence:'No reads in 45 days · Retention policy needs verification',savings:41,priority:'Low',confidence:73,action:'Confirm retention needs and move eligible objects to archive tier.',cost:64},
];
