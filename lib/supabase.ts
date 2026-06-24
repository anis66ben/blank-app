// Client Supabase — placeholder MVP.
//
// L'application de démonstration fonctionne avec des données en mémoire (lib/mock-data.ts)
// afin de tourner sans backend. Pour brancher Supabase :
//
// 1. npm i @supabase/supabase-js
// 2. Renseigner NEXT_PUBLIC_SUPABASE_URL et NEXT_PUBLIC_SUPABASE_ANON_KEY (.env.local)
// 3. Décommenter ci-dessous et remplacer les sélecteurs du store par des requêtes.
//
// import { createClient } from "@supabase/supabase-js";
//
// export const supabase = createClient(
//   process.env.NEXT_PUBLIC_SUPABASE_URL!,
//   process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
// );

export const SUPABASE_CONFIGURED = Boolean(
  process.env.NEXT_PUBLIC_SUPABASE_URL &&
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
);
