import { useMemo, useState } from "react";
import { AlertCircle, ArrowDownRight, ArrowUpRight, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ProviderBadge, useDataset } from "./AppShell";
import { apiGetAiRecommendations, getStoredToken } from "@/config/api";
import { money, type Recommendation } from "@/mockData/cloud";
import "./AIRecommendations.css";

type RecommendationCandidate = {
  id: string;
  provider: Recommendation["provider"];
  resource_id: string;
  resource_name: string;
  title: string;
  problem: string;
  evidence: string;
  savings: number;
  priority: string;
  confidence: number;
  action: string;
  current_monthly_cost: number;
};

type AiRecommendation = RecommendationCandidate & { reason: string };
type AiSource = "claude" | "gemini" | "openrouter" | "groq" | "rule_engine";

const priorityOrder: Record<string, number> = { High: 0, Medium: 1, Low: 2 };
const sourceNames: Record<AiSource, string> = {
  claude: "Claude",
  gemini: "Google Gemini",
  openrouter: "OpenRouter",
  groq: "Groq",
  rule_engine: "Rule Engine",
};

function getRuleEngineRecommendations(candidates: RecommendationCandidate[]): AiRecommendation[] {
  return [...candidates]
    .sort(
      (a, b) =>
        (priorityOrder[a.priority] ?? 3) - (priorityOrder[b.priority] ?? 3) ||
        b.confidence - a.confidence ||
        b.savings - a.savings,
    )
    .slice(0, 8)
    .map((candidate) => ({
      ...candidate,
      reason: `The rule engine flagged ${candidate.problem.replace(/[.]+$/, "")}. Evidence: ${candidate.evidence.replace(/[.]+$/, "")}.`,
    }));
}

