import { createFileRoute } from '@tanstack/react-router';
import { AppShell } from '@/components/cloud/AppShell';
import { UnusedView } from '@/components/cloud/Views';
export const Route = createFileRoute('/unused-services')({ head:()=>({meta:[{title:'Unused Services | Cloud Advisor'},{name:'description',content:'Review potentially unused cloud services using activity-based evidence.'},{property:'og:title',content:'Unused Services | Cloud Advisor'},{property:'og:description',content:'Review potentially unused cloud services and the evidence behind each signal.'},{property:'og:type',content:'website'},{name:'twitter:card',content:'summary_large_image'}]}),component:()=> <AppShell><UnusedView/></AppShell> });
