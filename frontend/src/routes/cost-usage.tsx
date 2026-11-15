import { createFileRoute } from '@tanstack/react-router';
import { AppShell } from '@/components/cloud/AppShell';
import { CostView } from '@/components/cloud/Views';
export const Route = createFileRoute('/cost-usage')({ head:()=>({meta:[{title:'Cost Usage | Cloud Advisor'},{name:'description',content:'Explore cloud cost trends, service breakdowns, and spending patterns.'},{property:'og:title',content:'Cost Usage | Cloud Advisor'},{property:'og:description',content:'Explore cloud cost trends and service spending across AWS, Azure, and GCP.'},{property:'og:type',content:'website'},{name:'twitter:card',content:'summary_large_image'}]}),component:()=> <AppShell><CostView/></AppShell> });
