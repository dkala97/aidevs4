import { z } from "zod";
import { config } from "../../config/env.js";
import { toolsMetadata } from "../../config/metadata.js";
import { ParcelsClient } from "../services/parcels-client.js";
import { defineTool } from "./types.js";

const redirectPackageInputSchema = z.object({
  packageId: z
    .string()
    .min(1)
    .describe("ID paczki do przekierowania, np. PKG12345678"),
  destination: z
    .string()
    .min(1)
    .describe("Kod docelowego punktu odbioru, np. PWR3847PL"),
  code: z
    .string()
    .min(1)
    .describe("Kod zabezpieczający podany przez operatora podczas rozmowy"),
});

export const redirectPackageTool = defineTool({
  name: toolsMetadata.redirect_package.name,
  title: toolsMetadata.redirect_package.title,
  description: toolsMetadata.redirect_package.description,
  inputSchema: redirectPackageInputSchema,
  outputSchema: {
    confirmation: z
      .string()
      .describe("Kod potwierdzenia do przekazania operatorowi"),
    packageId: z.string().describe("ID paczki"),
    destination: z.string().describe("Kod docelowego punktu odbioru"),
  },
  annotations: {
    readOnlyHint: false,
    destructiveHint: false,
    idempotentHint: false,
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
      const client = new ParcelsClient(config.HUB_URL, config.HUB_API_KEY);
      const result = await client.redirectPackage(
        args.packageId,
        args.destination,
        args.code,
      );

      return {
        content: [
          {
            type: "text",
            text: `Paczka ${result.packageId} została przekierowana do ${result.destination}.\nKod potwierdzenia dla operatora: ${result.confirmation}`,
          },
        ],
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
