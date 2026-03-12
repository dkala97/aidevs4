/**
 * Client dla zewnętrznego API paczek.
 * Obsługuje akcje: check (sprawdzenie statusu) i redirect (przekierowanie paczki).
 */

import { logger } from "../utils/logger.js";

export interface PackageStatus {
  packageId: string;
  status: string;
  location?: string;
  details?: Record<string, unknown>;
}

export interface RedirectConfirmation {
  confirmation: string;
  packageId: string;
  destination: string;
}

export class ParcelsClient {
  private readonly apiUrl: string;
  private readonly apiKey: string;

  constructor(hubUrl: string, apiKey: string) {
    this.apiUrl = `${hubUrl}/api/packages`;
    this.apiKey = apiKey;
  }

  async checkPackage(packageId: string): Promise<PackageStatus> {
    logger.info("parcels_client", {
      message: "Checking package status",
      packageId,
    });

    const response = await fetch(this.apiUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        apikey: this.apiKey,
        action: "check",
        packageid: packageId,
      }),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    const data = (await response.json()) as Record<string, unknown>;

    // Extract known fields, pass the rest as details
    const { status, location, ...rest } = data;

    return {
      packageId,
      status: String(status ?? "unknown"),
      location: location !== undefined ? String(location) : undefined,
      details: Object.keys(rest).length > 0 ? rest : undefined,
    };
  }

  async redirectPackage(
    packageId: string,
    destination: string,
    code: string,
  ): Promise<RedirectConfirmation> {
    logger.info("parcels_client", {
      message: "Redirecting package",
      packageId,
      destination,
      // code intentionally NOT logged (security sensitive)
    });

    const response = await fetch(this.apiUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        apikey: this.apiKey,
        action: "redirect",
        packageid: packageId,
        destination,
        code,
      }),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    const data = (await response.json()) as Record<string, unknown>;

    if (!data.confirmation) {
      throw new Error("API did not return a confirmation code");
    }

    return {
      confirmation: String(data.confirmation),
      packageId,
      destination,
    };
  }
}
