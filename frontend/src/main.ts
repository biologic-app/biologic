import { application, store } from "@/app";
import { useAuth } from "@/modules/auth";
import { registerServiceWorker } from "@/shared/composables/usePushNotifications";

useAuth(store).restoreSession().finally(() => {
  application.mount("#app");
});

registerServiceWorker();
