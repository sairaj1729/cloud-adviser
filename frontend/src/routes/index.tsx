import { createFileRoute } from '@tanstack/react-router';
import { AppShell } from '@/components/cloud/AppShell';
import { CostView } from '@/components/cloud/Views';
export const Route = createFileRoute('/')({ head:()=>({meta:[{title:'Dashboard | Cloud Advisor'},{name:'description',content:'Monitor multi-cloud spending and identify cost optimization opportunities with Cloud Advisor.'},{property:'og:title',content:'Cloud Advisor Dashboard'},{property:'og:description',content:'Understand cloud spend and uncover actionable savings across AWS, Azure, and GCP.'},{property:'og:type',content:'website'},{name:'twitter:card',content:'summary_large_image'}]}),component:()=> <AppShell><CostView dashboard/></AppShell> });
