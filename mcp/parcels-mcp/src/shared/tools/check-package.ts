import { z } from "zod";
import { config } from "../../config/env.js";
import { toolsMetadata } from "../../config/metadata.js";
import { ParcelsClient } from "../services/parcels-client.js";
import { defineTool } from "./types.js";

const checkPackageInputSchema = z.object({
  packageId: z.string().min(1).describe("ID paczki, np. PKG12345678"),
});

export const checkPackageTool = defineTool({
  name: toolsMetadata.check_package.name,
  title: toolsMetadata.check_package.title,
  description: toolsMetadata.check_package.description,
  inputSchema: checkPackageInputSchema,
  outputSchema: {
    packageId: z.string().describe("ID paczki"),
    status: z.string().describe("Aktualny status paczki"),
    location: z.string().optional().describe("Aktualna lokalizacja paczki"),
    details: z
      .record(z.unknown())
      .optional()
      .describe("Dodatkowe metadane z API"),
  },
  annotations: {
    readOnlyHint: true,
    destructiveHint: false,
    idempotentHint: true,
    openWorldHint: true,
  },
  handler: async (args, context) => {
    if (context.signal?.aborted) {
      return {
        isError: true,
        content: [{ type: "text", text: "Operacja anulowana" }],
      };
    }

    try {
      const client = new ParcelsClient(config.HUB_URL, config.PARCELS_API_KEY);
      const result = await client.checkPackage(args.packageId);

      const lines = [
        `Paczka: ${result.packageId}`,
        `Status: ${result.status}`,
        result.location ? `Lokalizacja: ${result.location}` : null,
      ].filter(Boolean);

      return {
        content: [{ type: "text", text: lines.join("\n") }],
        structuredContent: result as unknown as Record<string, unknown>,
      };
    } catch (error) {
      return {
        isError: true,
        content: [{ type: "text", text: `Błąd: ${(error as Error).message}` }],
      };
    }
  },
});
