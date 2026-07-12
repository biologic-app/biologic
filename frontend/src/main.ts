import { application, store } from "@/app";
import { router } from "@/app/router";
import { useAuth } from "@/modules/auth";
import { initTelemetry } from "@/shared/composables/useTelemetry";
import { registerServiceWorker } from "@/app/registerServiceWorker";

useAuth(store).restoreSession().finally(() => {
  application.mount("#app");
  initTelemetry(router);
});

registerServiceWorker();
