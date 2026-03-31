import { AuthUser } from "@/shared/types/auth";
import { Permission } from "@/shared/types/permissions";
import z from "zod";

export interface AuthState {
  user: AuthUser | null;
  permissions: Permission[];
  loading: boolean;
  initialized: boolean;
}

export type LoginSchema = {
  username: string;
  password: string;
  remember: boolean;
};

export type LoginZodSchema = z.ZodObject<{
  username: z.ZodString;
  password: z.ZodString;
  remember: z.ZodDefault<z.ZodBoolean>;
}>;
