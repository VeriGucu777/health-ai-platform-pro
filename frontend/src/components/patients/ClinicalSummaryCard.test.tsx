import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { ClinicalSummaryCard } from "@/components/patients/ClinicalSummaryCard";

const baseProps = {
  locale: "tr" as const,
  title: "Klinik özet",
  subtitle: "Son dönem klinik görünüm",
  description: "Mevcut kayıtların kısa karar destek özeti.",
  emptyMessage: "Özet oluşturmak için yeterli klinik veri bulunmuyor.",
  disclaimer: "Bu özet klinik karar destek amaçlıdır; tanı veya tedavi önerisi değildir.",
  itemLabels: { laboratory_summary: "Laboratuvar" },
  trendMessages: {},
  itemMessages: {
    lipid_panel_with_triglycerides:
      "Lipid panelinde LDL {ldl} mg/dL, HDL {hdl} mg/dL ve trigliserid {triglycerides} mg/dL kayıtlı.",
  },
  loading: false,
  loadError: null,
  onRetry: () => undefined,
  retryLabel: "Yeniden dene",
  loadingLabel: "Yükleniyor…",
  formatDate: (value: string) => value,
};

describe("ClinicalSummaryCard", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders title, subtitle, and disclaimer", () => {
    render(<ClinicalSummaryCard {...baseProps} items={[]} />);
    expect(screen.getByRole("heading", { name: "Klinik özet" })).toBeInTheDocument();
    expect(screen.getByText("Son dönem klinik görünüm")).toBeInTheDocument();
    expect(
      screen.getByText(/tanı veya tedavi önerisi değildir/i),
    ).toBeInTheDocument();
  });

  it("shows empty state when there are no items", () => {
    render(<ClinicalSummaryCard {...baseProps} items={[]} />);
    expect(
      screen.getByText("Özet oluşturmak için yeterli klinik veri bulunmuyor."),
    ).toBeInTheDocument();
  });

  it("lists up to six overview bullets", () => {
    const items = Array.from({ length: 7 }, (_, index) => ({
      key: index === 0 ? "laboratory_summary" : `item_${index}`,
      severity: "info",
      label: `Label ${index}`,
      message: `Message ${index}`,
      message_key: null,
      message_params: {},
      trend_status: null,
      source_count: 1,
      data_window_start: null,
      data_window_end: null,
    }));
    render(<ClinicalSummaryCard {...baseProps} items={items} />);
    expect(screen.getByText(/Laboratuvar:/)).toBeInTheDocument();
    expect(screen.queryByText(/Label 6:/)).not.toBeInTheDocument();
  });
});
