import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export default function HomePage() {
  const hasToken = cookies().get("fc_token")?.value;
  redirect(hasToken ? "/dashboard" : "/login");
}
