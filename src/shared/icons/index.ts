import { addCollection } from "@iconify/vue";
import lucide from "@iconify-json/lucide/icons.json";

// Nuxt UI's Icon.vue renders `i-lucide-*` names via @iconify/vue's <Icon>,
// which otherwise fetches unknown icons from api.iconify.design at runtime.
// Registering the whole collection locally means every i-lucide-* icon
// resolves from memory, with no network request ever made.
addCollection(lucide);
