import { application, store } from "@/app";
import { useAuth } from "@/modules/auth";

useAuth(store).restoreSession().finally(() => {
  application.mount("#app");
});
