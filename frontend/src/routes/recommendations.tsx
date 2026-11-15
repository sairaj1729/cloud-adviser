import { createFileRoute } from '@tanstack/react-router';
import { AppShell } from '@/components/cloud/AppShell';
import { RecommendationsView } from '@/components/cloud/Views';
export const Route = createFileRoute('/recommendations')({ head:()=>({meta:[{title:'Recommendations | Cloud Advisor'},{name:'description',content:'Prioritized, evidence-backed cloud cost optimization recommendations.'},{property:'og:title',content:'Recommendations | Cloud Advisor'},{property:'og:description',content:'Take action on evidence-backed recommendations to reduce cloud spending.'},{property:'og:type',content:'website'},{name:'twitter:card',content:'summary_large_image'}]}),component:()=> <AppShell><RecommendationsView/></AppShell> });
