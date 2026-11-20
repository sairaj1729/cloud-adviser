import { createFileRoute } from '@tanstack/react-router';
import { AppShell } from '@/components/cloud/AppShell';
import { AiRecommendationsView } from '@/components/cloud/Views';

export const Route = createFileRoute('/ai-recommendations')({
  head: () => ({
    meta: [
      { title: 'AI Recommendations | Cloud Advisor' },
      { name: 'description', content: 'Autonomous multi-cloud fleet rightsizing, hardware SKU optimization, and automated CLI runbooks.' },
      { property: 'og:title', content: 'AI Recommendations | Cloud Advisor' },
      { property: 'og:description', content: 'Autonomous multi-cloud fleet rightsizing, hardware SKU optimization, and automated CLI runbooks.' },
      { property: 'og:type', content: 'website' },
      { name: 'twitter:card', content: 'summary_large_image' }
    ]
  }),
  component: () => (
    <AppShell>
      <AiRecommendationsView />
    </AppShell>
  )
});
