import { commonContent } from "@/content/en/common";

/** Resolves localized copy. Phase 1A returns English only; extend for Turkish later. */
export function getCommonContent(locale?: string) {
  void locale;
  return commonContent;
}
