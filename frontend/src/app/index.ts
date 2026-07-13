import "./styles/index.css";
import "@/shared/icons";
import ui from "@nuxt/ui/vue-plugin";
import { createApp } from "vue";
import App from "./App.vue";
import { router } from "./router";
import { i18n } from "@/shared/i18n";
import { store } from "./store";
export { store };
import { setApiHooks } from "@/shared/api/client.api";
import { useAuth } from "@/modules/auth";

export const application = createApp(App)
  .use(store)
  .use(router)
  .use(i18n)
  .use(ui);

setApiHooks({
  onRefresh: () => useAuth().refresh(),
  onUnauthorized: () => {
    useAuth().handleAuthLoss();
  },
});
