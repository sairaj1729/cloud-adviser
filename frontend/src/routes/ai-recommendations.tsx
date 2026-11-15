import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/cloud/AppShell";
import { AIRecommendationsView } from "@/components/cloud/AIRecommendations";

export const Route = createFileRoute("/ai-recommendations")({
  head: () => ({
    meta: [
      { title: "AI Recommendations | Cloud Advisor" },
      {
        name: "description",
        content: "Generate structured cloud optimization recommendations from resource context.",
      },
    ],
  }),
  component: () => (
    <AppShell>
      <AIRecommendationsView />
    </AppShell>
  ),
});
