"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Github, Mail, Lock, Loader2, ArrowRight, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import toast from "react-hot-toast";

export default function LoginPage() {
    const router = useRouter();
    const [isLogin, setIsLogin] = useState(true);
    const [loading, setLoading] = useState(false);
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);

        try {
            let data;
            if (isLogin) {
                data = await api.login(email, password);
                toast.success("Welcome back!");
            } else {
                data = await api.register(email, password);
                toast.success("Account created successfully!");
            }

            localStorage.setItem("token", data.access_token);
            router.push("/dashboard");
        } catch (error: any) {
            toast.error(error.message || "Authentication failed");
        } finally {
            setLoading(false);
        }
    };

    const handleGitHubLogin = () => {
        window.location.href = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:3500"}/auth/github`;
    };

    return (
        <div className="min-h-screen bg-black flex flex-col items-center justify-center p-4 relative overflow-hidden">
            {/* Background Glow */}
            <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-[120px] pointer-events-none" />
            <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-600/10 rounded-full blur-[120px] pointer-events-none" />

            <div className="w-full max-w-md z-10">
                <div className="text-center mb-10">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600 to-purple-600 p-0.5 mb-6 ring-1 ring-white/10 shadow-2xl shadow-blue-500/20">
                        <div className="w-full h-full bg-black rounded-[14px] flex items-center justify-center">
                            <Sparkles className="w-8 h-8 text-white" />
                        </div>
                    </div>
                    <h1 className="text-4xl font-bold text-white tracking-tight mb-3">
                        {isLogin ? "Welcome to Axel" : "Create your account"}
                    </h1>
                    <p className="text-gray-400 text-lg">
                        {isLogin ? "Sign in to continue building." : "Get started with the world's most capable AI coder."}
                    </p>
                </div>

                <div className="bg-gray-900/50 backdrop-blur-xl border border-white/10 rounded-3xl p-8 shadow-2xl ring-1 ring-white/5">
                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">Email Address</label>
                            <div className="relative">
                                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="w-full bg-black/50 border border-white/10 rounded-xl py-3 pl-11 pr-4 text-white placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                                    placeholder="axel@example.com"
                                    required
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">Password</label>
                            <div className="relative">
                                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="w-full bg-black/50 border border-white/10 rounded-xl py-3 pl-11 pr-4 text-white placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                                    placeholder="••••••••"
                                    required
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full bg-white text-black font-semibold py-3 rounded-xl hover:bg-gray-200 transition-colors flex items-center justify-center gap-2 group"
                        >
                            {loading ? (
                                <Loader2 className="w-5 h-5 animate-spin" />
                            ) : (
                                <>
                                    {isLogin ? "Sign In" : "Create Account"}
                                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                                </>
                            )}
                        </button>
                    </form>

                    <div className="relative my-8">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-white/10"></div>
                        </div>
                        <div className="relative flex justify-center text-xs uppercase">
                            <span className="bg-[#0b0e14] px-4 text-gray-500">Or continue with</span>
                        </div>
                    </div>

                    <button
                        onClick={handleGitHubLogin}
                        className="w-full bg-gray-800/50 border border-white/10 text-white font-medium py-3 rounded-xl hover:bg-gray-800 transition-colors flex items-center justify-center gap-3"
                    >
                        <Github className="w-5 h-5" />
                        Sign in with GitHub
                    </button>
                </div>

                <div className="mt-8 text-center">
                    <p className="text-gray-400">
                        {isLogin ? "Don't have an account?" : "Already have an account?"}{" "}
                        <button
                            onClick={() => setIsLogin(!isLogin)}
                            className="text-white font-semibold hover:underline decoration-blue-500/50 underline-offset-4"
                        >
                            {isLogin ? "Create one now" : "Sign in instead"}
                        </button>
                    </p>
                </div>
            </div>
        </div>
    );
}
