"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import toast from "react-hot-toast";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { registerUser } from "@/services/authService";

export default function RegisterPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      setLoading(true);
      await registerUser(email, password);
      toast.success("Account created. Please log in.");
      router.push("/login");
    } catch {
      toast.error("Registration failed. Try another email.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="page-enter mx-auto flex min-h-screen w-full max-w-md items-center px-4">
      <Card className="w-full">
        <p className="text-xs uppercase tracking-[0.18em] text-muted">Finance Copilot</p>
        <h1 className="mt-2 text-4xl font-semibold">Create Account</h1>
        <p className="mt-1 text-sm text-muted">Start building better money habits today.</p>

        <form className="mt-6 space-y-3" onSubmit={onSubmit}>
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required />
          <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="At least 8 characters" minLength={8} required />
          <Button type="submit" className="w-full" isLoading={loading}>
            Register
          </Button>
        </form>

        <p className="mt-4 text-sm text-muted">
          Already have an account? <Link className="text-accent transition hover:text-[#88ffd6]" href="/login">Log in</Link>
        </p>
      </Card>
    </main>
  );
}