export function AIRecommendationsView() {
  const { recommendations, resources } = useDataset();
  const [results, setResults] = useState<AiRecommendation[]>([]);
  const [model, setModel] = useState("");
  const [source, setSource] = useState<AiSource>("claude");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [fallbackNotice, setFallbackNotice] = useState("");

  const candidates = useMemo(
    () =>
      [...recommendations]
        .sort(
          (a, b) =>
            (priorityOrder[a.priority] ?? 3) - (priorityOrder[b.priority] ?? 3) ||
            b.savings - a.savings,
        )
        .slice(0, 30)
        .map((recommendation: Recommendation) => {
          const resource = resources.find((item) => item.name === recommendation.resource);
          return {
            id: recommendation.id,
            provider: recommendation.provider,
            resource_id: resource?.id ?? recommendation.resource,
            resource_name: recommendation.resource,
            title: recommendation.title,
            problem: recommendation.problem,
            evidence: recommendation.evidence,
            savings: recommendation.savings,
            priority: recommendation.priority,
            confidence: recommendation.confidence,
            action: recommendation.action,
            current_monthly_cost: resource?.cost ?? recommendation.cost,
          };
        }),
    [recommendations, resources],
  );

  async function getRecommendations() {
    setError("");
    setFallbackNotice("");
    setResults([]);
    if (candidates.length === 0) {
      setError("There are no cloud recommendations available to analyze.");
      return;
    }

    if (!getStoredToken()) {
      setResults(getRuleEngineRecommendations(candidates));
      setModel("Rule Engine");
      setSource("rule_engine");
      setFallbackNotice(
        "Sign-in is required for cloud AI providers; showing local rule-engine recommendations instead.",
      );
      return;
    }

    setIsLoading(true);
    try {
      const response = await apiGetAiRecommendations(candidates);
      setResults(response.recommendations);
      setModel(response.model);
      setSource(response.source);
      if (response.source !== "claude") {
        setFallbackNotice(`Using ${sourceNames[response.source]} recommendations.`);
      }
    } catch (requestError) {
      console.warn("AI recommendations request failed; using rule-engine results:", requestError);
      setResults(getRuleEngineRecommendations(candidates));
      setModel("Rule Engine");
      setSource("rule_engine");
      setFallbackNotice(
        "AI providers could not be reached; showing recommendations from the rule engine instead.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="view-stack ai-recommendations-view">
      <section className="ai-hero surface">
        <div className="ai-hero-copy">
          <span className="ai-section-kicker">
            <Sparkles size={14} /> AI-POWERED CLOUD ADVISOR
          </span>
          <h2>Find your next cloud savings</h2>
          <p>
            Configured AI providers review your resource evidence, rank optimization opportunities,
            and explain why each one is worth a closer look.
          </p>
          <Button
            type="button"
            className="ai-get-recommendations"
            onClick={getRecommendations}
            disabled={isLoading || candidates.length === 0}
          >
            <Sparkles size={16} />
            {isLoading ? "Analyzing your cloud data..." : "Get recommendations"}
          </Button>
          <span className="ai-privacy-note">
            Resource metrics and cost context are sent to configured AI providers for analysis.
          </span>
        </div>
        <div className="ai-hero-art" aria-hidden="true">
          <span>
            <Sparkles size={30} />
          </span>
          <i className="ai-orbit ai-orbit-one" />
          <i className="ai-orbit ai-orbit-two" />
          <i className="ai-orbit ai-orbit-three" />
        </div>
      </section>

      {error && (
        <div className="ai-request-error" role="alert">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {fallbackNotice && (
        <div className="ai-fallback-notice" role="status">
          <AlertCircle size={16} />
          <span>{fallbackNotice}</span>
        </div>
      )}

      {isLoading && (
        <div className="ai-loading-state" role="status">
          <span className="ai-loading-spinner" />
          AI providers are reviewing {candidates.length} evidence-backed opportunities...
        </div>
      )}

      {results.length > 0 && (
        <section className="ai-results" aria-live="polite">
          <div className="ai-results-heading">
            <div>
              <span className="ai-section-kicker">AI-PRIORITIZED OPPORTUNITIES</span>
              <h2>Your recommendations</h2>
              <p>
                {source === "rule_engine"
                  ? "Ranked and explained using the cloud rule engine and its resource evidence."
                  : `Each reason is generated by ${sourceNames[source]} from the resource evidence below.`}
              </p>
            </div>
            <span className={`ai-model-badge ${source === "rule_engine" ? "is-fallback" : ""}`}>
              <Sparkles size={13} /> {model}
            </span>
          </div>

          <div className="ai-result-list">
            {results.map((recommendation, index) => (
              <article className="ai-result-card surface" key={recommendation.id}>
                <div className="ai-result-rank">{String(index + 1).padStart(2, "0")}</div>
                <div className="ai-result-content">
                  <div className="ai-result-topline">
                    <ProviderBadge provider={recommendation.provider} />
                    <span
                      className={`priority-pill priority-${recommendation.priority.toLowerCase()}`}
                    >
                      {recommendation.priority} priority
                    </span>
                    <span className="ai-confidence">{recommendation.confidence}% confidence</span>
                  </div>
                  <h3>{recommendation.title}</h3>
                  <p className="ai-result-resource">{recommendation.resource_name}</p>
                  <div className="ai-reason">
                    <span className="ai-reason-label">
                      <Sparkles size={13} />
                      {source === "rule_engine"
                        ? "RULE ENGINE REASON"
                        : `WHY ${sourceNames[source].toUpperCase()} RECOMMENDS THIS`}
                    </span>
                    <p>{recommendation.reason}</p>
                  </div>
                  <div className="ai-result-evidence">
                    <strong>Evidence</strong>
                    <span>{recommendation.evidence}</span>
                  </div>
                  <div className="ai-result-action">
                    <strong>Suggested action</strong>
                    <span>{recommendation.action}</span>
                  </div>
                </div>
                <div className="ai-result-savings">
                  {recommendation.savings > 0 ? (
                    <ArrowDownRight size={16} />
                  ) : (
                    <ArrowUpRight size={16} />
                  )}
                  <small>ESTIMATED SAVINGS</small>
                  <strong>
                    {money(recommendation.savings)}
                    <span>/mo</span>
                  </strong>
                  <small>Current {money(recommendation.current_monthly_cost)}/mo</small>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
