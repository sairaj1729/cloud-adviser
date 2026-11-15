import { createFileRoute } from '@tanstack/react-router';
import { AppShell } from '@/components/cloud/AppShell';
import { UtilizationView } from '@/components/cloud/Views';
export const Route = createFileRoute('/low-utilization')({ head:()=>({meta:[{title:'Low Utilization | Cloud Advisor'},{name:'description',content:'Discover underutilized cloud resources and estimated savings.'},{property:'og:title',content:'Low Utilization | Cloud Advisor'},{property:'og:description',content:'Discover underutilized cloud resources and opportunities to right-size capacity.'},{property:'og:type',content:'website'},{name:'twitter:card',content:'summary_large_image'}]}),component:()=> <AppShell><UtilizationView/></AppShell> });
