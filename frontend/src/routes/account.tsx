import { createFileRoute } from '@tanstack/react-router';
import { AppShell } from '@/components/cloud/AppShell';
import { AccountView } from '@/components/cloud/Views';
export const Route = createFileRoute('/account')({ head:()=>({meta:[{title:'Account | Cloud Advisor'},{name:'description',content:'View your Cloud Advisor profile, preferences, and cloud connection status.'},{property:'og:title',content:'Account | Cloud Advisor'},{property:'og:description',content:'Manage Cloud Advisor preferences and view cloud connection status.'},{property:'og:type',content:'website'},{name:'twitter:card',content:'summary_large_image'}]}),component:()=> <AppShell><AccountView/></AppShell> });
