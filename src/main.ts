import "@fontsource-variable/onest/wght.css";
import "@/assets/css/main.css";
import { createApp } from "vue";
import ui from "@nuxt/ui/vue-plugin";
import App from "@/app/App.vue";
import { router } from "@/app/router";
import { i18n } from "@/shared/i18n";
import { createPinia } from "pinia";
import { setApiHooks } from "@/shared/api/client.api";
import { useAuthStore } from "@/modules/auth";

const pinia = createPinia();
const app = createApp(App);

app.use(pinia);
app.use(router);
app.use(i18n);
app.use(ui);

setApiHooks({
  onUnauthorized: () => {
    const auth = useAuthStore();
    auth.logoutLocal();
    if (router.currentRoute.value.name !== "login") {
      router.push({ name: "login" });
    }
  },
});

app.mount("#app");
