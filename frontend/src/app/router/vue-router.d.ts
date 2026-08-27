// This can be directly added to any of your `.ts` files like `router.ts`
// It can also be added to a `.d.ts` file. Make sure it's included in
// project's tsconfig.json "files"
import "vue-router";
import type { Resource, Action } from "@/shared/types/permissions";

// To ensure it is treated as a module, add at least one `export` statement
export {};

declare module "vue-router" {
  interface RouteMeta {
    requiresAuth: boolean;
    /** Canonical backend permission code (resource.action). */
    permission?: string;
    resource?: Resource;
    action?: Action;
  }
}
