import { providerMeta as baseMeta, services as baseServices, unused as baseUnused, resources as baseResources, recommendations as baseRecs, trend as baseTrend, type Cloud, type Finding, type Resource, type Recommendation, type Service } from './cloud';

export type ScenarioId = 'bank_balanced' | 'retail_balanced' | 'retail_2900' | 'production';
export type Scenario = {
  id: ScenarioId;
  name: string;
  domain?: string;
  tagline: string;
  synthetic: boolean;
  item_count?: number;
};

export const scenarios: Scenario[] = [
  {
    id: 'bank_balanced',
    name: 'Global Bank Multi-Cloud',
    domain: 'Banking & FinTech',
    tagline: '10,000 Balanced Assets across AWS, Azure, GCP',
    synthetic: true,
    item_count: 10000
  },
  {
    id: 'retail_balanced',
    name: 'Enterprise Retail Fleet',
    domain: 'Retail & E-Commerce',
    tagline: '10,000 Balanced Assets across AWS, Azure, GCP',
    synthetic: true,
    item_count: 10000
  },
  {
    id: 'retail_2900',
    name: 'Mid-Market Retail Fleet',
    domain: 'Retail Operations',
    tagline: '2,900 Multi-Cloud Assets across AWS, Azure, GCP',
    synthetic: true,
    item_count: 2900
  },
  {
    id: 'production',
    name: 'Production Infrastructure',
    tagline: '2,900 Multi-Cloud Assets across AWS, Azure, GCP',
    synthetic: false,
    item_count: 2900
  }
];

export type Dataset = ReturnType<typeof buildDataset>;

export function buildDataset(id?: ScenarioId) {
  const sc = scenarios.find(s => s.id === id) || scenarios[0]!;
  return {
    scenario: sc,
    providerMeta: baseMeta,
    services: baseServices,
    trend: baseTrend,
    unused: baseUnused,
    resources: baseResources,
    recommendations: baseRecs
  };
}
