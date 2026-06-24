import type { Property, Provider } from "./types";

export interface ScoredProvider {
  provider: Provider;
  score: number;
  breakdown: {
    availability: number;
    zone: number;
    rating: number;
    load: number;
  };
}

// Attribution automatique (version MVP du cahier des charges) :
// score = disponibilité (40%) + zone proche (30%) + rating (20%) + charge actuelle (10%)
export function scoreProviders(
  property: Property,
  providers: Provider[],
): ScoredProvider[] {
  const propertyZone = zoneOf(property.address);

  return providers
    .map((provider) => {
      const availability = provider.availabilityScore; // 0..1
      const zone = provider.zone === propertyZone ? 1 : 0.3;
      const rating = provider.rating / 5;
      const load = 1 - Math.min(provider.currentLoad, 5) / 5; // moins chargé = mieux

      const breakdown = {
        availability: availability * 0.4,
        zone: zone * 0.3,
        rating: rating * 0.2,
        load: load * 0.1,
      };

      const score =
        breakdown.availability +
        breakdown.zone +
        breakdown.rating +
        breakdown.load;

      return { provider, score, breakdown };
    })
    .sort((a, b) => b.score - a.score);
}

function zoneOf(address: string): string {
  // Heuristique simple : on déduit la zone à partir de la ville présente dans l'adresse.
  const lower = address.toLowerCase();
  if (lower.includes("chamonix")) return "Chamonix";
  if (lower.includes("megève") || lower.includes("megeve")) return "Megève";
  if (lower.includes("annecy")) return "Annecy";
  return "Chamonix";
}
