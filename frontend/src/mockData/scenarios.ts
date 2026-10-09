import { providerMeta as baseMeta, services as baseServices, unused as baseUnused, resources as baseResources, recommendations as baseRecs, trend as baseTrend, type Cloud, type Finding, type Resource, type Recommendation, type Service } from './cloud';

export type ScenarioId = 'production';
export type Scenario = {
  id: ScenarioId;
  name: string;
  tagline: string;
  synthetic: boolean;
};

export const scenarios: Scenario[] = [
  {
    id: 'production',
    name: 'Production Infrastructure',
    tagline: '2,900 Multi-Cloud Resources (data.json)',
    synthetic: false
  }
];

export type Dataset = ReturnType<typeof buildDataset>;

export function buildDataset(_id?: ScenarioId) {
  return {
    scenario: scenarios[0]!,
    providerMeta: baseMeta,
    services: baseServices,
    trend: baseTrend,
    unused: baseUnused,
    resources: baseResources,
    recommendations: baseRecs
  };
}
