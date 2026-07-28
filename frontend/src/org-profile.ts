/**
 * Org profile stored once, propagated into every compliance wizard.
 *
 * Kept in localStorage for now. Lives on the deployer's device, not our
 * servers. Populated either through ``/settings/org`` or interactively from
 * the auth success screen.
 */

const STORAGE_KEY = "af_org_profile_v1";

export type SizeCategory = "microenterprise" | "sme" | "large" | "public_body" | "";

export interface OrgProfile {
  organisation: string;
  address: string;
  contact: string;
  size_category: SizeCategory;
  accountability_owner: string;
  pmm_owner: string;
  authority_contact: string;
  ce_marking_affixed: boolean;
  member_states: string;
}

export const EMPTY_PROFILE: OrgProfile = {
  organisation: "",
  address: "",
  contact: "",
  size_category: "",
  accountability_owner: "",
  pmm_owner: "",
  authority_contact: "",
  ce_marking_affixed: false,
  member_states: "",
};

export function loadOrgProfile(): OrgProfile {
  if (typeof window === "undefined") return EMPTY_PROFILE;
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return EMPTY_PROFILE;
  try {
    return { ...EMPTY_PROFILE, ...(JSON.parse(raw) as Partial<OrgProfile>) };
  } catch {
    return EMPTY_PROFILE;
  }
}

export function saveOrgProfile(profile: OrgProfile): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
}

export function clearOrgProfile(): void {
  localStorage.removeItem(STORAGE_KEY);
}

/** Convenience: return the first non-empty value among candidates. */
export function firstNonEmpty(...candidates: (string | undefined | null)[]): string {
  for (const c of candidates) {
    if (c && c.trim().length > 0) return c;
  }
  return "";
}
