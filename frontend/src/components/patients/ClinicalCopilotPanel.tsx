"use client";

import { useCallback, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ApiClientError } from "@/lib/api/client";
import {
  evaluateClinicalCopilot,
  type ClinicalCopilotEvaluationResponse,
} from "@/lib/api/clinical-copilot";
import type { EncounterStatus } from "@/lib/api/clinical-encounters";

export type ClinicalCopilotPanelLabels = {
  title: string;
  disclaimer: string;
  idleHint: string;
  evaluateButton: string;
  evaluatePending: string;
  noActiveRulesMessage: string;
  errorMessage: string;
  readOnlyHint: string;
};

type PanelState = "idle" | "loading" | "completed" | "error";

type Props = {
  patientId: string;
  encounterId: string;
  encounterStatus: EncounterStatus;
  accessToken: string;
  labels: ClinicalCopilotPanelLabels;
  onUnauthorized: () => void;
};

export function ClinicalCopilotPanel({
  patientId,
  encounterId,
  encounterStatus,
  accessToken,
  labels,
  onUnauthorized,
}: Props) {
  const [panelState, setPanelState] = useState<PanelState>("idle");
  const [result, setResult] = useState<ClinicalCopilotEvaluationResponse | null>(null);
  const [errorText, setErrorText] = useState<string | null>(null);
  const inFlightRef = useRef(false);

  const isFinalized = encounterStatus === "finalized";
  const canEvaluate = encounterStatus === "active" || isFinalized;

  const runEvaluate = useCallback(async () => {
    if (!canEvaluate || inFlightRef.current) {
      return;
    }
    inFlightRef.current = true;
    setPanelState("loading");
    setErrorText(null);

    try {
      const data = await evaluateClinicalCopilot(accessToken, patientId, encounterId);
      setResult(data);
      setPanelState("completed");
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 401) {
        onUnauthorized();
        return;
      }
      setPanelState("error");
      setErrorText(labels.errorMessage);
    } finally {
      inFlightRef.current = false;
    }
  }, [
    accessToken,
    canEvaluate,
    encounterId,
    labels.errorMessage,
    onUnauthorized,
    patientId,
  ]);

  return (
    <aside
      aria-labelledby="clinical-copilot-heading"
      className="rounded-xl border border-border bg-white p-5 shadow-sm lg:sticky lg:top-6"
    >
      <h2 id="clinical-copilot-heading" className="text-lg font-semibold text-text-primary">
        {labels.title}
      </h2>
      <p className="mt-2 text-sm text-text-secondary">{labels.disclaimer}</p>

      {isFinalized ? (
        <p className="mt-3 text-xs text-text-secondary" role="status">
          {labels.readOnlyHint}
        </p>
      ) : null}

      {canEvaluate ? (
        <div className="mt-4">
          <Button
            type="button"
            variant="secondary"
            disabled={panelState === "loading" || !canEvaluate}
            onClick={() => void runEvaluate()}
          >
            {panelState === "loading" ? labels.evaluatePending : labels.evaluateButton}
          </Button>
        </div>
      ) : null}

      <div className="mt-4 space-y-2 text-sm" role="status">
        {panelState === "idle" && canEvaluate ? (
          <p className="text-text-secondary">{labels.idleHint}</p>
        ) : null}
        {panelState === "loading" ? (
          <p className="text-text-secondary">{labels.evaluatePending}</p>
        ) : null}
        {panelState === "completed" && result ? (
          <p className="rounded-lg border border-border bg-slate-50 px-3 py-2 text-text-secondary">
            {labels.noActiveRulesMessage}
          </p>
        ) : null}
        {panelState === "error" && errorText ? (
          <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-red-900">{errorText}</p>
        ) : null}
      </div>
    </aside>
  );
}
