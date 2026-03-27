"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import toast from "react-hot-toast";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/hooks/useAuth";
import { loginUser } from "@/services/authService";

export default function LoginPage() {
  const router = useRouter();
  const setToken = useAuth((state) => state.setToken);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      setLoading(true);
      const response = await loginUser(email, password);
      setToken(response.access_token);
      toast.success("Welcome back");
      router.push("/dashboard");
    } catch (error) {
      toast.error("Invalid credentials");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="page-enter mx-auto flex min-h-screen w-full max-w-md items-center px-4">
      <Card className="w-full">
        <p className="text-xs uppercase tracking-[0.18em] text-muted">Finance Copilot</p>
        <h1 className="mt-2 text-4xl font-semibold">Welcome Back</h1>
        <p className="mt-1 text-sm text-muted">Log in to continue your finance journey.</p>

        <form className="mt-6 space-y-3" onSubmit={onSubmit}>
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required />
          <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" required />
          <Button type="submit" className="w-full" isLoading={loading}>
            Login
          </Button>
        </form>

        <p className="mt-4 text-sm text-muted">
          New here? <Link className="text-accent transition hover:text-[#88ffd6]" href="/register">Create account</Link>
        </p>
      </Card>
    </main>
  );
}
