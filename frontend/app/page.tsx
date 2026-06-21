"use client";

import { useState } from "react";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { PreferenceForm } from "@/components/PreferenceForm";
import { ResultsPanel } from "@/components/ResultsPanel";
import type { RecommendationResponse } from "@/lib/types";

export default function HomePage() {
  const [results, setResults] = useState<RecommendationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  return (
    <>
      <Header />

      {serverError && (
        <div
          role="alert"
          className="flex items-center justify-between gap-4 border-b border-error/20 bg-error-container px-8 py-3 text-sm text-on-error-container"
        >
          <span className="flex-1 text-center">{serverError}</span>
          <button
            type="button"
            onClick={() => setServerError(null)}
            className="shrink-0 rounded px-2 py-1 text-xs font-semibold hover:bg-error/10"
            aria-label="Dismiss error"
          >
            Dismiss
          </button>
        </div>
      )}

      <main className="mx-auto w-full max-w-[1200px] flex-1 px-8 py-10">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-[2fr_3fr] lg:gap-10">
          <section aria-label="Your preferences">
            <PreferenceForm
              onResults={setResults}
              onLoadingChange={setIsLoading}
              onSubmitted={() => setHasSubmitted(true)}
              onServerError={setServerError}
            />
          </section>

          <section
            aria-label="Recommendations"
            className="lg:border-l lg:border-outline-variant/30 lg:pl-10"
          >
            <h2 className="mb-6 text-xl font-semibold text-on-surface">
              Recommendations
            </h2>
            <ResultsPanel
              data={results}
              isLoading={isLoading}
              hasSubmitted={hasSubmitted}
            />
          </section>
        </div>
      </main>

      <Footer />
    </>
  );
}
